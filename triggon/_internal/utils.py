def to_dict(
    keys: tuple[str, ...],
    values: tuple[str | int, ...] | None,
) -> dict[str, str | int | None]:
    if values is None:
        values_iter = (None,) * len(keys)
    else:
        values_iter = values

    label_values = {}
    for key, val in zip(keys, values_iter):
        label_values[key] = val

    return label_values
