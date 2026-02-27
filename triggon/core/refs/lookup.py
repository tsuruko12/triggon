from ..._internal import VAR
from ..._internal.arg_types import AttrRef, VarRef


class RefLookup:
    def get_ids_by_file(self, file: str) -> set[int]:
        # Return ref_ids for the given file
        return {ref_id for ref_id, meta in self._id_meta.items() if meta.file == file}

    def get_refs(
        self,
        label: str | None = None,
    ) -> tuple[tuple[VarRef, ...], tuple[AttrRef, ...]]:
        if label is not None:
            self.ensure_labels_exist(label)
            target_values = [self._label_refs[label]]
        else:
            target_values = [refs for refs in self._label_refs.values()]

        matched_var_refs = []
        matched_attr_refs = []

        for value in target_values:
            for kind, refs in value.items():
                if kind == VAR:
                    matched_var_refs.extend(refs)
                else:
                    # 'attr'
                    matched_attr_refs.extend(refs)

        return tuple(matched_var_refs), tuple(matched_attr_refs)

    def is_registered_name(
        self,
        target_name: str,
        target_ids: set[int],
        target_var_refs: tuple[VarRef, ...],
        target_attr_refs: tuple[AttrRef, ...],
        func_name: str,
    ) -> True:
        for ref in target_var_refs:
            if ref.var_name != target_name:
                continue
            if ref.ref_id in target_ids:
                return True

        for ref in target_attr_refs:
            if ref.full_name != target_name:
                continue
            # Attr names can collide; check func_name too
            if ref.ref_id not in target_ids:
                continue
            if self._id_meta[ref.ref_id].func_name == func_name:
                return True

        return False
