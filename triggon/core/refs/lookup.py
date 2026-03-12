from typing import cast

from ..._internal._types.aliases import UpdateRefs
from ..._internal._types.structs import AttrRef, RefMeta, RefsByKind, VarRef
from ..._internal.keys import ATTR, GLOB_VAR, MODULE_SCOPE


class RefLookup:
    _label_refs: dict[str, RefsByKind]
    _id_meta: dict[int, RefMeta]

    def get_ids_by_file(self, file: str) -> set[int]:
        # return ref_ids for the given file
        return {ref_id for ref_id, meta in self._id_meta.items() if meta.file == file}

    def get_refs(
        self,
        label: str | None = None,
    ) -> tuple[tuple[VarRef, ...], tuple[AttrRef, ...]]:
        if label is not None:
            target_values = [self._label_refs[label]]
        else:
            target_values = [refs for refs in self._label_refs.values()]

        matched_var_refs = []
        matched_attr_refs = []

        for value in target_values:
            for kind, refs in value.items():
                if kind == GLOB_VAR:
                    matched_var_refs.extend(cast(VarRef, refs))
                elif kind == ATTR:
                    matched_attr_refs.extend(cast(AttrRef, refs))
                else:
                    raise AssertionError(f"unreachable kind key: {kind!r}")

        return tuple(matched_var_refs), tuple(matched_attr_refs)

    def is_registered_name(
        self,
        target_name: str,
        target_ids: set[int],
        target_var_refs: tuple[VarRef, ...],
        target_attr_refs: tuple[AttrRef, ...],
        target_scope_name: str,
    ) -> bool:
        for ref in target_var_refs:
            if ref.var_name != target_name:
                continue
            if ref.ref_id in target_ids:
                return True

        for ref in target_attr_refs:
            if ref.full_name != target_name:
                continue
            if ref.ref_id not in target_ids:
                continue
            
            scope_name = self._id_meta[ref.ref_id].scope_name
            if scope_name == target_scope_name or scope_name == MODULE_SCOPE:
                return True

        return False

    def find_update_refs(self, label: str, file: str) -> UpdateRefs:
        label_refs = self._label_refs[label]

        update_refs = []

        for ref in label_refs[GLOB_VAR]:
            if self._id_meta[ref.ref_id].file != file:
                continue
            update_refs.append(ref)

        for ref in label_refs[ATTR]:
            if self._id_meta[ref.ref_id].file != file:
                continue
            update_refs.append(ref)

        return update_refs
