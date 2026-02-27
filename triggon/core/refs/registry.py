from typing import Mapping

from ..._internal import (
    LOG_VERBOSITY,
    VAR,
    get_callsite,
    get_target_frame,
)
from ..value_resolver import resolve_ref_info
from ..._internal.arg_types import AttrRef, LabelToRefs, RefMeta, VarRef


class RefRegistrar:
    def register_ref_map(self, label_to_refs: LabelToRefs, f_globals: Mapping) -> None:
        frame = get_target_frame(depth=1)
        callsite = get_callsite(frame)

        target_ids = self.get_ids_by_file(callsite.file)

        for label, name_to_idx in label_to_refs.items():
            target_var_refs, target_attr_refs = self.get_refs(label)

            for name, idx in name_to_idx.items():
                with self._lock:
                    registered = self.is_registered_name(
                        name,
                        target_ids,
                        target_var_refs,
                        target_attr_refs,
                        callsite.func_name,
                    )
                    if registered:
                        continue

                    ref = resolve_ref_info(name, frame)

                    if ref[0] == VAR:
                        kind, value = ref
                        save_ref = VarRef(ref_id=self._latest_id, var_name=name)
                    else:
                        # 'attr'
                        kind, value, attr_name, parent_obj = ref
                        save_ref = AttrRef(
                            ref_id=self._latest_id,
                            attr_name=attr_name,
                            parent_obj=parent_obj,
                            full_name=name,
                        )

                    self._label_refs[label][kind].append(save_ref)
                    self._id_meta[self._latest_id] = RefMeta(
                        file=callsite.file,
                        func_name=callsite.func_name,
                        orig_val=value,
                        idx=idx,
                    )
                    self._latest_id += 1

                if self.debug[LOG_VERBOSITY] == 3:
                    self.log_registered_name(value, callsite)
                if self._label_is_active[label]:
                    self.update_values(label, idx, f_globals, callsite, set_true=True)
