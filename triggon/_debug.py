from typing import Any


LOG_DEBUG = "【Debug】 [Line]: {lineno}, [Function]: `{func}`, "

LOG_FLAG = LOG_DEBUG + "[State]: Label `{label}` is {state}"

LOG_TRIG = LOG_DEBUG + "[Label]: `{label}`, [Action]: {action}"

LOG_VALUE = (
  LOG_DEBUG 
  + "[Label]: `{label}` (index {num}), [Flag]: {state}, [Value]: {value}"
)

LOG_VAR = (
  LOG_DEBUG 
  + "[Label]: `{label}` (index {num}), "
  "[Flag]: {state}, [Variable]: `{var}`, [Value]: {value}"
)


def _get_debug_info(self) -> str:
   # only used debug mode
   func_name = self._frame.f_code.co_name

   if self._lineno is None:
      self._lineno = self._frame.f_lineno

   return func_name

def _get_var_name(
      self, var_ref: tuple[str, ...] | list[tuple[str, ...]], value: Any=None,
) -> str | tuple[list[str], list[Any]]:
   if isinstance(var_ref, list):
      var_names = []
      var_values = []
  
      for i, val in enumerate(var_ref):
         if val[0] != self._lineno:
            continue
         elif len(val) == 2 and globals()[val[1]] == value[i]:
            if len(var_ref) == 3:
              class_name = var_ref[2].__class__.__name__
              var_names.append(f"{class_name}.{val[1]}")
            else:
              var_names.append(val[1])

            var_values.append(value[i])
         elif len(val) == 3 and val[2].__dict__[val[1]] == value[i]:
            if len(var_ref) == 3:
              class_name = var_ref[2].__class__.__name__
              var_names.append(f"{class_name}.{val[1]}")
            else:
              var_names.append(val[1])

            var_values.append(value[i])

      return (var_names, var_values)
   else:
      if len(var_ref) == 3:
         class_name = var_ref[2].__class__.__name__
         return f"{class_name}.{var_ref[1]}"
      
      return var_ref[1]

def _print_flag_debug(self, label: str, state: str, reset: bool=True) -> None:
    func_name = self._get_debug_info()

    print(
        LOG_FLAG.format(
           lineno=self._lineno, func=func_name, label=label, state=state,
        )
    )

    if reset:
       self._clear_frame()

def _print_val_debug(
      self, label: str, index: int, flag: bool, org_value: Any,
) -> None:
   if flag:
      value = f"{repr(org_value)} -> {repr(self._new_value[label][index])}"
   else:
      value = repr(org_value)

   func_name = self._get_debug_info()

   print(
      LOG_VALUE.format(
         lineno=self._lineno, func=func_name, label=label, 
         num=index, state=flag, value=value,
      )
   )
   self._clear_frame()

def _print_var_debug(
      self, target_index: tuple[Any] | list[tuple[Any]], 
      label: str, index: int, flag: bool, 
      org_value: Any, new_value: Any=None, change: bool=False,
) -> None:
   func_name = self._get_debug_info()

   if isinstance(org_value, (list, tuple)):
      (var_names, var_values) = self._get_var_name(target_index, org_value)

      for i, var in enumerate(var_names):
         if change:
            value = f"{repr(var_values[i])} -> {repr(new_value)}"
         else:
            value = repr(var_values[i])
            print(
               LOG_VAR.format(
                  lineno=self._lineno, func=func_name, 
                  label=label, num=index, 
                  state=flag, var=var, value=value,
               )
            )
   else:
    var_name = self._get_var_name(target_index)

    if change:
        value = f"{repr(org_value)} -> {repr(new_value)}"
    else:
        value = repr(org_value)

    print(
        LOG_VAR.format(
           lineno=self._lineno, func=func_name, 
           label=label, num=index, 
           state=flag, var=var_name, value=value,
        )
    )  

def _print_trig_debug(self, label: str, action: str) -> None:
    func_name = self._get_debug_info()

    print(
        LOG_TRIG.format(
           lineno=self._lineno, func=func_name, label=label, action=action,
        )
    )
    self._clear_frame()

