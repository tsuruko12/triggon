from types import FrameType
from typing import Any

from .trig_func import TrigFunc
from ._internal._err_handler import (
    _count_symbol,
    _ensure_after_type,
    _ensure_index_type,
    _ensure_label_type,
    _ensure_var_type,
    _normalize_arg_types, 
)
from ._internal._exceptions import (
  InvalidArgumentError, 
  InvalidClassVarError,
  SYMBOL,
  _ExitEarly,
)
from ._internal._methods import _bind_to_triggon
from ._internal._sentinel import _NO_VALUE
from ._internal._var_update import _is_delayed_func


class Triggon:
    debug: bool
    _trigger_flags: dict[str, bool]
    _new_values: dict[str, tuple[Any, ...]]
    _org_values: dict[str, list[Any]]
    _var_refs: dict[str, tuple[str, ...] | list[tuple[str, ...]]]
    _delay_info: dict[str, str]
    _disable_flags: dict[str, bool]
    _return_values: tuple[bool, Any] | None
    _file_name: str
    _lineno: int
    _frame: FrameType

    # 'new_values': Each label holds a tuple of values.
    # 'org_values': Each label index holds a list of values,
    #              or None if unset.
    # 'var_refs': Each label index holds a tuple of strings,
    #             a list of such tuples, or None if unset.
    # 'delay_info': Each label holds a list containing one or two frames
    #               for delayed triggers, or None if not delayed.

    def __init__(
        self, label: str | dict[str, Any], /, new: Any = None, 
        *, debug: bool | str | list[str] | tuple[str, ...] = False,
    ) -> None:
      """
      Register the given labels with their corresponding values.

      Values must be passed in the order of their index positions.
      To treat a sequence as a single value, wrap it in another sequence.

      Accepted formats:
          - label, value
          - label, [value]
          - label, (value,)
          - {label: value}
          - {label: [value]}
          - {label: (value,)}

      Keyword Args:
          debug:
              If set to True, print labels for tracing in real time.  
              If label names are passed, print only those labels.
      """

      self.debug = debug
      self._trigger_flags = {}
      self._new_values = {}
      self._org_values = {}
      self._var_refs = {}  
      self._delay_info = {}
      self._disable_flags = {}   
      self._return_values = None
      self._file_name = None
      self._lineno = None
      self._frame = None

      changed_items = _normalize_arg_types(label, new)
      self._scan_dict(changed_items)

    def _scan_dict(self, arg_dict: dict[str, Any]) -> None:      
      for key, value in arg_dict.items():          
          index = _count_symbol(key)

          if index != 0:
              raise InvalidArgumentError(
                  f"Please remove the '*' prefix from '{key}'. " 
                  "To specify by index, "
                  "provide the values in index order using a list or tuple."
              )
       
          self._add_new_label(key, value)

      if not isinstance(self.debug, bool):
        self._ensure_debug_type()

    def _add_new_label(self, label: str, value: Any) -> None:
      # Normalized to a tuple
      if isinstance(value, (list, tuple)):
        length = len(value)
        if length == 0:
          # An empty sequence is handled as a single value
          length = 1
          self._new_values[label] = (value,)
        else:
          self._new_values[label] = tuple(value)
      else:
        length = 1
        self._new_values[label] = (value,)

      self._trigger_flags[label] = False
      self._disable_flags[label] = False
      # [[trigger_frame_info], [revert_frame_info]] for delayed triggers
      self._delay_info[label] = [None, None]

      # Create a list of None values—one for each index of this label
      # (length is greater than 0)
      self._org_values[label] = [None] * length
      self._var_refs[label] = [None] * length

    def set_trigger(
        self, 
        label: str | list[str] | tuple[str, ...] = None, 
        /, 
        *, 
        all: bool = False,
        index: int = None, 
        cond: str = None, 
        after: int | float = None,
    ) -> None:
      """
      Activate the labels.

      Values are switched only if the variables were registered 
      via switch_var().

      Keyword Args:
          all:
              Activate all labels.
          
          index:
              Specify the index to apply to all given labels 
              to switch variable values.

            Note: 
                Applies only to variables already registered with switch_var().
                Does not apply if the variable is not registered,
                or if the value is handled by switch_lit().
          
          cond:
              Specify a condition for activating the label.
              Must be a valid comparison expression
              (e.g., "x > 10", "obj.count == 5"). 
              The labels are active if the result is True.

          after:
              Set the delay in seconds before labels become active.

              Note: 
                  The actual execution occurs approximately 0.011 seconds later 
                  than the specified time.
      """

      _ensure_index_type(index)
      _ensure_after_type(after)
      if not isinstance(all, bool):
        raise TypeError("'all' is must be a bool.")
      
      if all:
        labels = self._trigger_flags.keys()
      else:
        if label is None:
          raise TypeError("No labels specified.")
        _ensure_label_type(label)
        
        if isinstance(label, (list, tuple)):
          labels = [v.lstrip(SYMBOL) for v in label]
        else: 
          labels = [label.lstrip(SYMBOL)]

        self._ensure_label_exists(labels)

      if index is not None:
        self._compare_value_counts(labels, index)

      self._update_or_skip(labels, index, cond, after) 
      self._clear_frame()

    def is_triggered(
        self, *label: str,
    ) -> bool | list[bool] | tuple[bool, ...]:
      """
      Return True if the given label is active; otherwise return False.

      If multiple labels are given, return a list or tuple of booleans,
      matching the input type.
      """

      _ensure_label_type(label, unpack=True)
      self._ensure_label_exists(label, unpack=True)

      if isinstance(label[0], list):
        return [self._trigger_flags[v] for v in label[0]]
      if isinstance(label[0], tuple):
        return tuple(self._trigger_flags[v] for v in label[0])
      if len(label) > 1:
        return tuple(self._trigger_flags[v] for v in label)
      return self._trigger_flags[label[0]]

    def switch_lit(
        self, label: str | list[str] | tuple[str, ...], /, org: Any, 
        *, index: int = None,
    ) -> Any:
      """
      Switche to the value registered when the instance is created 
      for the given label and index if the label is active.

      Also supports switching to a function.
      If the function is delayed by TrigFunc, execute it and return its result.

      Note:
          If multiple labels are given and more than one of them is active,
          the one with the lower index in the sequence takes priority. 
      """

      self._get_marks(init=True) # For debug

      _ensure_label_type(label)
      _ensure_index_type(index)

      if isinstance(label, (list, tuple)):
        for v in label:
          stripped_label = v.lstrip(SYMBOL)
          self._ensure_label_exists(stripped_label)

          if self._trigger_flags[stripped_label]:
            label = v
            break

        # When all labels' triggers are inactive
        if not isinstance(label, str):
          self._get_marks(label, index, org, strip=True)
          return org

      name = label.lstrip(SYMBOL)
      self._ensure_label_exists(name)

      if index is None:
        index = _count_symbol(label)
      self._compare_value_counts(name, index)

      flag = self._trigger_flags[name]
      if not flag:
        ret_value = org
        self._get_marks(name, index, org)
      else:
        ret_value = self._new_values[name][index] 
        self._get_marks(name, index, org, ret_value)
    
      if _is_delayed_func(ret_value):
          return ret_value()
      return ret_value

    def switch_var(
          self, label: str | dict[str, Any], var: Any = None, /, 
          *, index: int = None,
    ) -> Any:
        """
        Register the variables for the labels and their specified indices.

        On the first registration, the activated labels are switched 
        to their index values when the instance is created.

        Supports only variable references (not literals or expressions).

        Keyword Args:
            index:
                Specify the index value for the given label 
                to register the variable.  
                When the value is updated, that index value is applied.

                If multiple indices are passed, 
                register all of them for the label.  
                When the value is updated, 
                the first index in the tuple is applied.

        Returns:
            When a single label is passed, return the variable's value.
            Otherwise, return None.

            If the value is a function delayed with TrigFunc, 
            execute it and return its result.
        """

        # Multiple indices are supported in the implementation,
        # but they have no practical use, so they currently raise an error.

        changed_items = _normalize_arg_types(label, var, index)
        has_looped = False

        # Normalize to a tuple
        if index is not None:
          if isinstance(index, int):
            i = (index,)
          elif isinstance(index, range):
            i = tuple(index)
          else:
            i = index

        if len(changed_items) == 1:
          single_key = True
        else:
          single_key = False

        for key, value in changed_items.items():
            name = key.lstrip(SYMBOL)

            if index is None:
              i = (_count_symbol(key),)

            if not has_looped:
              init_flag = self._init_or_not(name, i)         
              if not init_flag:
                if not single_key:
                  continue
                self._clear_frame()

                if _is_delayed_func(value):
                    return value()              
                return value
              
            has_looped = True

            trig_flag = self._trigger_flags[name]
            var_ref = self._var_refs[name][i[0]]  

            if not trig_flag and self._delay_info[name][0] is None:
              if not single_key:
                continue     

              self._clear_frame()

              if _is_delayed_func(value):
                  return value()
              return value

            if self._delay_info[name][0] is None:   
              if isinstance(var_ref, list):
                  for v in var_ref:
                      self._update_var_value(
                          v, label, i[0], self._new_values[name][i[0]],
                      )
              else:
                  self._update_var_value(
                      var_ref, label, i[0], self._new_values[name][i[0]],
                  )
              ret_value = self._new_values[name][i[0]]
            else:
              ret_value = value

            if single_key:
              self._clear_frame()

              if _is_delayed_func(ret_value):
                return ret_value()
              return ret_value

        self._clear_frame()

    def is_registered(
        self, *variable: str,
    ) -> bool | list[bool] | tuple[bool, ...]:
      """
      Return True if the variable is registered; otherwise return False.

      If multiple variables are given, return a list or tuple of booleans,
      matching the input type.
      """

      vars = _ensure_var_type(variable)
      self._get_target_frame("is_registered")

      result = []
      for var in vars:
        is_glob = False
        if "." in var:
          (left, right) = var.split(".")

          class_inst = self._frame.f_locals.get(left)
          if class_inst is None:
              glob_inst = self._frame.f_globals.get(left)
              if glob_inst is None:
                result.append(False)
                continue
              is_glob = True
              class_inst = glob_inst.__name__
          elif isinstance(class_inst, type):
            is_glob = True
            class_inst = class_inst.__name__
          result.append(
            self._check_var_refs(class_inst, right, is_glob)
          )
        else:
          try:
            self._frame.f_globals[var]
          except KeyError:
            result.append(False)
          else:
            result.append(self._check_var_refs(var)) 

      self._clear_frame()

      if len(result) == 1:
        return result[0]
      return result
            
    def revert(
          self, 
          label: str | list[str] | tuple[str, ...] = None, 
          /, 
          *, 
          all: bool = False, 
          disable: bool = False, 
          cond: str = None,
          after: int | float = None,
    ) -> None:
      """
      Deactivate the labels.

      Keyword Args:
          all:
              Deactivate all labels.

          disable:
              Permanently disable labels.
              set_trigger() ignores this when the labels are in this state.

          cond:
              Specify a condition for deactivating labels.
              Must be a valid comparison expression
              (e.g., "x > 10", "obj.count == 5"). 
              The labels are inactive if the result is True.

          after:
              Set the delay in seconds before labels become inactive.

              Note: 
                  The actual execution occurs approximately 0.011 seconds later 
                  than the specified time.
      """

      _ensure_after_type(after)
      if not isinstance(disable, bool):
        raise TypeError("'disable' is must be a bool.")
      if not isinstance(all, bool):
        raise TypeError("'all' is must be a bool.")

      if all:
        labels = tuple(self._trigger_flags.keys())
      else:
        if label is None:
          raise InvalidArgumentError("No labels specified.")
        _ensure_label_type(label)

        if isinstance(label, (list, tuple)):
          labels = [v.lstrip(SYMBOL) for v in label]
        else:
          labels = [label.lstrip(SYMBOL)]

        self._ensure_label_exists(labels)

      self._revert_or_skip(labels, disable, cond, after)     
      self._clear_frame()
    
    def exit_point(self, func: TrigFunc) -> Any:
      """
      Handle an early return, triggered by trigger_return().

      Returns:
          The result of trigger_return().
      """

      if not _is_delayed_func(func):
        raise TypeError(
          "'func' must be a function wrapped in a TrigFunc instance."
        )

      try:
          return func()
      except _ExitEarly:
          if _is_delayed_func(self._return_values):
              return self._return_values()
          return self._return_values

    def trigger_return(
        self, label: str | list[str] | tuple[str, ...], /, 
        ret: Any = _NO_VALUE, *, index: int = None,
    ) -> Any:
        """
        Trigger an early return with the value provided at instance creation
        if the labels are active.

        Returns:
            The value set in the class instance.  
            If 'ret' is passed, it is returned instead.
        """

        _ensure_label_type(label)
        _ensure_index_type(index)

        if isinstance(label, str):
           label = [label]

        for v in label:
          name = v.lstrip(SYMBOL)
          self._ensure_label_exists(name)

          if index is None:
            index = _count_symbol(label)
          self._compare_value_counts(name, index)

          if not self._trigger_flags[name]:
              return 

          if ret is _NO_VALUE:
            ret_value = self._new_values[name][index]
          else:
            ret_value = ret                        
          self._return_values = ret_value

          self._get_target_frame("exit_point", has_exit=True)
          self._debug_trig_return(name)

          raise _ExitEarly 
        
    def trigger_func(
        self, label: str | list[str] | tuple[str, ...], /, func: TrigFunc,
    ) -> Any:
        """
        Call the function if the labels are active.

        Returns:
            The result of the given function.
        """

        if not _is_delayed_func(func):
          raise TypeError(
            "'func' must be a function wrapped in a TrigFunc instance."
          )
        _ensure_label_type(label)

        if isinstance(label, str):
           label = [label]

        for v in label:
          name = v.lstrip(SYMBOL)
          self._ensure_label_exists(name)

          if self._trigger_flags[name]:
              self._debug_trig_func(name, func)            
              return func()


_bind_to_triggon(Triggon)
