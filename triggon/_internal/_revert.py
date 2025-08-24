from threading import Lock, Timer
from typing import Any


proc_lock = Lock()


def _revert_or_skip(
        self, labels: list[str], disable: bool, 
        cond: Any, after: int | float | None,
) -> None:
    target_labels = []
    for label in labels:
        if self._delay_info[label][1] is not None:
            continue
        if not disable and not self._trigger_flags[label]:
            continue
        if disable and self._disable_flags[label]:
            continue     
        target_labels.append(label)
    
    target_func = "revert"
    
    if cond is not None:
        self._get_target_frame(target_func)
        if not self._get_cond_result(cond):
            return
    
    if after is None:
        self._deactivate_trigger(target_labels, disable)
        self._debug_revert(target_labels, after, disable)
        self._has_var_refs(target_labels, target_func, after, to_org=True)
    else:
        update_labels = (
            self._has_var_refs(target_labels, target_func, after, to_org=True)
        )
        self._debug_revert(target_labels, after, disable)
        Timer(
            after, self._deactivate_trigger,
            args=(target_labels, disable, update_labels),
            kwargs={"delay": True},
        ).start()

def _deactivate_trigger(
        self, labels: list[str], disable: bool, 
        update_labels: list[str] = None, delay: bool = False,
) -> None:
    with proc_lock:
        for label in labels:
            self._trigger_flags[label] = False
            if disable:
                self._disable_flags[label] = True

        if delay:
            self._debug_revert(labels, None, disable, delay=True)
            if update_labels is not None:
                self._update_all_vars(update_labels, None, to_org=True)