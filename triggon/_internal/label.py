from typing import KeysView

from ..errors import InvalidArgumentError, UnregisteredLabelError
from .arg_types import LabelArg, IndexArg


SYMBOL = "*"


class LabelValidator:
    def strip_prefix_symbols( 
        self,
        labels: LabelArg | KeysView[str],
        idxs: IndexArg | None,
    ) -> tuple[tuple[str, ...], tuple[int, ...]]:
        if isinstance(labels, str):
            labels = (labels,)
        if isinstance(idxs, int):
            idxs = (idxs,)
        
        symbol_counts = []
        stripped_labels = []

        for label in labels:
            stripped_labels.append(label.lstrip(SYMBOL))
            
            if idxs is not None:
                continue        
            count = 0
            for c in label:
                if c == SYMBOL:
                    count += 1
                    continue
                symbol_counts.append(count)
                break

        if idxs is None:
            idxs = tuple(symbol_counts)
        elif isinstance(idxs, range):
            idxs = tuple(idxs)

        self.check_value_idxs(stripped_labels, idxs, labels)
        return tuple(stripped_labels), idxs

    def ensure_labels_exist(
            self, 
            labels: str | tuple[str, ...] | KeysView[str],
            org_labels: tuple[str, ...] | KeysView[str] = None,
    ) -> None:
        if isinstance(labels, str):
            labels = (labels,)
        
        for i, label in enumerate(labels):
            if label not in self._new_values:
                org_label = org_labels[i] if org_labels is not None else None
                raise UnregisteredLabelError(label, org_label)

    def check_value_idxs(
        self, 
        labels: LabelArg | KeysView[str], 
        idxs: IndexArg | None,
        org_labels: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self.ensure_labels_exist(labels, org_labels)

        if idxs is None:
            return
        
        if isinstance(labels, str):
            labels = (labels,)
        if isinstance(idxs, int):
            idxs = (idxs,)

        if len(labels) != len(idxs):
            raise InvalidArgumentError(
                "the number of labels and idxs must be the same"
            )

        for i, label in zip(idxs, labels):
            try:
                values = self._new_values[label]
            except KeyError:
                raise UnregisteredLabelError(label)
            else:
                if i is None:
                    continue
                if len(values) - 1 < i:
                    raise IndexError(
                        f"index {i} is out of range for label {label!r}"
                    )
