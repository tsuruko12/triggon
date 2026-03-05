from typing import TYPE_CHECKING, Any, Mapping

from .._internal import (
    ATTR,
    LOG_VERBOSITY,
    UPDATE_LOCK,
    VAR,
)
from .._internal._types.structs import (
    AttrRef,
    Callsite,
    DebugConfig,
    RefMeta,
    RefsByKind,
    VarRef,
)
from ..errors.public import UpdateError
from ..trigfunc import TRIGFUNC_ATTR


class ValueUpdater:
    debug: DebugConfig
    _new_values: Mapping[str, tuple[Any, ...]]
    _label_refs: dict[str, RefsByKind]
    _id_meta: dict[int, RefMeta]

    if TYPE_CHECKING:

        def log_value_update(
            self,
            label: str | None,
            idx: int | None,
            prev_value: Any,
            new_value: Any,
            callsite: Callsite,
            target_name: str | None = None,
        ) -> None: ...

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

        # use a global lock for value assignment

        # update global variables
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

        # update attributes
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
                idx = self._id_meta[ref_id].idx
            new_value = label_value[idx]

        return new_value, idx

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
