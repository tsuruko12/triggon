from pathlib import Path
import sys

import pytest

ROOT = str(Path(__file__).resolve().parents[1] / "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from triggon import InvalidArgumentError, Triggon


class CustomTriggon(Triggon):
    pass


def test_init_single_label():
    tg = Triggon("A", 10)

    tg.set_trigger("A")

    assert tg.switch_lit("A", 0) == 10


def test_init_defaults_to_none():
    tg = Triggon("A")

    tg.set_trigger("A")

    assert tg.switch_lit("A", 1) is None


def test_init_seq_becomes_indexed():
    tg = Triggon("A", [10, 20, 30])

    tg.set_trigger("A", indices=1)

    assert tg.switch_lit("A", 0, indices=1) == 20


def test_init_with_label_values():
    tg = Triggon(label_values={"A": 1, "B": 2})

    tg.set_trigger("B")

    assert tg.switch_lit("A", 0) == 0
    assert tg.switch_lit("B", 0) == 2


def test_init_keeps_wrapped_seq():
    tg = Triggon(label_values={"A": ([1, 2],)})

    tg.set_trigger("A")

    assert tg.switch_lit("A", 0) == [1, 2]


def test_init_rejects_missing_labels():
    with pytest.raises(InvalidArgumentError):
        Triggon()


def test_init_rejects_non_str_label():
    with pytest.raises(TypeError):
        Triggon(1, 1)


def test_init_rejects_label_values_with_positional_args():
    with pytest.raises(InvalidArgumentError):
        Triggon("A", 1, label_values={"B": 2})


def test_init_rejects_empty_label_values():
    with pytest.raises(InvalidArgumentError):
        Triggon(label_values={})


def test_init_rejects_non_map_label_values():
    with pytest.raises(TypeError):
        Triggon(label_values=[("A", 1)])


def test_init_rejects_non_str_label_value_key():
    with pytest.raises(TypeError):
        Triggon(label_values={1: "A"})


def test_init_rejects_symbol_prefixed_label():
    with pytest.raises(InvalidArgumentError):
        Triggon("*A", 1)


def test_init_rejects_symbol_prefixed_label_value_key():
    with pytest.raises(InvalidArgumentError):
        Triggon(label_values={"*A": 1, "B": 2})


def test_init_rejects_empty_debug_seq():
    with pytest.raises(InvalidArgumentError, match="debug must not be empty"):
        Triggon("A", 1, debug=[])


def test_init_rejects_non_str_debug_item():
    with pytest.raises(TypeError, match=r"debug\[1\]: expected str, got int"):
        Triggon("A", 1, debug=("A", 1))


def test_from_label_seq_becomes_indexed():
    tg = Triggon.from_label("A", new_values=[10, 20, 30])

    assert tg.switch_lit("A", 0) == 0

    tg.set_trigger("A", indices=2)

    assert tg.switch_lit("A", 0, indices=2) == 30


def test_from_labels_accepts_multiple_labels():
    tg = Triggon.from_labels({"A": 1, "B": ([1, 2],)})

    tg.set_trigger("A")
    assert tg.switch_lit("A", 0) == 1


def test_from_labels_keeps_wrapped_seq():
    tg = Triggon.from_labels({"A": 1, "B": ([1, 2],)})

    tg.set_trigger("B")
    assert tg.switch_lit("B", 0) == [1, 2]


def test_from_labels_sequence_becomes_indexed():
    tg = Triggon.from_labels({"A": [10, 20, 30]})

    tg.set_trigger("A", indices=1)

    assert tg.switch_lit("A", 0, indices=1) == 20


def test_from_label_preserves_subclass():
    tg = CustomTriggon.from_label("A", new_values=1)

    assert isinstance(tg, CustomTriggon)


def test_from_labels_preserves_subclass():
    tg = CustomTriggon.from_labels({"A": 1})

    assert isinstance(tg, CustomTriggon)


def test_from_label_rejects_symbol_prefix():
    with pytest.raises(InvalidArgumentError):
        Triggon.from_label("*A", new_values=1)


def test_from_label_rejects_non_str_label():
    with pytest.raises(TypeError):
        Triggon.from_label(1, new_values=1)


def test_from_labels_rejects_symbol_prefix():
    with pytest.raises(InvalidArgumentError):
        Triggon.from_labels({"*A": 1, "B": 2})


def test_from_labels_rejects_empty_map():
    with pytest.raises(InvalidArgumentError):
        Triggon.from_labels({})


def test_from_labels_rejects_non_map():
    with pytest.raises(TypeError):
        Triggon.from_labels([("A", 1)])


def test_from_labels_rejects_non_str_key():
    with pytest.raises(TypeError):
        Triggon.from_labels({1: "A"})


def test_add_labels_ignores_duplicate_labels():
    tg = Triggon.from_label("A", new_values=1)

    tg.add_labels({"A": 99, "B": 2})
    tg.set_trigger(("A", "B"))

    assert tg.switch_lit("A", 0) == 1
    assert tg.switch_lit("B", 0) == 2


def test_add_label_registers_single_label():
    tg = Triggon.from_label("A", new_values=1)

    tg.add_label("B", 2)
    tg.set_trigger("B")

    assert tg.switch_lit("A", 0) == 0
    assert tg.switch_lit("B", 0) == 2


def test_add_label_defaults_to_none():
    tg = Triggon.from_label("A", new_values=1)

    tg.add_label("B")
    tg.set_trigger("B")

    assert tg.switch_lit("B", 10) is None


def test_add_label_seq_becomes_indexed():
    tg = Triggon.from_label("A", new_values=1)

    tg.add_label("B", [10, 20, 30])
    tg.set_trigger("B", indices=1)

    assert tg.switch_lit("B", 0, indices=1) == 20


def test_add_labels_registers_multiple_labels():
    tg = Triggon.from_label("A", new_values=1)

    tg.add_labels({"B": 2, "C": ([3, 4],)})
    tg.set_trigger(("B", "C"))

    assert tg.switch_lit("B", 0) == 2
    assert tg.switch_lit("C", 0) == [3, 4]


def test_add_label_rejects_symbol_prefix():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InvalidArgumentError):
        tg.add_label("*B", 2)


def test_add_label_rejects_non_str_label():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(TypeError):
        tg.add_label(1, 2)


def test_add_label_rejects_whitespace_label():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InvalidArgumentError):
        tg.add_label(" ", 2)


def test_add_labels_rejects_symbol_prefix():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InvalidArgumentError):
        tg.add_labels({"*B": 2})


def test_add_labels_rejects_empty_map():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InvalidArgumentError):
        tg.add_labels({})


def test_add_labels_rejects_non_map():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(TypeError):
        tg.add_labels([("B", 2)])


def test_add_labels_rejects_non_str_key():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(TypeError):
        tg.add_labels({1: 2})


def test_add_labels_rejects_whitespace_key():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InvalidArgumentError):
        tg.add_labels({" ": 2})
