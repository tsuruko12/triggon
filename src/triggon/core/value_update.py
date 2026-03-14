from collections.abc import Mapping, MutableMapping
from typing import TYPE_CHECKING, Any

from .._internal._types.aliases import UpdateRefs
from .._internal._types.structs import (
    AttrRef,
    Callsite,
    DebugConfig,
    RefMeta,
    VarRef,
)
from .._internal.keys import LOG_VERBOSITY
from .._internal.lock import UPDATE_LOCK
from ..errors.public import UpdateError
from ..trigfunc import TRIGFUNC_ATTR


class ValueUpdater:
    debug: DebugConfig
    _new_values: Mapping[str, tuple[Any, ...]]
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

        def find_update_refs(self, label: str, file: str) -> UpdateRefs: ...

    def update_values(
        self,
        label: str,
        idx: int | None,
        f_globals: MutableMapping[str, Any],
        callsite: Callsite,
        set_true: bool,
        update_refs: UpdateRefs | None = None,
    ) -> None:
        debug_on = self.debug[LOG_VERBOSITY] > 1
        label_value = self._new_values[label]

        if update_refs is None:
            update_refs = self.find_update_refs(label, callsite.file)

        for ref in update_refs:
            new_value, label_idx = self._get_new_value_and_idx(
                set_true,
                label_value,
                idx,
                ref.ref_id,
            )

            # use a global lock for value assignment
            with UPDATE_LOCK:
                if isinstance(ref, AttrRef):
                    # update attributes
                    try:
                        prev_value = getattr(ref.parent_obj, ref.attr_name)
                        if prev_value == new_value:
                            continue

                        if set_true and hasattr(new_value, TRIGFUNC_ATTR):
                            setattr(ref.parent_obj, ref.attr_name, new_value._run())
                        else:
                            setattr(ref.parent_obj, ref.attr_name, new_value)
                    except (AttributeError, TypeError, ValueError) as e:
                        raise UpdateError(ref.full_name, e) from None
                    else:
                        target_name = ref.full_name
                elif isinstance(ref, VarRef):
                    # update global variables
                    try:
                        prev_value = f_globals[ref.var_name]
                        if prev_value == new_value:
                            continue

                        if set_true and hasattr(new_value, TRIGFUNC_ATTR):
                            f_globals[ref.var_name] = new_value._run()
                        else:
                            f_globals[ref.var_name] = new_value
                    except KeyError as e:
                        raise UpdateError(ref.var_name, e) from None
                    else:
                        target_name = ref.var_name
                else:
                    raise AssertionError(f"unreachable ref class: {ref!r}")

                if debug_on:
                    self.log_value_update(
                        label,
                        label_idx,
                        prev_value,
                        new_value,
                        callsite,
                        target_name,
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
