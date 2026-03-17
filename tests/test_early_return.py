from pathlib import Path
import sys

import pytest

ROOT = str(Path(__file__).resolve().parents[1] / "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from triggon import InvalidArgumentError, TrigFunc, Triggon
from triggon.errors.public import InactiveCaptureError, UnregisteredLabelError


def _run_nested_capture_return():
    tg = Triggon.from_labels({"A": 1, "B": 2})

    with tg.capture_return() as outer:
        with tg.capture_return() as inner:
            tg.set_trigger("A")
            tg.trigger_return("A", value=100)

        tg.set_trigger("B")
        tg.trigger_return("B", value=200)

    return outer, inner


def test_requires_active_ctx():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InactiveCaptureError):
        tg.trigger_return("A", value=10)


def test_defaults_when_not_triggered():
    tg = Triggon.from_label("A", new_values=1)

    with tg.capture_return() as result:
        pass

    assert result.triggered is False
    assert result.value is None


def test_uses_explicit_value():
    tg = Triggon.from_label("A", new_values=1)

    def run():
        tg.set_trigger("A")
        tg.trigger_return("A", value=300)

    with tg.capture_return() as result:
        run()

    assert result.triggered is True
    assert result.value == 300


def test_returns_none_when_inactive():
    tg = Triggon.from_labels({"A": 1, "B": 2})

    with tg.capture_return() as result:
        assert tg.trigger_return("A", value=300) is None

    assert result.triggered is False
    assert result.value is None


def test_triggers_for_active_indexed_label():
    tg = Triggon.from_label("A", new_values=(10, 20, 30))

    def run():
        tg.set_trigger("A", indices=2)
        tg.trigger_return("A", value=999)

    with tg.capture_return() as result:
        run()

    assert result.triggered is True
    assert result.value == 999


def test_runs_deferred_explicit_value():
    f = TrigFunc()
    tg = Triggon.from_label("A", new_values=1)

    def run():
        tg.set_trigger("A")
        tg.trigger_return("A", value=f.len("abcd"))

    with tg.capture_return() as result:
        run()

    assert result.triggered is True
    assert result.value == 4


def test_deactivates_after_exit():
    tg = Triggon.from_label("A", new_values=1)

    with tg.capture_return():
        pass

    with pytest.raises(InactiveCaptureError):
        tg.trigger_return("A", value=10)


def test_deactivates_after_exc():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(RuntimeError, match="boom"):
        with tg.capture_return():
            raise RuntimeError("boom")

    with pytest.raises(InactiveCaptureError):
        tg.trigger_return("A", value=10)


def test_rejects_unregistered_label():
    tg = Triggon.from_label("A", new_values=1)

    with tg.capture_return():
        with pytest.raises(UnregisteredLabelError):
            tg.trigger_return("B", value=10)


def test_runs_deferred_explicit_value():
    f = TrigFunc()
    tg = Triggon.from_label("A", new_values=1)

    def run():
        tg.set_trigger("A")
        tg.trigger_return("A", value=f.len("hello"))

    with tg.capture_return() as result:
        run()

    assert result.triggered is True
    assert result.value == 5


def test_uses_first_active_label():
    tg = Triggon.from_labels({"A": 10, "B": 20, "C": 30})

    def run():
        tg.set_trigger(("B", "C"))
        tg.trigger_return(("A", "B", "C"), value=999)

    with tg.capture_return() as result:
        run()

    assert result.triggered is True
    assert result.value == 999


def test_marks_none_value_as_triggered():
    tg = Triggon.from_label("A", new_values=1)

    def run():
        tg.set_trigger("A")
        tg.trigger_return("A", value=None)

    with tg.capture_return() as result:
        run()

    assert result.triggered is True
    assert result.value is None


def test_nested_keeps_inner_result():
    outer, inner = _run_nested_capture_return()

    assert inner.triggered is True
    assert inner.value == 100


def test_nested_restores_outer_ctx():
    outer, inner = _run_nested_capture_return()

    assert inner.triggered is True
    assert outer.triggered is True
    assert outer.value == 200


@pytest.mark.parametrize(
    "call",
    [
        lambda tg: tg.trigger_return(1, value=10),
    ],
)
def test_rejects_invalid_arg_types(call):
    tg = Triggon.from_label("A", new_values=1)

    with tg.capture_return():
        with pytest.raises(TypeError):
            call(tg)

def test_rejects_symbol_labels():
    tg = Triggon.from_label("A", new_values=1)

    with tg.capture_return():
        with pytest.raises(InvalidArgumentError):
            tg.trigger_return("*A", value=10)
