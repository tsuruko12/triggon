from typing import Any

from ..errors import UpdateError
from ..trigfunc import TRIGFUNC_ATTR
from .._internal import (
    ATTR,
    LOG_VERBOSITY,
    UPDATE_LOCK,
    VAR,
)
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
        debug_on = self.debug[LOG_VERBOSITY] > 1
        label_value = self._new_values[label]

        var_refs, attr_refs = self._find_update_refs(label, callsite.file)

        # Use a global lock for value assignment

        # Update global variables
        for ref in var_refs:
            new_value, label_idx = self._get_new_value_and_idx(
                set_true,
                label_value,
                idx,
                ref.ref_id,
            )
            with UPDATE_LOCK:
                try:
                    prev_value = f_globals[ref.var_name]
                    if prev_value == new_value:
                        continue
                    if set_true and hasattr(new_value, TRIGFUNC_ATTR):
                        f_globals[ref.var_name] = new_value.run()
                    else:
                        f_globals[ref.var_name] = new_value
                except KeyError as e:
                    raise UpdateError(ref.var_name, e) from None
                else:
                    if debug_on:
                        self.log_value_update(
                            label,
                            label_idx,
                            prev_value,
                            new_value,
                            callsite,
                            target_name=ref.var_name,
                        )

        # Update attributes
        for ref in attr_refs:
            new_value, label_idx = self._get_new_value_and_idx(
                set_true,
                label_value,
                idx,
                ref.ref_id,
            )
            with UPDATE_LOCK:
                try:
                    prev_value = getattr(ref.parent_obj, ref.attr_name)
                    if prev_value == new_value:
                        continue
                    if set_true and hasattr(new_value, TRIGFUNC_ATTR):
                        setattr(ref.parent_obj, ref.attr_name, new_value.run())
                    else:
                        setattr(ref.parent_obj, ref.attr_name, new_value)
                except (AttributeError, TypeError, ValueError) as e:
                    raise UpdateError(ref.full_name, e) from None
                else:
                    if debug_on:
                        self.log_value_update(
                            label,
                            label_idx,
                            prev_value,
                            new_value,
                            callsite,
                            target_name=ref.full_name,
                        )

    def _get_new_value_and_idx(
        self,
        set_true: bool,
        label_value: tuple[Any, ...],
        idx: int | None,
        ref_id: int,
    ) -> tuple[Any, int | None]:
        if not set_true:
            new_value = self._id_meta[ref_id].orig_val
        else:
            if idx is None:
                idx = self._get_last_idx(ref_id)
            new_value = label_value[idx]

        return new_value, idx

    def _get_last_idx(self, ref_id: int) -> int:
        idxs = self._id_meta[ref_id].idxs
        return idxs[-1]

    def _find_update_refs(
        self,
        label: str,
        file: str,
    ) -> tuple[list[VarRef], list[AttrRef]]:
        label_refs = self._label_refs[label]
        var_refs = label_refs[VAR]
        attr_refs = label_refs[ATTR]

        target_var_refs = [ref for ref in var_refs if self._id_meta[ref.ref_id].file != file]
        target_attr_refs = [ref for ref in attr_refs if self._id_meta[ref.ref_id].file != file]
        return target_var_refs, target_attr_refs
