import inspect
from typing import Any

from ._exceptions import (
    _FrameAccessError,
    _UnsetExitError,
    SYMBOL,
)


def _store_org_value(self, label: str, index: int, org_value: Any) -> None:
    target_index = self._org_value[label][index] 

    if target_index is None:
        self._org_value[label][index] = []

    self._org_value[label][index].append(org_value)

def _update_var_value(
    self, var_ref: tuple[str, ...] | list[tuple[str, ...]], 
    label: str, index: int, update_value: Any, to_org: bool=False,
) -> None:
    # var_ref can be:
    # - (file name, lineno, var name) for globals
    # - (file name, lineno, attr name, instance) for class attributes
    # - a list of either form

    if to_org:
        trig_flag = False
    else:
        trig_flag = True

    if isinstance(var_ref, list):
        for value in var_ref:
            if value[0] != self._file_name or value[1] != self._lineno:
                continue

            if len(value) == 4:
                setattr(value[3], value[2], update_value)
            else:
                self._frame.f_globals[value[2]] = update_value   
    else:     
        if len(var_ref) == 4:     
            setattr(var_ref[3], var_ref[2], update_value)
        else:    
            self._frame.f_globals[var_ref[2]] = update_value

    if self.debug:
        self._print_var_debug(label, index, trig_flag, update_value)


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

    if self.debug:
        self._get_target_frame(target_func)
        self._print_flag_debug(name, "active", clear=False)

    self._label_has_var(name, target_func)

def _label_has_var(
    self, label: str, called_func: str, to_org: bool=False,
) -> None:
    if self._var_list[label] is None:
        return
    
    if to_org:
        update_value = self._org_value[label]
    else:
        # Each index always holds a single value.
        update_value = self._new_value[label]

    self._get_target_frame(called_func)

    # Restore all variables to their original or new values 
    for i in range(len(self._var_list[label])):
        var_ref = self._var_list[label][i]

        if var_ref is None:
            continue
        elif isinstance(var_ref, list):
            for i_2, val in enumerate(var_ref):
                if to_org:
                    self._update_var_value(
                        val, label, i, update_value[i][i_2], to_org,
                    )
                elif not to_org:
                    self._update_var_value(
                        val, label, i, update_value[i], to_org,
                    )
                    break
        else:
            if to_org:
                self._update_var_value(
                    var_ref, label, i, update_value[i][0], to_org,
                )
            else:
                self._update_var_value(
                    var_ref, label, i, update_value[i], to_org,
                )

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
              break
      elif isinstance(target_name, list):
          if frame.f_code.co_name in target_name:
              self._frame = frame.f_back
              break
      elif frame.f_code.co_name == target_name:
         self._frame = frame.f_back
         break 
      
      frame = frame.f_back

   if has_exit:
       return
   elif self._frame is None:
       raise _FrameAccessError()
   
   self._get_trace_info()

def _get_trace_info(self) -> None:
    if self._lineno is None:
        self._lineno = self._frame.f_lineno

    if self._file_name is None:
        self._file_name = self._frame.f_code.co_filename

def _clear_frame(self) -> None:
   # to prevent memory leak by releasing the frame reference
   self._frame = None
   self._lineno = None
   self._file_name = None


