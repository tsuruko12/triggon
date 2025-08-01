import inspect
from threading import Timer
from typing import Any

from ._exceptions import (
    _FrameAccessError,
    _UnsetExitError,
)


def _store_org_value(self, label: str, index: int, org_value: Any) -> None:
    target_index = self._org_value[label][index] 

    if target_index is None:
        self._org_value[label][index] = []

    self._org_value[label][index].append(org_value)

def _update_var_value(
    self, var_ref: tuple[str, ...] | list[tuple[str, ...]], 
    label: str, index: int, update_value: Any, 
    inner_index: int=None, to_org: bool=False,
) -> None:
    # var_ref can be:
    # - (file name, lineno, var name) for globals
    # - (file name, lineno, attr name, instance) for class attributes
    # - a list of either form

    if to_org:
        trig_flag = False
    else:
        trig_flag = True
  
    if len(var_ref) == 4:     
        setattr(var_ref[3], var_ref[2], update_value)
    else:    
        if self._delayed_labels[label] is None:
            self._frame.f_globals[var_ref[2]] = update_value
        else:
            self._delayed_labels[label].f_globals[var_ref[2]] = update_value

    if self.debug:
        if self._delayed_labels[label] is None:
            deley = False
        else:
            deley = True

        self._print_var_debug(
            label, index, trig_flag, inner_index, update_value, deley=deley,
        )

def _label_has_var(
    self, 
    label: str, called_func: str, after: int | float, to_org: bool=False,
) -> None:
    if self._var_list[label] is None:
        return

    self._get_target_frame(called_func)

    if after is None:
        self._update_all_vars(label, to_org)
    else:
        self._delayed_labels[label] = self._frame
        self._frame = None
        Timer(after, self._update_all_vars, args=(label, to_org)).start()

def _update_all_vars(self, label: str, to_org: bool) -> None:
    if to_org:
        update_value = self._org_value[label]
    else:
        # Each index always holds a single value.
        update_value = self._new_value[label]

    # Restore all variables to their original or new values 
    for i in range(len(self._var_list[label])):
        var_ref = self._var_list[label][i]

        if var_ref is None:
            continue
        elif isinstance(var_ref, list):
            if to_org:
                for i_2, val in enumerate(update_value[i]):
                    self._update_var_value(
                        var_ref[i_2], label, i, val, i_2, to_org,
                    )
            else:
                for i_2, val in enumerate(var_ref):
                    self._update_var_value(
                        val, label, i, update_value[i], i_2, to_org,
                    )             
        else:
            if to_org:
                self._update_var_value(
                    var_ref, label, i, update_value[i][0], to_org=to_org,
                )
            else:
                self._update_var_value(
                    var_ref, label, i, update_value[i], to_org=to_org,
                )

def _get_target_frame(
        self, target_name: str | list[str, str], 
        frame: str=None, has_exit: bool=False,
) -> None:
   if self._frame is not None and frame is not None:
      return

   if frame is not None:
       cur_frame = frame
   else:
       cur_frame = inspect.currentframe()

   while cur_frame:
      if has_exit:
          if cur_frame.f_code.co_name == "<module>":
              raise _UnsetExitError()
          elif cur_frame.f_code.co_name == target_name:
              break
      elif isinstance(target_name, list):
          if cur_frame.f_code.co_name in target_name:
              self._frame = cur_frame.f_back
              break
      elif cur_frame.f_code.co_name == target_name:
         self._frame = cur_frame.f_back
         break 
      
      cur_frame = cur_frame.f_back

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


