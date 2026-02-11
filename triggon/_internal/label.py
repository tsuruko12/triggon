from typing import KeysView

from ..errors import InvalidArgumentError, UnregisteredLabelError
from .arg_types import LabelTypes, IndexTypes


SYMBOL = "*"


class Label:
    def strip_prefix_symbols( 
        self,
        labels: LabelTypes | KeysView[str],
        indexes: IndexTypes | None,
    ) -> tuple[tuple[str, ...], tuple[int, ...]]:
        if isinstance(labels, str):
            labels = (labels,)
        if isinstance(indexes, int):
            indexes = (indexes,)
        
        symbol_counts = []
        stripped_labels = []

        for label in labels:
            stripped_labels.append(label.lstrip(SYMBOL))
            
            if indexes is not None:
                continue        
            count = 0
            for c in label:
                if c == SYMBOL:
                    count += 1
                    continue
                symbol_counts.append(count)
                break

        if indexes is None:
            indexes = tuple(symbol_counts)
        elif isinstance(indexes, range):
            indexes = tuple(indexes)

        self._check_value_indexes(stripped_labels, indexes, labels)
        return tuple(stripped_labels), indexes

    def ensure_labels_exist(
            self, 
            labels: str| tuple[str, ...] | KeysView[str],
            org_labels: tuple[str, ...] | KeysView[str] = None,
    ) -> None:
        if isinstance(labels, str):
            labels = (labels,)
        
        for i, label in enumerate(labels):
            if label not in self._new_values:
                org_label = org_labels[i] if org_labels is not None else None
                raise UnregisteredLabelError(label, org_label)

    def _check_value_indexes(
        self, 
        labels: list[str] | KeysView[str], 
        indexes: tuple[int, ...],
        org_labels: list[str] | tuple[str, ...],
    ) -> None:
        self.ensure_labels_exist(labels, org_labels)

        if len(labels) != len(indexes):
            raise InvalidArgumentError(
                "the number of labels and indexes must be the same"
            )

        for i, label in zip(indexes, labels):
            try:
                values = self._new_values[label]
            except KeyError:
                raise UnregisteredLabelError(label)
            else:
                if len(values) - 1 < i:
                    raise IndexError(
                        f"index {i} is out of range for label {label!r}"
                    )
