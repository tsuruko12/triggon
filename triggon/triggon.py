from types import FrameType
from typing import Any

from ._exceptions import (
    LABEL_TYPE_ERROR,
    SYMBOL,
    _ExitEarly,
    InvalidArgumentError, 
    _check_label_type,
    _compare_value_counts,
    _count_symbol,
    _handle_arg_types,
)
from . import _debug
from . import _var_analysis
from . import _var_update
from .trig_func import TrigFunc


class Triggon:
    debug: bool
    _debug_var: dict[str, tuple[int, str] | list[tuple[int, str]]]
    _trigger_flag: dict[str, bool]
    _new_value: dict[str, tuple[Any]]
    _org_value: dict[str, tuple[Any]]
    _var_list: dict[str, tuple[str]]
    _disable_label: dict[str, bool]
    _id_list: dict[str, int | tuple[int]]
    _return_value: tuple[bool, Any] | None = None
    _lineno: int = None
    _frame: FrameType = None

    def __init__(
        self, label: str | dict[str, Any], /, new: Any=None, 
        *, debug: bool=False,
    ) -> None:
      """
      Registers labels and their corresponding values.

      Values must be passed in the order of their index positions.
      To treat a sequence as a single value, wrap it in another sequence.

      Accepted formats:
      - label, value
      - label, [value]
      - label, (value,)
      - {label: value}
      - {label: [value]}
      - {label: (value,)}
      """

      self.debug = debug
      self._trigger_flag = {}
      self._new_value = {}
      self._org_value = {}
      self._var_list = {}  
      self._disable_label = {}   
      self._id_list = {}

      change_list = _handle_arg_types(label, new)
      self._scan_dict(change_list)

    def _scan_dict(self, arg_dict: dict[str, Any]) -> None:      
      for key, value in arg_dict.items():          
          label = key.lstrip(SYMBOL)
          index = _count_symbol(key)

          if index != 0:
              raise InvalidArgumentError(
                  f"Please remove the '*' prefix from `{key}`. " 
                  "To specify by index, "
                  "provide the values in index order using a list or tuple."
              )

          try:
            self._new_value[label]

            raise InvalidArgumentError(
              f"`{label}` already exists." 
              "Duplicate labels are not allowed for this function."
            ) 
          except KeyError:
            self._add_new_label(label, value)

    def _add_new_label(self, label: str, value: Any, /) -> None:
      if isinstance(value, (list, tuple)):
        length = len(value)
      else:
        length = 1

      if isinstance(value, list) and length > 1: 
        self._new_value[label] = tuple(value)
      elif isinstance(value, tuple) and length > 1:
        self._new_value[label] = value
      elif isinstance(value, list) and length == 1:
        if isinstance(value[0], (list, tuple)):
          self._new_value[label] = value
        else:
          self._new_value[label] = (value[0],)
      elif isinstance(value, tuple) and length == 1:
        if isinstance(value[0], (list, tuple)):
          self._new_value[label] = value 
        else:
          self._new_value[label] = value
      else:
        # Unwrapped single value
        self._new_value[label] = (value,)
        
      self._trigger_flag[label] = False
      self._disable_label[label] = False

      # Create a list of None values—one for each index of this label
      self._org_value[label] = [None] * length
      self._var_list[label] = [None] * length
      self._id_list[label] = [None] * length

    def set_trigger(
        self, label: str | list[str] | tuple[str, ...], /,
    ) -> None:
      """
      Activates the trigger flag for the given label(s).

      If variables were registered via `alter_var()`, 
      their values will be updated when the flag is activated.
      """
    
      if isinstance(label, (list, tuple)):
        for name in label:
          if not isinstance(name, str):
             raise InvalidArgumentError(LABEL_TYPE_ERROR)

          self._check_label_flag(name)
      elif isinstance(label, str):
        self._check_label_flag(label)       
      else:
        raise InvalidArgumentError(LABEL_TYPE_ERROR)
      
      self._clear_frame()

    def alter_literal(
        self, label: str, /, org: Any, *, index: int=None,
    ) -> Any:
      """
      Changes the value at the specified label and position 
      if the flag is active.

      Only accepts immediate values
      (e.g., literals or expressions).
      """

      _check_label_type(label)
      
      name = label.lstrip(SYMBOL)
      self._check_exist_label(name)

      if index is None:
        index = _count_symbol(label)
      _compare_value_counts(self._new_value[name], index)

      self._org_value[name][index] = org
      flag = self._trigger_flag[name]

      if self.debug:
        self._get_target_frame("alter_literal")
        self._print_val_debug(name, index, flag, org)
        self._clear_frame()

      if not flag:
        return self._org_value[name][index]

      return self._new_value[name][index]  

    def alter_var(
          self, label: str | dict[str, Any], var: Any=None, /, 
          *, index: int=None,
    ) -> None | Any:
        """
        Change the value of variables associated with the given label 
        if the flag is active.

        Only supports variable references (not literals or expressions).

        Supports updating:
        - Global variables
        - Class attributes (fields)
        """

        (change_list, arg_type) = _handle_arg_types(label, var, index, True)
        init_flag = False

        if len(change_list) == 1:
          # When only one label is provided
          label = next(iter(change_list))
          _check_label_type(label)

          name = label.lstrip(SYMBOL)
          self._check_exist_label(name)

          if index is None:
            index = _count_symbol(label)
          _compare_value_counts(self._new_value[name], index)

          if (
            self._var_list[name][index] is None 
            or self._is_new_var(name, index, var)
          ):
            self._store_org_value(name, index, change_list[label])
 
            self._get_target_frame("alter_var")
            self._lineno = self._frame.f_lineno     

            # Initial process to store argument variables 
            self._init_arg_list(change_list, arg_type, index)
            init_flag = True

          trig_flag = self._trigger_flag[name]
          vars = self._var_list[name][index]

          if not trig_flag:
            if self.debug:
              self._get_target_frame("alter_var")

              self._print_var_debug(
                vars, name, index, trig_flag, change_list[label],
              )   
            self._clear_frame()

            return var
          elif not init_flag:
             return var

          self._update_var_value(vars, self._new_value[name][index])  

          if self.debug:
            self._print_var_debug(
              vars, name, index, trig_flag, change_list[label], 
              self._new_value[name][index], change=True,
            )
          self._clear_frame()

          return var
        else:
           # When multiple labels are provided in a dictionary

          if index is not None:
            raise InvalidArgumentError(
              "Cannot use the `index` keyword with a dictionary. " 
              "Use '*' in the label instead." 
            )
          
          for key, val in change_list.items():
            _check_label_type(key)
            
            name = key.lstrip(SYMBOL)
            index = _count_symbol(key)

            if self._org_value[name][index] is None:
              self._store_org_value(name, index, val)

            if (
               not init_flag
               and (self._var_list[name][index] is None 
               or self._is_new_var(name, index, val))
            ):    
              self._get_target_frame("alter_var")
              self._lineno = self._frame.f_lineno

              # Initial process to store argument variables
              self._init_arg_list(change_list, arg_type)
              init_flag = True
            
            if not init_flag:
              continue

            trig_flag = self._trigger_flag[name]
            vars = self._var_list[name][index]  

            if not trig_flag:
              if self.debug:
                self._get_target_frame("alter_var")
                self._print_var_debug(vars, name, index, trig_flag, val)

              continue          

            self._update_var_value(vars, self._new_value[name][index])

            if self.debug:
              self._get_target_frame("alter_var")

              self._print_var_debug(
                vars, name, index, trig_flag, val, 
                self._new_value[name][index], change=True,
              )
            
          self._clear_frame()

    def revert(
          self, label: str | list[str] | tuple[str, ...], /, 
          *, disable: bool=False,
    ) -> None:
      """
      Revert the trigger flag of the specified label to False.
      If `disable` is set to True, the label will be permanently disabled.
      """

      if isinstance(label, (list, tuple)):
        for name in label:
          if not isinstance(name, str):
            raise InvalidArgumentError(LABEL_TYPE_ERROR)
          
          self._revert_label(name, disable)
      elif isinstance(label, str):
        self._revert_label(label, disable)
      else:
        raise InvalidArgumentError(LABEL_TYPE_ERROR)        

    def _revert_label(self, label: str, disable: bool) -> None:
      name = label.lstrip(SYMBOL)
      self._check_exist_label(name)

      if not self._trigger_flag[name]:
        return

      if disable:
        state = "disable" # for debug
        self._disable_label[name] = True
      else:
        state = "inactive" # for debug
      self._trigger_flag[name] = False

      self._label_has_var(name, "revert", True)

      if self.debug:
        self._get_target_frame("revert")
        self._print_flag_debug(name, state)    
        self._clear_frame()  
    
    def exit_point(self, label: str, func: TrigFunc, /) -> None | Any:
      """
      Handles an early return triggered by `trigger_return()`,  
      based on the specified label.
      """

      name = label.lstrip(SYMBOL)
      self._check_exist_label(name)

      try:
          return func()
      except _ExitEarly:
          if not self._return_value[0]:
              return self._return_value[1]
          
          print(self._return_value[1])

    def trigger_return(
        self, label: str, /, ret=None, *, index: int=None, do_print: bool=False,
    ) -> None | Any:
        """
        Executes an early return using the set return value,  
        if the trigger flag is active.

        If `do_print` is True, prints the value with the early return.  
        Raises `InvalidArgumentError` if the value is not a string.
        """

        name = label.lstrip(SYMBOL)
        self._check_exist_label(name)

        if index is None:
           index = _count_symbol(label)

        if not self._trigger_flag[name]:
            return 
            
        if do_print:
           if ret is None and not isinstance(self._new_value[name][index], str):
             raise InvalidArgumentError(
                "Expected a value of type `str`, "
                f"but got `{type(self._new_value[name][index]).__name__}`."
             )   
           elif ret is not None and not isinstance(ret, str):
             raise InvalidArgumentError(
                "Expected a value of type `str`, "
                f"but got `{type(ret).__name__}`."
             )

        if ret is None:
          value = self._new_value[name][index]
        else:
          value = ret   
                    
        self._return_value = (do_print, value)

        if self.debug:
          self._get_target_frame("trigger_return")
          self._print_trig_debug(name, "Return")

        raise _ExitEarly 
        
    def trigger_func(self, label: str, func: TrigFunc, /) -> None | Any:
        """
        Executes the given function 
        if the trigger flag for the label is active.
        """

        name = label.lstrip(SYMBOL)
        self._check_exist_label(name)

        if self._trigger_flag[name]:
            if self.debug:
              self._get_target_frame("trigger_func")
              self._print_trig_debug(name, "Trigger a function") 
                    
            return func()


for name, func in vars(_var_analysis).items():
    if callable(func):
        setattr(Triggon, name, func)


for name, func in vars(_debug).items():
    if callable(func):
        setattr(Triggon, name, func)


for name, func in vars(_var_update).items():
    if callable(func):
        setattr(Triggon, name, func)