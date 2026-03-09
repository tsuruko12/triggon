import threading
from collections.abc import MutableMapping
from typing import TYPE_CHECKING, Any

from ..._internal._types.aliases import LabelToRefs
from ..._internal._types.structs import (
    AttrRef,
    DebugConfig,
    RefMeta,
    RefsByKind,
    VarRef,
)
from ..._internal.frames import get_callsite, get_target_frame
from ..._internal.keys import ATTR, GLOB_VAR, LOG_VERBOSITY
from ..value_resolver import resolve_ref_info
from .lookup import RefLookup


class RefRegistrar(RefLookup):
    debug: DebugConfig
    _label_is_active: dict[str, bool]
    _lock: threading.Lock

    if TYPE_CHECKING:
        from ..._internal._types.aliases import UpdateRefs
        from ..._internal._types.structs import Callsite

        def log_registered_name(
            self,
            target_name: str,
            label: str,
            callsite: Callsite,
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

    def register_ref_map(self, label_to_refs: LabelToRefs) -> None:
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
                        callsite.func_name,
                    )
                    if registered:
                        continue

                    ref = resolve_ref_info(name, frame)

                    if ref[0] == GLOB_VAR:
                        _, value = ref
                        save_ref = VarRef(ref_id=self._latest_id, var_name=name)
                        self._label_refs[label][GLOB_VAR].append(save_ref)
                    elif ref[0] == ATTR:
                        _, value, attr_name, parent_obj = ref
                        save_ref = AttrRef(
                            ref_id=self._latest_id,
                            attr_name=attr_name,
                            parent_obj=parent_obj,
                            full_name=name,
                        )
                        self._label_refs[label][ATTR].append(save_ref)
                    else:
                        raise AssertionError(f"unreachable ref kind: {ref[0]!r}")

                    self._id_meta[self._latest_id] = RefMeta(
                        file=callsite.file,
                        func_name=callsite.func_name,
                        orig_val=value,
                        idx=idx,
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
