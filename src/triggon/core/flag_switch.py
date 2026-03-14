import logging
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from threading import Lock, Timer
from typing import TYPE_CHECKING, Any

from .._internal._types.aliases import DelayKey, RevertMap, TriggerMap
from .._internal._types.structs import Callsite, DebugConfig, DelayState
from .._internal.frames import get_callsite, get_target_frame
from .._internal.keys import LOG_VERBOSITY, REVERT, TRIGGER
from .value_resolver import evaluate_cond


@dataclass(frozen=True, slots=True)
class _ToggleAction:
    delay_key: DelayKey
    f_globals: MutableMapping[str, Any]
    callsite: Callsite
    set_true: bool
    disable: bool


class LabelFlagController:
    debug: DebugConfig
    _logger: logging.Logger | None
    _label_is_active: dict[str, bool]
    _label_delay_state: dict[str, dict[DelayKey, DelayState]]
    _label_is_perm_disabled: dict[str, bool]
    _lock: Lock

    if TYPE_CHECKING:
        from .._internal._types.aliases import UpdateRefs

        def log_label_flag_change(
            self,
            label: str,
            callsite: Callsite,
            set_true: bool,
            after: int | float = 0,
            disable: bool = False,
        ) -> None: ...

        def update_values(
            self,
            label: str,
            idx: int | None,
            f_globals: MutableMapping[str, Any],
            callsite: Callsite,
            is_trigger: bool,
            update_refs: UpdateRefs | None = None,
        ) -> None: ...

    def set_label_flags(
        self,
        label_to_idx: TriggerMap | RevertMap,
        cond: str,
        after: int | float,
        reschedule: bool,
        set_true: bool,
        disable: bool = False,
    ) -> None:
        frame = get_target_frame(depth=2)
        if cond and not evaluate_cond(frame, cond):
            return

        if set_true:
            delay_key = TRIGGER
        else:
            delay_key = REVERT

        callsite = get_callsite(frame)
        f_globals = frame.f_globals
        frame = None

        toggle_act = _ToggleAction(delay_key, f_globals, callsite, set_true, disable)

        if after != 0 or reschedule:
            # remove labels that are already scheduled for a delay
            label_to_timer_id = self._prepare_delay(
                label_to_idx,
                toggle_act,
                after,
                reschedule,
                callsite,
            )
            if not label_to_timer_id:
                return
        else:
            label_to_timer_id = None

        if after == 0:
            self._set_flags_and_update(label_to_idx, toggle_act, label_to_timer_id)
        else:
            timer = Timer(
                after,
                self._set_flags_and_update,
                args=(label_to_idx, toggle_act),
                kwargs={"label_to_timer_id": label_to_timer_id},
            )
            target_labels = tuple(label_to_idx.keys())
            for label in label_to_idx:
                delay_state = self._label_delay_state[label][delay_key]
                with self._lock:
                    delay_state.timer = timer
                    delay_state.labels = target_labels

            timer.start()

    def _prepare_delay(
        self,
        label_to_idx: TriggerMap | RevertMap,
        toggle_act: _ToggleAction,
        after: int | float,
        reschedule: bool,
        callsite: Callsite,
    ) -> Mapping[str, int]:
        labels = tuple(label_to_idx)

        # label_to_idx and label_to_timer_id share the same labels
        label_to_timer_id = {}
        stale_timer = None
        stale_timer_labels = None
        debug_on = self.debug[LOG_VERBOSITY] == 3

        for label in labels:
            with self._lock:
                if self._label_is_perm_disabled[label]:
                    del label_to_idx[label]
                    continue

                delay_state = self._label_delay_state[label][toggle_act.delay_key]

                if not reschedule and delay_state.is_delay:
                    # already deferred labels are excluded
                    del label_to_idx[label]
                    continue
                elif reschedule and delay_state.is_delay:
                    delay_state.cur_timer_id += 1

                delay_state.is_delay = True

            label_to_timer_id[label] = delay_state.cur_timer_id
            if stale_timer is None:
                stale_timer = delay_state.timer
                stale_timer_labels = delay_state.labels

            if toggle_act.set_true and self._label_is_active[label]:
                continue
            elif not toggle_act.set_true and not self._label_is_active[label]:
                continue

            if after != 0 and debug_on:
                self.log_label_flag_change(
                    label,
                    callsite,
                    toggle_act.set_true,
                    after,
                    toggle_act.disable,
                )

        if stale_timer is not None and stale_timer_labels is not None:
            if all(v in label_to_timer_id.keys() for v in stale_timer_labels):
                stale_timer.cancel()

        return label_to_timer_id

    def _set_flags_and_update(
        self,
        label_to_idx: TriggerMap | RevertMap,
        toggle_act: _ToggleAction,
        label_to_timer_id: Mapping[str, int] | None = None,
    ) -> None:
        # used only for delayed execution
        labels = tuple(label_to_idx)

        debug_on = self.debug[LOG_VERBOSITY] != 0

        try:
            for label, i in label_to_idx.items():
                with self._lock:
                    delay_state = self._label_delay_state[label][toggle_act.delay_key]

                    if self._label_is_perm_disabled[label]:
                        continue

                    if delay_state.is_delay:
                        if label_to_timer_id is not None:
                            if label_to_timer_id[label] != delay_state.cur_timer_id:
                                # skip stale timer callbacks
                                continue
                        else:
                            continue

                    triggered = self._label_is_active[label]
                    if toggle_act.set_true and not triggered:
                        self._label_is_active[label] = True
                        toggled = True
                    elif not toggle_act.set_true and triggered:
                        self._label_is_active[label] = False
                        if toggle_act.disable:
                            self._label_is_perm_disabled[label] = True
                        toggled = True
                    else:
                        toggled = False

                if toggled and debug_on:
                    self.log_label_flag_change(
                        label,
                        toggle_act.callsite,
                        toggle_act.set_true,
                        disable=toggle_act.disable,
                    )

                self.update_values(
                    label,
                    i,
                    toggle_act.f_globals,
                    toggle_act.callsite,
                    toggle_act.set_true,
                )
        except Exception as e:
            if delay_state.is_delay:
                if self._logger is not None:
                    self._logger.exception(e)
            else:
                raise
        finally:
            self._clear_delay_state(
                label_to_timer_id,
                target_labels=labels,
                delay_key=toggle_act.delay_key,
            )

    def _clear_delay_state(
        self,
        label_to_timer_id: Mapping[str, int] | None,
        target_labels: tuple[str, ...],
        delay_key: DelayKey,
    ) -> None:
        if label_to_timer_id is None:
            return

        for label in target_labels:
            delay_state = self._label_delay_state[label][delay_key]
            with self._lock:
                if delay_state.cur_timer_id == label_to_timer_id[label]:
                    # initialize
                    self._label_delay_state[label][delay_key] = DelayState()
