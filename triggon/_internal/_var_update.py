from threading import Lock
from types import FunctionType
from typing import Any


proc_lock = Lock()


def _has_var_refs(
    self, labels: list[str], called_func: str, after: int | float | None, 
    index: int = None, to_org: bool = False,
) -> list[str] | None:
    update_labels = [v for v in labels if self._var_refs[v] is not None]
    if not update_labels:
        return None

    self._get_target_frame(called_func)

    if after is not None:            
        self._store_frame_info(update_labels, to_org)
        return update_labels

    self._update_all_vars(update_labels, index, to_org)
    return None
        
def _store_org_value(self, label: str, index: int, org_value: Any) -> None:
    target_index = self._org_values[label][index] 
    if target_index is None:
        self._org_values[label][index] = []
    self._org_values[label][index].append(org_value)

def _update_var_value(
    self, 
    var_refs: tuple[str, ...], 
    label: str, 
    index: int, 
    update_value: Any, 
    inner_index: int = None, 
    to_org: bool = False,
) -> None:
    # var_refs can be:
    # - (file name, lineno, var name) for globals
    # - (file name, lineno, attr name, instance) for class attributes

    i = _get_delay_index(to_org)

    with proc_lock:
        if len(var_refs) == 4:   
            prev_value = getattr(var_refs[3], var_refs[2])
            if prev_value == update_value:
                return       
            setattr(var_refs[3], var_refs[2], update_value)
        else:    
            if self._delay_info[label][i] is None:
                prev_value = self._frame.f_globals[var_refs[2]]
                if prev_value == update_value:
                    return      
                self._frame.f_globals[var_refs[2]] = update_value
            else:
                frame = self._delay_info[label][i][0]
                prev_value = frame.f_globals[var_refs[2]]
                if frame.f_globals[var_refs[2]] == update_value:
                    return
                frame.f_globals[var_refs[2]] = update_value

    self._debug_update(
        label, index, inner_index, update_value, to_org, prev_value,
    )

def _update_all_vars(
        self, labels: list[str], index: int | None, to_org: bool = False,
) -> None:
    for label in labels:
        if to_org:
            update_value = self._org_values[label]
        else:
            # Each index always holds a single value
            update_value = self._new_values[label]

        # Restore all variables to their original or new values 
        for i, ref in enumerate(self._var_refs[label]):
            if ref is None:
                continue
                  
            if isinstance(ref, list):
                if to_org:
                    for i_2, val in enumerate(update_value[i]):
                        self._update_var_value(
                            ref[i_2], label, i, val, i_2, to_org,
                        )
                else:
                    if index is not None:
                        i = index                    
                    for i_2, ref_2 in enumerate(ref):
                        self._update_var_value(
                            ref_2, label, i, update_value[i], i_2, to_org,
                        )             
            else:
                if to_org:
                    self._update_var_value(
                        ref, label, i, update_value[i][0], to_org=to_org,
                    )
                else:
                    if index is not None:
                        i = index
                    self._update_var_value(
                        ref, label, i, update_value[i], to_org=to_org,
                    )

        i = _get_delay_index(to_org)
        if self._delay_info[label][i] is not None:
            self._delay_info[label][i] = None


def _is_delayed_func(target: Any) -> bool:
    if type(target) is not FunctionType:
        return False
    
    has_mark = getattr(target, "_trigfunc", False)
    return has_mark


def _get_delay_index(to_org: bool) -> int:
    if to_org:
        return 1
    return 0