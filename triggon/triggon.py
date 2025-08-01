from types import FrameType
from typing import Any

from .trig_func import TrigFunc
from ._internal import (
  _debug,
  _err_handler,
  _set_trigger,
  _switch_var,
  _var_analysis,
  _var_update,
)
from ._internal._err_handler import (
  _check_label_type,
  _handle_arg_types, 
)
from ._internal._exceptions import (
  InvalidArgumentError,
  SYMBOL,
  _ExitEarly,
)
from ._internal._sentinel import _no_value


class Triggon:
    debug: bool
    _trigger_flag: dict[str, bool]
    _new_value: dict[str, tuple[Any, ...]]
    _org_value: dict[str, list[Any]]
    _var_list: dict[str, tuple[str, ...] | list[tuple[str, ...]]]
    _delayed_labels: dict[str, str]
    _disable_label: dict[str, bool]
    _return_value: tuple[bool, Any] | None
    _file_name: str
    _lineno: int
    _frame: FrameType

    # `new_value`: Each label holds a tuple of values.
    # `org_value`: Each label index holds a list of values,
    #              or None if unset.
    # `var_list`: Each label index holds a tuple of strings,
    #             a list of such tuples, or None if unset.

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
      self._delayed_labels = {}
      self._disable_label = {}   
      self._return_value = None
      self._file_name = None
      self._lineno = None
      self._frame = None

      change_list = _handle_arg_types(label, new)
      self._scan_dict(change_list)

    def _scan_dict(self, arg_dict: dict[str, Any]) -> None:      
      for key, value in arg_dict.items():          
          index = self._count_symbol(key)

          if index != 0:
              raise InvalidArgumentError(
                  f"Please remove the `*` prefix from `{key}`. " 
                  "To specify by index, "
                  "provide the values in index order using a list or tuple."
              )
          
          self._add_new_label(key, value)

    def _add_new_label(self, label: str, value: Any, /) -> None:
      # The value is normalized to a tuple
      if isinstance(value, (list, tuple)):
        length = len(value)

        if length == 0:
          # An empty sequence is handled as a single value
          length = 1
          self._new_value[label] = (value,)
        else:
          self._new_value[label] = tuple(value)
      else:
        length = 1
        self._new_value[label] = (value,)

      self._trigger_flag[label] = False
      self._delayed_labels[label] = None
      self._disable_label[label] = False

      # Create a list of `None` values—one for each index of this label
      # (`length` is greater than 0)
      self._org_value[label] = [None] * length
      self._var_list[label] = [None] * length

    def set_trigger(
        self, label: str | list[str] | tuple[str, ...], /, 
        *, cond: str=None, after: int | float=None,
    ) -> None:
      """
      Activates the trigger flag for the given labels.

      If variables were registered via `alter_var()`, 
      their values will be updated when the flag is activated.

      If `cond` is provided, it must be a valid comparison expression 
      (e.g., `"x > 10"`, `"obj.count == 5"`). 
      The expression is evaluated safely and the trigger will only be 
      activated if the result is `True`.
      """

      if after is not None and not isinstance(after, (int, float)):
        raise TypeError("The `after` keyword must be `int` or `float`.")

      if isinstance(label, (list, tuple)):
        for name in label:
          _check_label_type(name, allow_dict=False)       
          self._check_label_flag(name, cond, after)
      else:
        _check_label_type(label, allow_dict=False)
        self._check_label_flag(label, cond, after)
        
      self._clear_frame()

    def switch_lit(
        self, label: str | list[str] | tuple[str, ...], /, org: Any, 
        *, index: int=None,
    ) -> Any:
      """
      Changes the value at the specified label(s) and position 
      if the flag is active.

      Only accepts immediate values
      (e.g., literals or expressions).

      Note:
        If multiple labels share the same name,  
        all will be triggered together by `set_trigger()`, 
        regardless of index.  
        In such cases, the one with the smaller index in the sequence takes precedence.  
        This also applies when different labels are active at once.
      """

      cur_functions = ["switch_lit", "alter_literal"] # Will change it after beta

      _check_label_type(label, allow_dict=False)

      if isinstance(label, (list, tuple)):
        for v in label:
          stripped_label = v.lstrip(SYMBOL)
          self._check_exist_label(stripped_label)

          if self._trigger_flag[stripped_label]:
            label = v
            break

        # When all labels' triggers are inactive
        if not isinstance(label, str):
          return org

      name = label.lstrip(SYMBOL)
      self._check_exist_label(name)

      if index is None:
        index = self._count_symbol(label)
      self._compare_value_counts(name, index)

      flag = self._trigger_flag[name]

      if not flag:
        ret_value = org
        new_val = _no_value # for debug
      else:
        ret_value = self._new_value[name][index] 
        new_val = self._new_value[name][index] # for debug

      if self.debug:
        self._get_target_frame(cur_functions)
        self._print_val_debug(name, index, flag, org, new_val)

      return ret_value

    def switch_var(
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

        change_list = _handle_arg_types(label, var, index)
        init_flag = False

        if len(change_list) == 1:
          # When only one label is provided
          label = next(iter(change_list))
          name = label.lstrip(SYMBOL)   

          if index is None:
            index = self._count_symbol(label)

          if not init_flag:
            init_flag = self._init_or_not(name, index)

          trig_flag = self._trigger_flag[name]
          vars = self._var_list[name][index]

          if not trig_flag:
            self._clear_frame()
            return var
          elif not init_flag:
             return var

          self._update_var_value(
            vars, name, index, self._new_value[name][index],
          )      
          self._clear_frame()

          return var
        else:
           # When multiple labels are provided in a dictionary

          if index is not None:
            raise InvalidArgumentError(
              "Cannot use the `index` keyword with a dictionary. " 
              "Use `*` in the label instead." 
            )
          
          for key in change_list.keys():
            name = key.lstrip(SYMBOL)
            index = self._count_symbol(key)

            if not init_flag:
              init_flag = self._init_or_not(name, index)
            
            if not init_flag:
              continue

            trig_flag = self._trigger_flag[name]
            vars = self._var_list[name][index]  

            if not trig_flag:
              continue          

            self._update_var_value(
              vars, name, index, self._new_value[name][index],
            )
            
          self._clear_frame()

    def revert(
          self, label: str | list[str] | tuple[str, ...]=None, /, 
          *, all: bool=False, disable: bool=False,
    ) -> None:
      """
      Revert the trigger flag(s) set by `set_trigger()` back to False.

      Use the `all` keyword to revert all labels at once. 
      If `disable` is set to True, the label(s) will be permanently disabled.
      """

      if label is None:
        if not all:
          raise InvalidArgumentError("No labels specified to revert.")
        
        for key in self._new_value.keys():
          self._revert_label(key, disable)      
      elif isinstance(label, (list, tuple)):
        for name in label:
          self._revert_label(name, disable)
      else:
        self._revert_label(label, disable)  

      self._clear_frame()      

    def _revert_label(self, label: str, disable: bool) -> None:
      _check_label_type(label, allow_dict=False)

      name = label.lstrip(SYMBOL)
      self._check_exist_label(name)

      if not disable and not self._trigger_flag[name]:
        return
      elif disable and self._disable_label[name]:
        return 

      if disable:
        state = "disable"  # for debug
        self._disable_label[name] = True
      else:
        state = "inactive" # for debug
      self._trigger_flag[name] = False

      self._label_has_var(name, "revert", to_org=True)

      if self.debug:
        self._get_target_frame("revert")
        self._print_flag_debug(name, state)    
    
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
        self, label: str, /, ret: Any=None, 
        *, index: int=None, do_print: bool=False,
    ) -> None | Any:
        """
        Executes an early return using the set return value,  
        if the trigger flag is active.

        If `do_print` is True, prints the value with the early return.  
        Raises `TypeError` if the value is not a string.
        """

        name = label.lstrip(SYMBOL)
        self._check_exist_label(name)

        if index is None:
           index = self._count_symbol(label)

        if not self._trigger_flag[name]:
            return 
            
        if do_print:
           if ret is None and not isinstance(self._new_value[name][index], str):
             raise TypeError(
                "Expected a value of type `str`, "
                f"but got `{type(self._new_value[name][index]).__name__}`."
             )   
           elif ret is not None and not isinstance(ret, str):
             raise TypeError(
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

        self._get_target_frame("exit_point", has_exit=True)

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
        
    # Old functions
    alter_literal = switch_lit
    alter_var = switch_var


modules = [
  _debug, 
  _err_handler, 
  _set_trigger, 
  _switch_var, 
  _var_analysis, 
  _var_update,
]

for module in modules:
  for name, func in vars(module).items():
      if callable(func):
          setattr(Triggon, name, func)