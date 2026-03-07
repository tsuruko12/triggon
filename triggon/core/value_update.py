from typing import TYPE_CHECKING, Any, Literal, Mapping, NamedTuple

from .._internal import (
    ATTR,
    GLOB_VAR,
    LOC_VAR,
    LOG_VERBOSITY,
    UPDATE_LOCK,
)
from .._internal._types.structs import (
    AttrRef,
    Callsite,
    DebugConfig,
    FrameContext,
    RefMeta,
    RefsByKind,
    VarRef,
)
from ..errors.public import UpdateError
from ..trigfunc import TRIGFUNC_ATTR


class _GlobVarRef(NamedTuple):
    kind: Literal["glob_var"]
    ref: VarRef


class _LocVarRef(NamedTuple):
    kind: Literal["loc_var"]
    ref: VarRef


class _AttrRef(NamedTuple):
    kind: Literal["attr"]
    ref: AttrRef


type UpdateRef = _GlobVarRef | _LocVarRef | _AttrRef


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
        frame_ctx: FrameContext,
        set_true: bool,
    ) -> None:
        debug_on = self.debug[LOG_VERBOSITY] > 1
        label_value = self._new_values[label]

        callsite = frame_ctx.callsite
        update_refs = self._find_update_refs(label, callsite.file)

        for ref_cls in update_refs:
            new_value, label_idx = self._get_new_value_and_idx(
                set_true,
                label_value,
                idx,
                ref_cls.ref.ref_id,
            )
            
            # use a global lock for value assignment
            with UPDATE_LOCK:
                # update attribute 
                if ref_cls.kind == ATTR:
                    attr_ref: AttrRef = ref_cls.ref
                    
                    try:
                        prev_value = getattr(attr_ref.parent_obj, attr_ref.attr_name)
                        if prev_value == new_value:
                            continue
                        if set_true and hasattr(new_value, TRIGFUNC_ATTR):
                            setattr(attr_ref.parent_obj, attr_ref.attr_name, new_value.run())
                        else:
                            setattr(attr_ref.parent_obj, attr_ref.attr_name, new_value)
                    except (AttributeError, TypeError, ValueError) as e:
                        raise UpdateError(attr_ref.full_name, e) from None
                    else:
                        if debug_on:
                            self.log_value_update(
                                label,
                                label_idx,
                                prev_value,
                                new_value,
                                callsite,
                                target_name=attr_ref.full_name,
                            )  
                        continue

                # update local/global variable

                if ref_cls.kind == LOC_VAR:
                    scope = frame_ctx.f_locals
                else:
                    scope = frame_ctx.f_globals
                
                var_ref: VarRef = ref_cls.ref

                try: 
                    prev_value = scope[var_ref.var_name]
                    if prev_value == new_value:
                        continue
                    if set_true and hasattr(new_value, TRIGFUNC_ATTR):
                        scope[var_ref.var_name] = new_value.run()
                    else:
                        scope[var_ref.var_name] = new_value
                except KeyError as e:
                    raise UpdateError(var_ref.var_name, e) from None
                else:
                    if debug_on:
                        self.log_value_update(
                            label,
                            label_idx,
                            prev_value,
                            new_value,
                            callsite,
                            target_name=var_ref.var_name,
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

    def _find_update_refs(self, label: str, file: str) -> list[UpdateRef]:
        update_refs = []
        label_refs = self._label_refs[label]

        for ref in label_refs[LOC_VAR]:
            if self._id_meta[ref.ref_id].file != file:
                continue    
            update_refs.append(_LocVarRef(kind=LOC_VAR, ref=ref))

        for ref in label_refs[GLOB_VAR]:
            if self._id_meta[ref.ref_id].file != file:
                continue    
            update_refs.append(_GlobVarRef(kind=GLOB_VAR, ref=ref))

        for ref in label_refs[ATTR]:
            if self._id_meta[ref.ref_id].file != file:
                continue    
            update_refs.append(_AttrRef(kind=ATTR, ref=ref))

        return update_refs
