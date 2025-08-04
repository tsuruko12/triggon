from threading import Timer

from ._err_handler import _check_label_type
from ._exceptions import SYMBOL


def _revert_value(
        self, label: str, disable: bool, after: int | float | None,
) -> None:
    _check_label_type(label, allow_dict=False)

    name = label.lstrip(SYMBOL)
    self._check_exist_label(name)

    if self._delay_info[name][1] is not None:
        return
    elif not disable and not self._trigger_flags[name]:
        return
    elif disable and self._disable_flags[name]:
        return 
    
    if after is None:
        self._deactivate_trigger(name, disable)
    else:
        Timer(after, self._deactivate_trigger, args=(name, disable)).start()

    # for debug
    if disable:
        state = "disable"
    else:
        state = "inactive"

    self._label_has_var(name, "revert", after, to_org=True)

    if self.debug:
        self._get_target_frame("revert")
        self._print_flag_debug(name, state) 

def _deactivate_trigger(self, label: str, disable: bool) -> None:
    self._trigger_flags[label] = False

    if disable:
        self._disable_flags[label] = True