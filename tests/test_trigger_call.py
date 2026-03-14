from pathlib import Path
import sys

import pytest

ROOT = str(Path(__file__).resolve().parents[1] / "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from triggon import InvalidArgumentError, TrigFunc, Triggon, UnregisteredLabelError


def test_runs_deferred_target_when_active():
    f = TrigFunc()
    tg = Triggon.from_label("A", new_values=1)

    tg.set_trigger("A")

    assert tg.trigger_call("A", f.len("abcd")) == 4


def test_returns_none_when_inactive():
    f = TrigFunc()
    tg = Triggon.from_label("A", new_values=1)

    assert tg.trigger_call("A", f.len("abcd")) is None


def test_accepts_multiple_labels():
    f = TrigFunc()
    tg = Triggon.from_labels({"A": 1, "B": 2})

    tg.set_trigger("B")

    assert tg.trigger_call(("A", "B"), f.len("hello")) == 5


def test_rejects_non_trigfunc_target():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(TypeError, match="deferred using a TrigFunc instance"):
        tg.trigger_call("A", 123)


def test_rejects_missing_call_suffix():
    f = TrigFunc()
    tg = Triggon.from_label("A", new_values=1)

    tg.set_trigger("A")

    with pytest.raises(TypeError, match="must end with a function or method call"):
        tg.trigger_call("A", f.len)


def test_rejects_unregistered_label():
    f = TrigFunc()
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(UnregisteredLabelError):
        tg.trigger_call("B", f.len("abc"))


def test_rejects_symbol_labels():
    f = TrigFunc()
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InvalidArgumentError):
        tg.trigger_call("*A", f.len("abc"))
