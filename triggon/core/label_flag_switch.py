from threading import Timer
from typing import Any, Literal, Mapping

from .._internal import LOG_VERBOSITY, get_callsite, get_target_frame
from .._internal.arg_types import Callsite


type DelayKey = Literal["trigger", "revert"]


class LabelFlagController:
    def set_label_flags(
        self,
        label_to_idx: dict[str, int | None],
        cond: str,
        after: int | float,
        set_true: bool,
    ) -> None:
        frame = get_target_frame(depth=1)
        if cond and not self._evaluate_cond(frame, cond):
            return

        if set_true:
            delay_key = "trigger"
        else:
            delay_key = "revert"

        callsite = get_callsite(frame)
        f_globals = frame.f_globals
        frame = None

        # Use a per-instance lock for label flag toggles

        if after == 0:
            self._set_flags_and_update(
                label_to_idx,
                callsite,
                f_globals,
                delay_key,
                set_true,
            )
        else:
            # Remove labels that are already scheduled for a delay
            self._prepare_delay(
                label_to_idx,
                callsite,
                after,
                delay_key,
                set_true,
            )
            # Schedule a delayed toggle
            Timer(
                after,
                self._set_flags_and_update,
                args=(label_to_idx, callsite, f_globals, delay_key, set_true),
                kwargs={"is_delay": True},
            ).start()

    def _prepare_delay(
        self,
        label_to_idx: dict[str, int | None],
        callsite: Callsite,
        after: int | float,
        delay_key: DelayKey,
        set_true: bool,
    ) -> None:
        labels = tuple(label_to_idx)

        debug_on = self.debug[LOG_VERBOSITY] == 3

        for label in labels:
            with self._lock:
                if self._label_delay_state[label][delay_key]:
                    del label_to_idx[label]
                    continue
                self._label_delay_state[label][delay_key] = True

            if debug_on:
                self.log_label_flag_change(
                    label,
                    callsite,
                    set_true,
                    after,
                )

    def _set_flags_and_update(
        self,
        label_to_idx: dict[str, int | None],
        callsite: Callsite,
        f_globals: Mapping[str, Any],
        delay_key: DelayKey,
        set_true: bool,
        is_delay: bool = False,
    ) -> None:
        debug_on = self.debug[LOG_VERBOSITY] != 0

        for label, i in label_to_idx.items():
            with self._lock:
                if self._label_is_perm_disabled[label]:
                    continue
                elif not is_delay and self._label_delay_state[label][delay_key]:
                    continue

                is_triggered = self._label_is_active[label]
                if set_true and not is_triggered:
                    self._label_is_active[label] = True
                elif not set_true and is_triggered:
                    self._label_is_active[label] = False
                else:
                    continue

                if is_delay:
                    self._label_delay_state[label][delay_key] = False

                if debug_on:
                    self.log_label_flag_change(label, callsite, set_true)
                self.update_values(label, i, f_globals, callsite, set_true)
