import inspect
from threading import Timer
from typing import Any

from ._exceptions import (
    _FrameAccessError,
    _UnsetExitError,
)


def _store_org_value(self, label: str, index: int, org_value: Any) -> None:
    target_index = self._org_values[label][index] 

    if target_index is None:
        self._org_values[label][index] = []

    self._org_values[label][index].append(org_value)

def _update_var_value(
    self, 
    var_ref: tuple[str, ...] | list[tuple[str, ...]], 
    label: str, 
    index: int, 
    update_value: Any, 
    inner_index: int = None, 
    to_org: bool = False,
) -> None:
    # var_ref can be:
    # - (file name, lineno, var name) for globals
    # - (file name, lineno, attr name, instance) for class attributes
    # - a list of either form

    if to_org:
        trig_flag = False
        i = 1
    else:
        trig_flag = True
        i = 0
  
    if len(var_ref) == 4:   
        setattr(var_ref[3], var_ref[2], update_value)
    else:    
        if self._delay_info[label][i] is None:
            self._frame.f_globals[var_ref[2]] = update_value
        else:
            self._delay_info[label][i].f_globals[var_ref[2]] = update_value

    if self.debug:
        if self._delay_info[label][i] is None:
            deley = False
        else:
            deley = True

        self._print_var_debug(
            label, index, trig_flag, inner_index, update_value, deley=deley,
        )

def _label_has_var(
    self, label: str, called_func: str, after: int | float, 
    index: int = None, to_org: bool = False,
) -> None:
    if after is None and self._var_refs[label] is None:
        return
    
    self._get_target_frame(called_func)   

    if after is None:            
        self._update_all_vars(label, index, to_org)
    else:
        if to_org:
            self._delay_info[label][1] = self._frame
        else:
            self._delay_info[label][0] = self._frame

        if self._var_refs[label] is None:
            return

        Timer(
            after, self._update_all_vars, args=(label, index, to_org),
        ).start()

def _update_all_vars(
        self, label: str, index: int | None, to_org: bool,
) -> None:
    if to_org:
        update_value = self._org_values[label]
    else:
        # Each index always holds a single value.
        update_value = self._new_values[label]

    # Restore all variables to their original or new values 
    for i in range(len(self._var_refs[label])):
        var_ref = self._var_refs[label][i]

        if var_ref is None:
            continue
        elif isinstance(var_ref, list):
            if to_org:
                for i_2, val in enumerate(update_value[i]):
                    self._update_var_value(
                        var_ref[i_2], label, i, val, i_2, to_org,
                    )
            else:
                if index is not None:
                    i = index

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
                if index is not None:
                    i = index
                    
                self._update_var_value(
                    var_ref, label, i, update_value[i], to_org=to_org,
                )

    if to_org and self._delay_info[label][1] is not None:
        self._delay_info[label][1] = None
    elif not to_org and self._delay_info[label][0] is not None:
        self._delay_info[label][0] = None

def _get_target_frame(
        self, target_name: str | list[str, str], has_exit: bool = False,
) -> None:
   if self._frame is not None:
      return

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


