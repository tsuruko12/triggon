from typing import Any

from ..errors import UpdateError
from .._internal import TRIGGON_LOG_VERBOSITY, UPDATE_LOCK
from .._internal.arg_types import (
    AttrRef,
    Callsite,
    VarRef,
)


class ValueUpdater:
    def update_values(
            self, 
            label: str, 
            idx: int | None, 
            f_globals: dict[str, Any],
            callsite: Callsite,
            set_true: bool,
    ) -> None:  
        debug_on = self.debug[TRIGGON_LOG_VERBOSITY] > 1
        label_value = self._new_values[label]

        var_refs, attr_refs = self._find_update_refs(label, callsite[0])

        # Use a global lock for value assignment

        # Update global variables
        for ref in var_refs:
            ref_id, var_name = ref

            new_value, label_idx = self._get_new_value_and_idx(
                set_true, 
                label_value, 
                idx, 
                ref_id,
            ) 
            with UPDATE_LOCK:     
                try:
                    prev_value = f_globals[var_name]
                    if prev_value == new_value:
                        continue
                    f_globals[var_name] = new_value   
                except KeyError as e:
                    raise UpdateError(var_name, e) from None
                else:
                    if debug_on:
                        self.log_value_update(
                            label, 
                            label_idx, 
                            var_name, 
                            prev_value,
                            new_value, 
                            callsite,
                        ) 

        # Update attributes
        for ref in attr_refs:
            ref_id, attr_name, obj, full_name = ref

            new_value, label_idx = self._get_new_value_and_idx(
                set_true, 
                label_value, 
                idx, 
                ref_id,
            )   
            with UPDATE_LOCK:
                try:
                    prev_value = getattr(obj, attr_name)
                    if prev_value == new_value:
                        continue
                    setattr(obj, attr_name, new_value)
                except (AttributeError, TypeError, ValueError) as e:
                    raise UpdateError(full_name, e) from None
                else:
                    if debug_on:
                        self.log_value_update(
                            label, 
                            label_idx, 
                            full_name, 
                            prev_value,
                            new_value, 
                            callsite,
                        ) 

    def _get_new_value_and_idx(
            self, 
            set_true: bool, 
            label_value: tuple[Any, ...],
            idx: int | None,
            ref_id: int, 
    ) -> tuple[Any, int | None]:
        if not set_true:                 
            new_value = self._id_meta[ref_id][1]
        else:
            if idx is None:
                idx = self._get_last_idx(ref_id)
            new_value = label_value[idx]

        return new_value, idx

    def _get_last_idx(self, ref_id: int) -> int:
        idxs = self._id_meta[ref_id][2]
        return idxs[-1]

    def _find_update_refs(
            self, label: str, file_name: str,
    ) -> tuple[list[VarRef], list[AttrRef]]:
        label_refs = self._label_refs[label]
        var_refs = label_refs["var"]
        attr_refs = label_refs["attr"]

        target_var_refs = [
            ref for ref in var_refs if self._is_from_file(ref, file_name)
        ]
        target_attr_refs = [
            ref for ref in attr_refs if self._is_from_file(ref, file_name)
        ]     
        return target_var_refs, target_attr_refs
    
    def _is_from_file(self, ref: VarRef | AttrRef, file_name: str) -> bool:
        ref_id = ref[0]
        return self._id_meta[ref_id][0] != file_name
        