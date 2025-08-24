from typing import Any

from ._sentinel import _NO_VALUE


def _init_or_not(self, label: str, index: tuple[int, ...]) -> bool:
    self._get_target_frame("switch_var")

    self._ensure_label_exists(label)  
    self._compare_value_counts(label, index)

    if (
        self._var_refs[label][index[0]] is None 
        or self._is_new_var(label, index[0])
    ):  
        # Initial process to store argument variables 
        self._trace_func_call()
        return True 
    return False

def _is_new_var(
        self, label: str, index: int, target_refs: tuple[str, ...] = None,
) -> bool:
    var_refs = self._var_refs[label][index]

    if var_refs is None:
        return 
    if isinstance(var_refs, tuple):
        var_refs = [var_refs]

    if target_refs is not None:
        if len(target_refs) == 3:
            cmp_tar_refs = (target_refs[0], target_refs[2])
        elif len(target_refs) == 4:
            cmp_tar_refs = (target_refs[2], target_refs[3])
    else:
        cmp_tar_refs = (self._file_name, self._lineno)

    for ref in var_refs:
        if target_refs is not None:
            if len(ref) == 3:
                # (file name, var name)
                cmp_refs = (ref[0], ref[2])
            elif len(ref) == 4:
                # (attr name, class instance)
                cmp_refs = (ref[2], ref[3])
        else:
            # (file name, line number)
            cmp_refs = (ref[0], ref[1])

        if cmp_refs == cmp_tar_refs:
            return False
             
    return True

def _find_match_var(self, label: str, target_refs: tuple[str, ...]) -> Any:
    # Used to retrieve the original value for revert()

    # value is a list
    for key, value in self._var_refs.items(): 
        # list_val is a list or tuple or None
        for i, list_val in enumerate(value):
            if list_val is None:
                continue
            elif isinstance(list_val, tuple):
                if self._is_ref_match(list_val, target_refs):
                    return self._org_values[key][i][0]  
            else:
                for i_2, val in enumerate(list_val):
                    if self._is_ref_match(val, target_refs):
                        return self._org_values[key][i][i_2]
                    
    return _NO_VALUE

def _is_ref_match(
        self, list_val: tuple[str, ...], target_val: tuple[str, ...],
) -> bool:
    if len(list_val) == 3 and len(target_val) == 3:
        return list_val[0] == target_val[0] and list_val[2] == target_val[2]
    if len(list_val) == 4 and len(target_val) == 4:
        return list_val[2:] == target_val[2:]
    