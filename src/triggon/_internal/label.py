from collections.abc import KeysView, Mapping, Sequence, ValuesView
from typing import Any

from ..errors.public import InvalidArgumentError, UnregisteredLabelError
from ._types.aliases import IndexArg, LabelArg

SYMBOL = "*"


class LabelValidator:
    _new_values: Mapping[str, tuple[Any, ...]]

    def resolve_labels_and_idxs(
        self,
        labels: LabelArg | KeysView[str],
        idxs: IndexArg | ValuesView[int] | None,
        allow_symbol: bool = True,
        is_init: bool = False,
    ) -> tuple[tuple[str, ...], tuple[int, ...]]:
        if isinstance(labels, str):
            labels = (labels,)
        if isinstance(idxs, int):
            idxs = (idxs,)

        # keep original labels before stripping
        orig_labels = tuple(labels)

        labels, counts = self._strip_prefix_symbols(labels, allow_symbol)

        if idxs is None:
            # use symbol counts as idxs
            idxs = counts
        else:
            assert isinstance(idxs, Sequence)
            if len(labels) != len(idxs):
                raise InvalidArgumentError("labels and indices must have the same length")

        for i, label in enumerate(labels):
            _validate_label(label)
            if is_init:
                continue

            self._ensure_labels_exist(label, orig_labels[i])
            self.validate_idx_range(label, idxs[i])

        return tuple(labels), tuple(idxs)

    def _strip_prefix_symbols(
        self,
        labels: Sequence[str] | KeysView[str],
        allow_symbol: bool,
    ) -> tuple[list[str], list[int]]:
        symbol_counts = []
        stripped_labels = []
        seen_labels = set()

        for label in labels:
            stripped = label.lstrip(SYMBOL)
            if stripped in seen_labels:
                continue
            stripped_labels.append(stripped)
            seen_labels.add(stripped)

            prefix_count = 0
            for ch in label:
                if ch == SYMBOL:
                    if not allow_symbol:
                        raise InvalidArgumentError(
                            f"remove the leading {SYMBOL!r} characters from {label!r}"
                        )
                    prefix_count += 1
                    continue
                break
            symbol_counts.append(prefix_count)

        return stripped_labels, symbol_counts

    def _ensure_labels_exist(self, label: str, orig_label: str | None = None) -> None:
        if label not in self._new_values:
            raise UnregisteredLabelError(label, orig_label)

    def validate_idx_range(self, label: str, idx: int) -> None:
        label_values = self._new_values[label]
        if len(label_values) - 1 < idx:
            raise IndexError(f"index {idx} is out of range for label {label!r}")


def _validate_label(label: str) -> None:
    if not label or any(ch.isspace() for ch in label):
        raise InvalidArgumentError(f"label must not be empty or contain whitespace: {label!r}")
