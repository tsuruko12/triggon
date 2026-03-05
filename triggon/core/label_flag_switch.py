import logging
from dataclasses import dataclass
from threading import Lock, Timer
from typing import TYPE_CHECKING, Any, Mapping

from .._internal import LOG_VERBOSITY, REVERT, TRIGGER
from .._internal._types import (
    Callsite,
    DebugConfig,
    DelayKey,
    DelayState,
    RevertMap,
    TriggerMap,
)
from .._internal.frames import get_callsite, get_target_frame
from .value_resolver import evaluate_cond


@dataclass(frozen=True, slots=True)
class _ToggleData:
    callsite: Callsite
    f_globals: dict[str, Any]
    delay_key: DelayKey
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
            f_globals: dict[str, Any],
            callsite: Callsite,
            is_trigger: bool,
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

        data = _ToggleData(callsite, f_globals, delay_key, set_true, disable)

        if after != 0 or reschedule:
            # remove labels that are already scheduled for a delay
            label_to_timer_id = self._prepare_delay(label_to_idx, data, after, reschedule)
            if not label_to_timer_id:
                return
        else:
            label_to_timer_id = None

        if after == 0:
            self._set_flags_and_update(label_to_idx, data, label_to_timer_id=label_to_timer_id)
        else:
            timer = Timer(
                after,
                self._set_flags_and_update,
                args=(label_to_idx, data),
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
        data: _ToggleData,
        after: int | float,
        reschedule: bool,
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
                elif data.set_true and self._label_is_active[label]:
                    del label_to_idx[label]
                    continue
                elif not data.set_true and not self._label_is_active[label]:
                    del label_to_idx[label]
                    continue

                delay_state = self._label_delay_state[label][data.delay_key]

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

            if debug_on:
                self.log_label_flag_change(
                    label,
                    data.callsite,
                    data.set_true,
                    after,
                    data.disable,
                )

        if stale_timer is not None and stale_timer_labels is not None:
            if all(v in label_to_timer_id.keys() for v in stale_timer_labels):
                stale_timer.cancel()

        return label_to_timer_id

    def _set_flags_and_update(
        self,
        label_to_idx: TriggerMap | RevertMap,
        data: _ToggleData,
        label_to_timer_id: Mapping[str, int] | None = None,
    ) -> None:
        # used only for delayed execution
        labels = tuple(label_to_idx)

        debug_on = self.debug[LOG_VERBOSITY] != 0

        try:
            for label, i in label_to_idx.items():
                with self._lock:
                    delay_state = self._label_delay_state[label][data.delay_key]

                    if self._label_is_perm_disabled[label]:
                        continue

                    if delay_state.is_delay:
                        if label_to_timer_id is not None:
                            if label_to_timer_id[label] != delay_state.cur_timer_id:
                                # skip stale timer callbacks
                                continue
                        else:
                            continue

                    is_triggered = self._label_is_active[label]
                    if data.set_true and not is_triggered:
                        self._label_is_active[label] = True
                    elif not data.set_true and is_triggered:
                        self._label_is_active[label] = False
                        if data.disable:
                            self._label_is_perm_disabled[label] = True
                    else:
                        continue

                if debug_on:
                    self.log_label_flag_change(
                        label,
                        data.callsite,
                        data.set_true,
                        disable=data.disable,
                    )

                self.update_values(label, i, data.f_globals, data.callsite, data.set_true)
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
                delay_key=data.delay_key,
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
