import inspect
from typing import Any

from ._exceptions import (
    _UnsetExitError,
    SYMBOL,
)
from ._switch_var import _is_mult_vars


def _store_org_value(self, label: str, index: int, org_value: Any) -> None:
    target_index = self._org_value[label][index] 

    if target_index is None:
        self._org_value[label][index] = org_value
        return
    elif not isinstance(target_index, list):
        self._org_value[label][index] = [target_index]
    elif not _is_mult_vars(target_index):
        self._org_value[label][index] = [target_index]

    if isinstance(org_value, (list, tuple)):
      for v in org_value:
          self._org_value[label][index].append(v)
    else:
      self._org_value[label][index].append(org_value)

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
                cur_value = var_ref[2].__dict__[var_ref[1]]

                if cur_value == update_value:
                    continue

                setattr(value[2], value[1], update_value)
            else:
                cur_value = self._frame.f_globals[value[1]]

                if cur_value == update_value:
                    continue 

                self._frame.f_globals[value[1]] = update_value   
    else:     
        if len(var_ref) == 3:
            cur_value = var_ref[2].__dict__[var_ref[1]]

            if cur_value == update_value:
                return
            
            setattr(var_ref[2], var_ref[1], update_value)
        else:  
            cur_value = self._frame.f_globals[var_ref[1]]
            
            if cur_value == update_value:
                return
            
            self._frame.f_globals[var_ref[1]] = update_value

def _check_label_flag(self, label: str, cond: str | None) -> None:
    target_func = "set_trigger"

    name = label.lstrip(SYMBOL)
    self._check_exist_label(name)

    if self._disable_label[name] or self._trigger_flag[name]:
        return
    
    if cond is not None:
        self._get_target_frame(target_func)

        if not self._ensure_safe_cond(cond):
            return
        
    self._trigger_flag[name] = True
    
    self._label_has_var(name, target_func, False)

    if self.debug:
        self._get_target_frame(target_func)
        self._print_flag_debug(name, "active", clear_fram=False)

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
        var_ref = self._var_list[label][i]

        if var_ref is None:
            continue
        elif isinstance(var_ref, list):
            for i_2, val in enumerate(var_ref):
                if not isinstance(update_value[i], (list, tuple)):
                    self._update_var_value(val, update_value[i])
                    continue            

                self._update_var_value(val, update_value[i][i_2])
        else:
            self._update_var_value(var_ref, update_value[i])      

def _get_target_frame(
        self, target_name: str | list[str, str], has_exit: bool=False,
) -> None:
   if self._frame is not None:
      return

   frame = inspect.currentframe()

   while frame:
      if has_exit:
          if frame.f_code.co_name == "<module>":
              raise _UnsetExitError()
          elif frame.f_code.co_name == target_name:
              return
      elif isinstance(target_name, list):
          if frame.f_code.co_name in target_name:
              self._frame = frame.f_back
              return
      elif frame.f_code.co_name == target_name:
         self._frame = frame.f_back
         return     
      
      frame = frame.f_back

def _clear_frame(self) -> None:
   # to prevent memory leak by releasing the frame reference
   self._frame = None
   self._lineno = None

