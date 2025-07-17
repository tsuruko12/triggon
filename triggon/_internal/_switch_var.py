import ast
from typing import Any

from ._err_handler import _count_symbol
from ._exceptions import SYMBOL

def _init_or_not(
        self, 
        label: str, index: int, data: dict[str, Any], 
        org_val: Any, arg_type: ast.AST,
) -> bool:
    if len(data) == 1:
        shared_index = index
    else:
        shared_index = None   

    mult_flag = _is_mult_vars(org_val)
    
    if mult_flag:
        target_val = org_val[0]
    else:
        target_val = org_val

    if (
        self._var_list[label][index] is None or 
        self._is_new_var(label, index, target_val)
    ):  
        self._get_target_frame(["switch_var", "alter_var"]) # Will change it after beta
        self._lineno = self._frame.f_lineno     

        # Initial process to store argument variables 
        self._init_arg_list(data, arg_type, shared_index)
 
        if shared_index is None:
            for key, val in data.items():
                name = key.lstrip(SYMBOL)
                index = _count_symbol(key)

                if mult_flag:
                    for v in val:
                        if self._org_value[name][index] is None:
                            self._store_org_value(name, index, v)
                else:
                    self._store_org_value(name, index, val)
                                
                self._find_match_var(name, index)
        else:
            self._store_org_value(label, index, data[label])
            self._find_match_var(label, index)

        return True
    
    return False

def _is_new_var(self, label: str, index: int, value: Any) -> bool:
    # The new value to be set
    if self._trigger_flag[label]:
        if self._new_value[label][index] == value:
            return False
        
        return True  
        
    # The original value to be set
    if isinstance(value, list):
        if self._org_value[label][index] == value:
            return False
    elif isinstance(value, tuple):
        if tuple(self._org_value[label][index]) == value:
            return False
    elif self._org_value[label][index] == value:
            return False
    
    return True

# Will update list type annotation later

def _find_match_var(
        self, label: str=None, index: int=None, 
        target_ref: tuple[str, ...]=None, init: bool=False,
) -> None | bool:
    # Used to retrieve the original value for `revert()`
    # or check if `target_ref` is already registered for a specific label.

    if not init:
      # it can be a list or tuple
      var_ref = self._var_list[label][index]
    else:
        # it always be a tuple
        var_ref = target_ref

    stop_flag = False

    # `value` is a list
    for key, value in self._var_list.items(): 
        if stop_flag and not init:
            return
        elif stop_flag and init:
            return False
        elif init and key != label:
            continue

        if key == label:
            stop_flag = True

        # `list_val` is a list or tuple or None
        for i, list_val in enumerate(value):
            if list_val is None:
                continue
            elif isinstance(list_val, tuple) and isinstance(var_ref, tuple):
                if self._is_ref_match(list_val, var_ref):
                    if not init:
                        self._org_value[label][index] = self._org_value[key][i]     
                    else:
                        return True

            elif isinstance(list_val, tuple) and isinstance(var_ref, list):
                for i_2, ref_v in enumerate(var_ref):
                    if self._is_ref_match(list_val, ref_v):
                        self._org_value[label][index][i_2] = (
                            self._org_value[key][i]
                        )
            elif isinstance(list_val, list) and isinstance(var_ref, tuple):
                for i_2, l_v in enumerate(list_val):
                    if self._is_ref_match(l_v, var_ref):
                        if not init:
                            self._org_value[label][index] = (
                                self._org_value[key][i][i_2]
                            )
                        else:
                            return True
            else:
                for ref_i, ref_val in enumerate(var_ref):
                    for list_i, v in enumerate(list_val):
                        if self._is_ref_match(v, ref_val):                           
                            self._org_value[label][index][ref_i] = (
                                self._org_value[key][i][list_i]
                            )

def _is_ref_match(
        self,
        list_val: tuple[str, ...], target_val: tuple[str, ...],
) -> bool:
    if len(list_val) == 2 and len(target_val) == 2:
        return list_val[1] == target_val[1]

    elif len(list_val) == 3 and len(target_val) == 3:
        return list_val[1:] == target_val[1:]
    

def _is_mult_vars(value: Any) -> bool:
  if isinstance(value, (list, tuple)):
    if len(value) > 1:
      return True
    
    return False
  
  return False