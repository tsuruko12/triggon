import logging
import os
import threading
from typing import Any

from ...trigfunc import TRIGFUNC_ATTR
from .._types.structs import Callsite, DebugConfig
from ..frames import get_callsite, get_target_frame
from ..sentinel import _NO_VALUE
from .setup import LOG_LABELS

TRIGGER_LOG = "Label {label} is {state}"
DELAY_TRIGGER_LOG = "Label {label} will be {state} after {sec}s"

SWITCH_LIT_LOG = "{prev_value} -> {new_value}"
UPDATE_REF_LOG = "{var}: " + SWITCH_LIT_LOG

REGISTER_REF_LOG = "{name} was registered under label {label}"
UNREGISTER_REF_LOG = "{name} was unregistered from label {label}"

TRIG_EARLY_RET = "Early return triggered (return_value={value})"
TRIG_CALL = "Trigger call executed (target={target})"

SWITCH_LIT_ATTR = "_switch_lit_debug_state"


class DebugLogger:
    debug: DebugConfig
    _logger: logging.Logger
    _lock: threading.Lock

    def _is_target_label(self, label: str) -> bool:
        target_labels = self.debug[LOG_LABELS]
        if target_labels is None:
            return True
        elif label in target_labels:
            return True
        return False

    def log_label_flag_change(
        self,
        label: str,
        callsite: Callsite,
        set_true: bool,
        after: int | float = 0,
        disable: bool = False,
    ) -> None:
        if not self._is_target_label(label):
            return

        if set_true:
            state = "active"
        elif not disable:
            state = "inactive"
        else:
            state = "disabled"

        if after == 0:
            log_msg = TRIGGER_LOG.format(label=repr(label), state=state)
        else:
            # verbosity level 3 only
            log_msg = DELAY_TRIGGER_LOG.format(
                label=repr(label),
                state=state,
                sec=after,
            )
        self._logger.debug(log_msg, extra=_build_log_extra(callsite))

    def log_registered_name(self, target_name: str, label: str, callsite: Callsite) -> None:
        log_msg = REGISTER_REF_LOG.format(name=repr(target_name), label=repr(label))
        self._logger.debug(log_msg, extra=_build_log_extra(callsite))

    def log_unregistered_name(self, target_name: str, label: str, callsite: Callsite) -> None:
        log_msg = UNREGISTER_REF_LOG.format(name=repr(target_name), label=repr(label))
        self._logger.debug(log_msg, extra=_build_log_extra(callsite))

    def log_value_update(
        self,
        label: str | None,
        idx: int | None,
        prev_value: Any,
        new_value: Any,
        callsite: Callsite,
        target_name: str | None = None,
    ) -> None:
        if label is not None and not self._is_target_label(label):
            return

        if hasattr(prev_value, TRIGFUNC_ATTR):
            prev_value = prev_value._trigcall.name
        if hasattr(new_value, TRIGFUNC_ATTR):
            new_value = new_value._trigcall.name

        if target_name is None:
            log_msg = SWITCH_LIT_LOG.format(
                prev_value=repr(prev_value),
                new_value=repr(new_value),
            )
        else:
            log_msg = UPDATE_REF_LOG.format(
                var=target_name,
                prev_value=repr(prev_value),
                new_value=repr(new_value),
            )

        if idx is not None:
            log_msg = f"{log_msg} (index={idx})"

        self._logger.debug(log_msg, extra=_build_log_extra(callsite))

    # used for switch_lit()
    def store_debug_state(
        self,
        orig_value: Any,
        new_value: Any = _NO_VALUE,
        label: str | None = None,
        idx: int | None = None,
    ) -> None:
        frame = get_target_frame(depth=2)
        callsite = get_callsite(frame, get_lasti=True)

        # build a unique key
        key_name = callsite.file, callsite.lineno, callsite.lasti

        with self._lock:
            debug_state = getattr(self, SWITCH_LIT_ATTR, None)

            if debug_state is None:
                # initialize the debug state store
                debug_state = {key_name: orig_value}
                setattr(self, SWITCH_LIT_ATTR, debug_state)
            elif key_name not in debug_state:
                debug_state[key_name] = orig_value

            prev_value = debug_state[key_name]

            if new_value is _NO_VALUE:
                new_value = orig_value
            debug_state[key_name] = new_value

            if prev_value == new_value:
                return

        self.log_value_update(
            label,
            idx,
            prev_value,
            new_value,
            callsite,
        )

    def log_early_return(self, label: str, value: Any, callsite: Callsite) -> None:
        if not self._is_target_label(label):
            return

        self._logger.debug(TRIG_EARLY_RET.format(value=value), extra=_build_log_extra(callsite))

    def log_triggered_call(self, label: str, target_name: str, callsite: Callsite) -> None:
        if not self._is_target_label(label):
            return

        self._logger.debug(TRIG_CALL.format(target=target_name), extra=_build_log_extra(callsite))


def _build_log_extra(callsite: Callsite) -> dict[str, str | int]:
    extra_data = {
        "caller_func": callsite.scope_name,
        "caller_file": os.path.basename(callsite.file),
        "caller_line": callsite.lineno,
    }

    return extra_data
