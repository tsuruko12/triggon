import inspect
from typing import Any

from ._exceptions import SYMBOL


def _store_org_value(
    self, label: str, index: int, org_value: Any,
) -> None:
    if isinstance(org_value, (list, tuple)):
      self._org_value[label][index] = []  

      for v in org_value:
          self._org_value[label][index].append(v)
    else:
      self._org_value[label][index] = org_value

def _update_var_value(
    self, 
    var_ref: tuple[Any] | list[tuple[Any]], update_value: Any,
) -> None:
    # var_ref can be:
    # - (lineno, var_name) for globals
    # - (lineno, attr_name, instance) for class attributes
    # - a list of either form

    if isinstance(var_ref, list):
        # When multiple variables are provided, a list is used
        for value in var_ref:
            if len(value) == 3:
                setattr(value[2], value[1], update_value)
            else:
                self._frame.f_globals[value[1]] = update_value   

    else:     
        if len(var_ref) == 3:
            setattr(var_ref[2], var_ref[1], update_value)
        else:  
            self._frame.f_globals[var_ref[1]] = update_value

def _check_exist_label(self, label: str) -> None:
    try:
        self._new_value[label]
    except KeyError:
        raise KeyError(f"`{label}` has not been set.")

def _check_label_flag(self, label: str) -> None:
    name = label.lstrip(SYMBOL)
    self._check_exist_label(name)

    if self._disable_label[name] or self._trigger_flag[name]:
        return
    
    self._trigger_flag[name] = True
    self._label_has_var(name, "set_trigger", False)

    if self.debug:
        self._get_target_frame("set_trigger")
        self._print_flag_debug(name, "active", reset=False)   

def _label_has_var(
    self, label: str, called_func: str, to_org: bool,
) -> None:
    if self._var_list[label] is None:
        return
    
    if to_org:
        update_value = self._org_value[label]
    else:
        update_value = self._new_value[label]

    self._get_target_frame(called_func)

    # Restore all variables to their original or new values 
    for i in range(len(self._var_list[label])):
        arg = self._var_list[label][i]

        if arg is None:
            continue
        elif isinstance(arg, list):
            for i_2, v in enumerate(arg):
                if not isinstance(update_value[i], tuple):
                    self._update_var_value(v, update_value[i])
                    continue            

                self._update_var_value(v, update_value[i][i_2])
                if self.debug:
                  self._print_var_debug(True, value[1], update_value[i][i_2], change=True)
        else:
            self._update_var_value(arg, update_value[i])     

def _is_new_var(self, label: str, index: int, value: Any) -> bool:
    if self._trigger_flag[label]:
        if self._new_value[label][index] == value:
            return False
    
        return True
    
    if self._org_value[label][index] == value:
        return False
    
    return True

def _get_target_frame(self, target_name: str) -> None:
   if self._frame is not None:
      return
   
   frame = inspect.currentframe()

   while frame:
      if frame.f_code.co_name == target_name:
         self._frame = frame.f_back
         return     
      frame = frame.f_back

def _clear_frame(self) -> None:
   # to prevent memory leak by releasing the frame reference
   self._frame = None
   self._lineno = None

