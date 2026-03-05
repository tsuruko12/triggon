from collections.abc import Mapping, Sequence
from typing import Any

from ..errors.public import InvalidArgumentError
from ._types.aliases import NumArg
from .sentinel import _NO_VALUE


def check_debug(debug: Any) -> None:
    if isinstance(debug, (bool, str)):
        return

    if not isinstance(debug, Sequence):
        _raise_type_error(arg_name="debug", type_msg="bool, str, or Sequence[str]")

    if isinstance(debug, Sequence):
        if not debug:
            _raise_value_error(arg_name="debug")
        for i, v in enumerate(debug):
            if not isinstance(v, str):
                _raise_type_error(arg_name="debug", type_msg="str", actual_value=v, idx=i)


def check_str_sequence(arg_name: str, args: Any, allow_multi: bool = True) -> None:
    if isinstance(args, str):
        return

    if not allow_multi:
        _raise_type_error(arg_name, type_msg="str")
    if not isinstance(args, Sequence):
        _raise_type_error(arg_name, type_msg="str or Sequence[str]")

    if isinstance(args, Sequence):
        if not args:
            _raise_value_error(arg_name)

        for i, arg in enumerate(args):
            if not isinstance(arg, str):
                _raise_type_error(arg_name, type_msg="str", actual_value=arg, idx=i)


def check_items(arg_name: str, arg: Any) -> None:
    if not isinstance(arg, Mapping):
        if arg_name == "label_values":
            _raise_type_error(arg_name, type_msg="Mapping[str, Any]")
        else:
            # 'label_to_refs'
            _raise_type_error(arg_name, type_msg="Mapping[str, Mapping[str, int]]")

    if not arg:
        _raise_value_error(arg_name)

    for key, val in arg.items():
        # key should be str
        if not isinstance(key, str):
            _raise_type_error(arg_name, type_msg="str", key=key)

        if arg_name == "label_to_refs":
            if not isinstance(val, Mapping):
                _raise_type_error(
                    arg_name,
                    type_msg="Mapping[str, int]",
                    actual_value=val,
                    key=key,
                )
            for key_2, val_2 in val.items():
                if not isinstance(key_2, str):
                    _raise_type_error(arg_name, type_msg="str", key=key)
                if not isinstance(val_2, int):
                    _raise_type_error(arg_name, type_msg="int", actual_value=val_2, key=key)
                _ensure_non_negative(val_2, arg_name="index")


def check_idxs(idxs: Any, allow_multi=True) -> None:
    if idxs is None:
        return
    if isinstance(idxs, int):
        _ensure_non_negative(idxs, "index")
        return

    if not allow_multi:
        _raise_type_error(arg_name="index", type_msg="int")

    if not isinstance(idxs, Sequence):
        _raise_type_error(arg_name="indices", type_msg="int or Sequence[int]")
    if not idxs:
        _raise_value_error(arg_name="indices")

    for i, idx in enumerate(idxs):
        if not isinstance(idx, int):
            _raise_type_error(arg_name="indices", type_msg="int", actual_value=idx, idx=i)
        _ensure_non_negative(idx, "index")


def check_after(after: Any) -> None:
    if not isinstance(after, (int, float)):
        _raise_type_error(arg_name="after", type_msg="int or float")
    _ensure_non_negative(after, "after")


def check_bool(arg: Any, arg_name: str) -> None:
    if not isinstance(arg, bool):
        _raise_type_error(arg_name, type_msg="bool")


def _ensure_non_negative(num: int | float | Sequence[int], arg_name: NumArg) -> None:
    if isinstance(num, Sequence):
        if any(n < 0 for n in num):
            raise InvalidArgumentError(f"{arg_name!r} must be non-negative")
        return

    if num < 0:
        raise InvalidArgumentError(f"{arg_name!r} must be non-negative")


def check_cond(cond: Any) -> None:
    if not isinstance(cond, str):
        _raise_type_error(arg_name="cond", type_msg="str")


def _raise_type_error(
    arg_name: str,
    type_msg: str,
    actual_value: Any = _NO_VALUE,
    idx: int | None = None,
    key: Any = _NO_VALUE,
) -> None:
    if actual_value is _NO_VALUE:
        if key is _NO_VALUE:
            raise TypeError(f"{arg_name} must be {type_msg}")
        else:
            raise TypeError(
                f"{arg_name}: expected key type {type_msg}, got {type(key).__name__} (key={key!r})"
            )
    else:
        if idx is not None:
            raise TypeError(
                f"{arg_name}[{idx}]: expected {type_msg}, got {type(actual_value).__name__}"
            )
        if key is not _NO_VALUE:
            raise TypeError(
                f"{arg_name}[{key!r}]: expected value type {type_msg}, "
                f"got {type(actual_value).__name__}"
            )


def _raise_value_error(arg_name: str) -> None:
    raise InvalidArgumentError(f"{arg_name} must not be empty")
