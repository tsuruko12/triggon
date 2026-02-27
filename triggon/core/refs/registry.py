from ..._internal import (
   TRIGGON_LOG_VERBOSITY, 
   VAR, 
   get_callsite,
   get_target_frame, 
)
from ..value_resolver import resolve_ref_info
from ..._internal.arg_types import AttrRef, LabelToRefs, RefMeta, VarRef


class RefRegistrar:
    def register_ref_map(self, label_to_refs: LabelToRefs) -> None:
        frame = get_target_frame(("register_ref", "register_refs"))
        callsite = get_callsite(frame)
        file, _, func_name = callsite

        target_ids = self.get_matched_ids(file)

        for label, name_to_idxs in label_to_refs.items():
          target_var_refs, target_attr_refs = self.get_matched_refs(label)
          
          for name, idxs in name_to_idxs.items():
            # idxs is a tuple
            result, ref_id = self.is_registered_name(
               name, target_ids, target_var_refs, target_attr_refs, func_name,
            )
            if result:
              new_ids = [i for i in idxs if i not in self._id_meta[ref_id].idxs]
              if new_ids:
                  self._id_meta[ref_id].idxs.extend(new_ids)
              continue
            
            ref = resolve_ref_info(name, frame)
            if ref[0] == VAR:
              kind, value = ref
              save_ref = VarRef(ref_id=self._latest_id, var_name=name)
            else:
              # 'attr'
              kind, value, attr_name, parent_obj = ref
              save_ref = AttrRef(
                 ref_id=self._latest_id, attr_name=attr_name, parent_obj=parent_obj, full_name=name,
              )
            
            self._label_refs[label][kind].append(save_ref)
            self._id_meta[self._latest_id] = RefMeta(
               file=file, func_name=func_name, orig_val=value, idxs=list(idxs),
            )
            self._latest_id += 1

            if self.debug[TRIGGON_LOG_VERBOSITY] == 3:
              self.log_registered_name(value, callsite)