from threading import Timer

from ._exceptions import SYMBOL


def _check_label_flag(
        self, label: str, cond: str | None, after: int | float,
) -> None:
    target_func = "set_trigger"

    name = label.lstrip(SYMBOL)
    self._check_exist_label(name)

    if self._disable_label[name] or self._trigger_flag[name]:
        return
    elif self._delayed_labels.get(label) is not None:
        return
    
    if cond is not None:
        self._get_target_frame(target_func)

        if not self._ensure_safe_cond(cond):
            return
        
    if after is None:
        self._trigger_flag[label] = True

        if self.debug:
            self._get_target_frame(target_func)
            self._print_flag_debug(name, "active", clear=False)
    else:
        Timer(after, self._delay_trigger, args=(name)).start()

        if self.debug:
            self._get_target_frame(target_func, frame=self._delayed_labels[name])
            self._print_flag_debug(name, "active", after, clear=False)

        self._delayed_labels[label] = None 
    
    self._label_has_var(name, target_func, after)

def _delay_trigger(self, label: str) -> None:
    self._trigger_flag[label] = True

