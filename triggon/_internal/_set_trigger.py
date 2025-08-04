from threading import Timer

from ._exceptions import SYMBOL


def _check_label_flag(
        self, label: str, cond: str | None, after: int | float | None,
) -> None:
    target_func = "set_trigger"

    name = label.lstrip(SYMBOL)
    self._check_exist_label(name)

    if self._disable_flags[name] or self._trigger_flags[name]:
        return
    elif self._delay_info[name][0] is not None:
        return
    
    if cond is not None:
        self._get_target_frame(target_func)

        if not self._ensure_safe_cond(cond):
            return
        
    if after is None:
        self._activate_trigger(name)
    else:
        Timer(after, self._activate_trigger, args=(name,)).start()

    if self.debug:
        self._get_target_frame(target_func)
        self._print_flag_debug(name, "active", after, clear=False) 
    
    self._label_has_var(name, target_func, after)

def _activate_trigger(self, label: str) -> None:
    self._trigger_flags[label] = True

