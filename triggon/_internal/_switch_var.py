def _init_or_not(self, label: str, index: int) -> bool:
    self._get_target_frame(["switch_var", "alter_var"]) # Will change it after beta 

    self._check_exist_label(label)  

    if (
        self._var_list[label][index] is None 
        or self._is_new_var(label, index)
    ):  
        # Initial process to store argument variables 
        self._trace_func_call()
        return True
    
    return False

def _is_new_var(
        self, label: str, index: int, target_ref: tuple[str, ...]=None,
) -> bool:
    # If both the file name and line number match,
    # the variable is already registered.

    var_ref = self._var_list[label][index]

    if isinstance(var_ref, tuple):
        if target_ref is not None:
            if target_ref[:3] == var_ref[:3]:
                return False
            else:
                return True
        elif var_ref[0] == self._file_name and var_ref[1] == self._lineno:
            return False
        
        return True
    
    for ref in var_ref:
        if target_ref is not None:
            if target_ref[:3] == var_ref[:3]:
                return False
        elif ref[0] == self._file_name and ref[1] == self._lineno:
            return False
        
    return True

def _find_match_var(
        self, 
        label: str=None, index: int=None, target_ref: tuple[str, ...]=None,
) -> None:
    # Used to retrieve the original value for `revert()`

    # it can be a list or tuple
    var_ref = self._var_list[label][index]

    # `value` is a list
    for key, value in self._var_list.items(): 
        if key == label:
            return

        # `list_val` is a list or tuple or None
        for i, list_val in enumerate(value):
            if list_val is None:
                continue
            elif isinstance(list_val, tuple) and isinstance(var_ref, tuple):
                if self._is_ref_match(list_val, var_ref):
                    self._org_value[label][index] = self._org_value[key][i]     

            elif isinstance(list_val, tuple) and isinstance(var_ref, list):
                for i_2, ref_v in enumerate(var_ref):
                    if self._is_ref_match(list_val, ref_v):
                        self._org_value[label][index][i_2] = (
                            self._org_value[key][i]
                        )
            elif isinstance(list_val, list) and isinstance(var_ref, tuple):
                for i_2, l_v in enumerate(list_val):
                    if self._is_ref_match(l_v, var_ref):
                        self._org_value[label][index] = (
                            self._org_value[key][i][i_2]
                        )
            else:
                for ref_i, ref_val in enumerate(var_ref):
                    for list_i, v in enumerate(list_val):
                        if self._is_ref_match(v, ref_val):                           
                            self._org_value[label][index][ref_i] = (
                                self._org_value[key][i][list_i]
                            )

def _is_ref_match(
        self, list_val: tuple[str, ...], target_val: tuple[str, ...],
) -> bool:
    if len(list_val) == 3 and len(target_val) == 3:
        return list_val[:2] == target_val[:2]

    elif len(list_val) == 4 and len(target_val) == 4:
        return list_val[:2] == target_val[:2]
    