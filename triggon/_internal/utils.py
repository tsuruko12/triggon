from typing import Any, KeysView, Sequence

from ._types import RevertMap, TriggerMap


def to_dict(
    keys: tuple[str, ...] | KeysView,
    values: tuple[str | int, ...] | None,
) -> TriggerMap | RevertMap:
    if values is None:
        values_iter = (None,) * len(keys)
    else:
        values_iter = values

    label_values = {}
    for key, val in zip(keys, values_iter):
        label_values[key] = val

    return label_values


def unwrap_value(value: tuple[Any, ...]) -> Sequence[str]:
    n = len(value)

    if n == 1:
        return value[0]
    return value
