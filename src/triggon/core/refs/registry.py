import threading
from collections.abc import MutableMapping, Sequence
from typing import TYPE_CHECKING, Any

from ..._internal._types.aliases import LabelToRefs
from ..._internal._types.structs import (
    AttrRef,
    Callsite,
    DebugConfig,
    RefMeta,
    VarRef,
)
from ..._internal.frames import get_callsite, get_target_frame
from ..._internal.keys import ATTR, GLOB_VAR, LOG_VERBOSITY, MODULE_SCOPE
from ..value_resolver import AttrResult, VarResult, resolve_ref_info
from .lookup import RefLookup


class RefRegistrar(RefLookup):
    debug: DebugConfig
    _label_is_active: dict[str, bool]
    _lock: threading.Lock

    if TYPE_CHECKING:
        from ..._internal._types.aliases import UpdateRefs

        def log_registered_name(
            self,
            target_name: str,
            label: str,
            callsite: Callsite,
        ) -> None: ...

        def log_unregistered_name(
            self, target_name: str, label: str, callsite: Callsite
        ) -> None: ...

        def update_values(
            self,
            label: str,
            idx: int | None,
            f_globals: MutableMapping[str, Any],
            callsite: Callsite,
            set_true: bool,
            update_refs: UpdateRefs | None = None,
        ) -> None: ...

    def register_target_refs(self, label_to_refs: LabelToRefs) -> None:
        frame = get_target_frame(depth=2)
        f_globals = frame.f_globals
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
                        callsite.scope_name,
                    )
                    if registered:
                        continue

                    ref = resolve_ref_info(name, frame)

                    if isinstance(ref, VarResult):
                        save_ref = VarRef(ref_id=self._latest_id, var_name=name)
                        self._label_refs[label][GLOB_VAR].append(save_ref)
                    elif isinstance(ref, AttrResult):
                        save_ref = AttrRef(
                            ref_id=self._latest_id,
                            attr_name=ref.attr_name,
                            parent_obj=ref.parent_obj,
                            full_name=name,
                        )
                        self._label_refs[label][ATTR].append(save_ref)
                    else:
                        raise AssertionError(f"unreachable ref type: {type(ref)!r}")

                    self._id_meta[self._latest_id] = RefMeta(
                        callsite.file,
                        ref.scope_name,
                        orig_val=ref.value,
                    )
                    self._latest_id += 1

                if self.debug[LOG_VERBOSITY] == 3:
                    self.log_registered_name(name, label, callsite)

                if self._label_is_active[label]:
                    self.update_values(
                        label,
                        idx,
                        f_globals,
                        callsite,
                        set_true=True,
                        update_refs=[save_ref],
                    )

    def unregister_target_refs(
        self, label: str, target_names: Sequence[str], target_ids: set[int], callsite: Callsite
    ) -> None:
        label_refs = self._label_refs[label]
        target_name_set = set(target_names)

        new_attr_refs = []
        for ref in label_refs[ATTR]:
            if ref.ref_id not in target_ids:
                new_attr_refs.append(ref)
                continue
            if ref.full_name not in target_name_set:
                new_attr_refs.append(ref)
                continue

            scope_name = self._id_meta[ref.ref_id].scope_name
            if scope_name != callsite.scope_name and scope_name != MODULE_SCOPE:
                new_attr_refs.append(ref)
                continue

            del self._id_meta[ref.ref_id]
            if self.debug[LOG_VERBOSITY] == 3:
                self.log_unregistered_name(ref.full_name, label, callsite)

        label_refs[ATTR] = new_attr_refs

        new_var_refs = []
        for ref in label_refs[GLOB_VAR]:
            if ref.ref_id not in target_ids:
                new_var_refs.append(ref)
                continue
            if ref.var_name not in target_name_set:
                new_var_refs.append(ref)
                continue

            del self._id_meta[ref.ref_id]
            if self.debug[LOG_VERBOSITY] == 3:
                self.log_unregistered_name(ref.var_name, label, callsite)

        label_refs[GLOB_VAR] = new_var_refs
