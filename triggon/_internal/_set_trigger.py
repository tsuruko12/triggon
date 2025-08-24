from threading import Lock, Timer
from typing import Any


proc_lock = Lock()


def _update_or_skip(
        self, labels: list[str], index: Any | None, 
        cond: str | None, after: int | float | None,
) -> None:
    target_labels = []
    label_flags = [] # For debug
    for label in labels:
        if self._disable_flags[label]:
            continue
        if self._delay_info[label][0] is not None:
            continue
        target_labels.append(label)
        label_flags.append(self._trigger_flags[label])
        
    target_func = "set_trigger"
    
    if cond is not None:
        self._get_target_frame(target_func)
        if not self._get_cond_result(cond):
            return
        
    if after is None:
        self._activate_trigger(target_labels)
        self._debug_trigger(target_labels, label_flags, after)
        self._has_var_refs(target_labels, target_func, after, index)
    else:
        update_labels = self._has_var_refs(
            target_labels, target_func, after, index,
        )
        self._debug_trigger(target_labels, label_flags, after)

        if False in label_flags:
            Timer(
                after, self._activate_trigger,
                args=(target_labels, index, update_labels),
                kwargs={"flags": label_flags, "delay": True},
            ).start()
        else:
            self._activate_trigger(target_labels)

def _activate_trigger(
        self, labels: list[str], index: int | None = None, 
        update_labels: list[str] | None = None, flags: list[bool] = None,
        delay: bool = False,
) -> None:
    with proc_lock:
        for label in labels:
            if self._disable_flags[label]:
                continue
            self._trigger_flags[label] = True

        # Delay branch
        if delay and False in flags:
            self._debug_trigger(labels, flags, after=None, delay=delay)
        if update_labels is not None:
            self._update_all_vars(update_labels, index)
