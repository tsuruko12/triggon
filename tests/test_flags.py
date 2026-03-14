from pathlib import Path
import sys
from time import monotonic, sleep

import pytest

ROOT = str(Path(__file__).resolve().parents[1] / "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from triggon import InvalidArgumentError, Triggon


def wait_until(predicate, timeout: float = 0.4, interval: float = 0.005):
    deadline = monotonic() + timeout

    while monotonic() < deadline:
        if predicate():
            return
        sleep(interval)

    assert predicate()


def test_is_triggered_reports_active_labels():
    tg = Triggon.from_labels({"A": 1, "B": 2, "C": 3})

    tg.set_trigger(("A", "C"))

    assert tg.is_triggered("A") is True
    assert tg.is_triggered("B") is False
    assert tg.is_triggered("C") is True
    assert tg.is_triggered(("A", "C")) is True
    assert tg.is_triggered(("A", "B")) is False
    assert tg.is_triggered(("B", "C"), match_all=False) is True


def test_revert_turns_off_only_requested_labels():
    tg = Triggon.from_labels({"A": 1, "B": 2, "C": 3})

    tg.set_trigger(("A", "B", "C"))
    tg.revert(("A", "C"))

    assert tg.is_triggered("A") is False
    assert tg.is_triggered("B") is True
    assert tg.is_triggered("C") is False


def test_cond_controls_trigger():
    tg = Triggon.from_label("A", new_values=1)
    enabled = False

    tg.set_trigger("A", cond="enabled")
    assert tg.is_triggered("A") is False

    enabled = True
    tg.set_trigger("A", cond="enabled")
    assert tg.is_triggered("A") is True


def test_cond_controls_revert():
    tg = Triggon.from_label("A", new_values=1)
    enabled = True

    tg.set_trigger("A")
    tg.revert("A", cond="not enabled")
    assert tg.is_triggered("A") is True

    tg.revert("A", cond="enabled")
    assert tg.is_triggered("A") is False


def test_set_trigger_all_activates_all_labels():
    tg = Triggon.from_labels({"A": 1, "B": 2, "C": 3})

    tg.set_trigger(all=True)

    assert tg.is_triggered(("A", "B", "C")) is True


def test_revert_all_deactivates_all_labels():
    tg = Triggon.from_labels({"A": 1, "B": 2, "C": 3})

    tg.set_trigger(all=True)
    tg.revert(all=True)

    assert tg.is_triggered("A") is False
    assert tg.is_triggered("B") is False
    assert tg.is_triggered("C") is False


def test_revert_disable_prevents_future_reactivation():
    tg = Triggon.from_label("A", new_values=1)

    tg.set_trigger("A")
    assert tg.is_triggered("A") is True

    tg.revert("A", disable=True)

    assert tg.is_triggered("A") is False

    tg.set_trigger("A")

    assert tg.is_triggered("A") is False


def test_set_trigger_requires_labels_or_all():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InvalidArgumentError, match="no labels specified"):
        tg.set_trigger()


def test_revert_requires_labels_or_all():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InvalidArgumentError, match="no labels specified"):
        tg.revert()


def test_after_delays_trigger():
    tg = Triggon.from_label("A", new_values=1)

    tg.set_trigger("A", after=0.05)
    assert tg.is_triggered("A") is False

    sleep(0.08)
    assert tg.is_triggered("A") is True


def test_after_delays_revert():
    tg = Triggon.from_label("A", new_values=1)

    tg.set_trigger("A")
    tg.revert("A", after=0.05)
    assert tg.is_triggered("A") is True

    sleep(0.08)
    assert tg.is_triggered("A") is False


def test_cond_and_after_gate_delayed_trigger():
    tg = Triggon.from_label("A", new_values=1)
    enabled = False

    tg.set_trigger("A", cond="enabled", after=0.05)
    sleep(0.08)
    assert tg.is_triggered("A") is False

    enabled = True
    tg.set_trigger("A", cond="enabled", after=0.05)
    assert tg.is_triggered("A") is False
    wait_until(lambda: tg.is_triggered("A") is True)


def test_cond_and_after_gate_delayed_revert():
    tg = Triggon.from_label("A", new_values=1)
    enabled = False

    tg.set_trigger("A")
    tg.revert("A", cond="enabled", after=0.05)
    sleep(0.08)
    assert tg.is_triggered("A") is True

    enabled = True
    tg.revert("A", cond="enabled", after=0.05)
    assert tg.is_triggered("A") is True
    wait_until(lambda: tg.is_triggered("A") is False)


def test_revert_reschedule_replaces_pending_delay():
    tg = Triggon.from_label("A", new_values=1)

    tg.set_trigger("A")
    tg.revert("A", after=0.20)
    sleep(0.05)
    assert tg.is_triggered("A") is True

    tg.revert("A", after=0.01, reschedule=True)

    wait_until(lambda: tg.is_triggered("A") is False)
    sleep(0.22)

    assert tg.is_triggered("A") is False


def test_staggered_trigger_delays_are_independent():
    tg = Triggon.from_labels({"A": 1, "B": 2, "C": 3})

    tg.set_trigger("A", after=0.04)
    tg.set_trigger("B", after=0.10)
    tg.set_trigger("C", after=0.16)

    assert tg.is_triggered("A") is False
    assert tg.is_triggered("B") is False
    assert tg.is_triggered("C") is False

    wait_until(lambda: tg.is_triggered("A") is True)
    assert tg.is_triggered("B") is False
    assert tg.is_triggered("C") is False

    wait_until(lambda: tg.is_triggered(("A", "B")) is True)
    assert tg.is_triggered("C") is False

    wait_until(lambda: tg.is_triggered(("A", "B", "C")) is True)


def test_staggered_revert_delays_are_independent():
    tg = Triggon.from_labels({"A": 1, "B": 2, "C": 3})

    tg.set_trigger(("A", "B", "C"))
    tg.revert("A", after=0.04)
    tg.revert("B", after=0.10)
    tg.revert("C", after=0.16)

    assert tg.is_triggered(("A", "B", "C")) is True

    wait_until(lambda: tg.is_triggered("A") is False)
    assert tg.is_triggered("B") is True
    assert tg.is_triggered("C") is True

    wait_until(lambda: tg.is_triggered("B") is False)
    assert tg.is_triggered("C") is True

    wait_until(lambda: tg.is_triggered(("A", "B", "C"), match_all=False) is False)


@pytest.mark.parametrize("action", ["set_trigger", "revert"])
def test_cond_raises_for_missing_names(action):
    tg = Triggon.from_label("A", new_values=1)

    if action == "revert":
        tg.set_trigger("A")
        with pytest.raises(NameError, match=r"cond: 'missing_name' is not defined"):
            tg.revert("A", cond="missing_name")
    else:
        with pytest.raises(NameError, match=r"cond: 'missing_name' is not defined"):
            tg.set_trigger("A", cond="missing_name")


@pytest.mark.parametrize("action", ["set_trigger", "revert"])
def test_cond_raises_for_missing_attrs(action):
    tg = Triggon.from_label("A", new_values=1)

    class Box:
        value = 1

    box = Box()

    if action == "revert":
        tg.set_trigger("A")
        with pytest.raises(AttributeError, match=r"cond: .*has no attribute 'missing'"):
            tg.revert("A", cond="box.missing == 1")
    else:
        with pytest.raises(AttributeError, match=r"cond: .*has no attribute 'missing'"):
            tg.set_trigger("A", cond="box.missing == 1")


@pytest.mark.parametrize("action", ["set_trigger", "revert"])
def test_cond_raises_for_invalid_allowed_calls(action):
    tg = Triggon.from_label("A", new_values=1)

    if action == "revert":
        tg.set_trigger("A")
        with pytest.raises(TypeError, match=r"cond: object of type 'int' has no len\(\)"):
            tg.revert("A", cond="len(1) == 1")
    else:
        with pytest.raises(TypeError, match=r"cond: object of type 'int' has no len\(\)"):
            tg.set_trigger("A", cond="len(1) == 1")


@pytest.mark.parametrize("action", ["set_trigger", "revert"])
@pytest.mark.parametrize(
    ("expr", "match"),
    [
        ("x = 1", "cond: only expressions are allowed"),
        ("len(text)", "cond: expression must evaluate to bool"),
        ("maker().value == 1", "cond: invalid attribute access"),
        ("text.lower() == 'a'", "cond: method 'lower' is not allowed"),
        ("pow(1, 2) == 1", "cond: function 'pow' is not allowed"),
        ("factory()() == 1", "cond: dynamic calls are not allowed"),
    ],
)
def test_cond_rejects_invalid_expressions(action, expr, match):
    tg = Triggon.from_label("A", new_values=1)
    text = "A"

    def maker():
        return object()

    def factory():
        return lambda: 1

    if action == "revert":
        tg.set_trigger("A")
        with pytest.raises(InvalidArgumentError, match=match):
            tg.revert("A", cond=expr)
    else:
        with pytest.raises(InvalidArgumentError, match=match):
            tg.set_trigger("A", cond=expr)


@pytest.mark.parametrize(
    "call",
    [
        lambda tg: tg.set_trigger(1),
        lambda tg: tg.set_trigger("A", indices="bad"),
        lambda tg: tg.set_trigger("A", all="yes"),
        lambda tg: tg.set_trigger("A", cond=1),
        lambda tg: tg.set_trigger("A", after="soon"),
        lambda tg: tg.set_trigger("A", reschedule="yes"),
    ],
)
def test_set_trigger_rejects_invalid_arg_types(call):
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(TypeError):
        call(tg)


@pytest.mark.parametrize(
    "call",
    [
        lambda tg: tg.revert(1),
        lambda tg: tg.revert("A", all="yes"),
        lambda tg: tg.revert("A", disable="yes"),
        lambda tg: tg.revert("A", cond=1),
        lambda tg: tg.revert("A", after="soon"),
        lambda tg: tg.revert("A", reschedule="yes"),
    ],
)
def test_revert_rejects_invalid_arg_types(call):
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(TypeError):
        call(tg)


@pytest.mark.parametrize(
    "call",
    [
        lambda tg: tg.set_trigger("A", indices=-1),
        lambda tg: tg.set_trigger("A", indices=(-1,)),
        lambda tg: tg.set_trigger("A", after=-0.1),
    ],
)
def test_set_trigger_rejects_negative_values(call):
    tg = Triggon.from_label("A", new_values=(1, 2))

    with pytest.raises(InvalidArgumentError, match="must be non-negative"):
        call(tg)


@pytest.mark.parametrize(
    "call",
    [
        lambda tg: tg.set_trigger(("A", "B"), indices=(0,)),
        lambda tg: tg.set_trigger("A", indices=(0, 1)),
    ],
)
def test_set_trigger_rejects_idxs_length_mismatch(call):
    tg = Triggon.from_labels({"A": (10, 20), "B": (30, 40)})

    with pytest.raises(InvalidArgumentError, match="same length"):
        call(tg)


def test_set_trigger_raises_for_out_of_range_idx():
    tg = Triggon.from_label("A", new_values=(10, 20))

    with pytest.raises(IndexError, match=r"index 5 is out of range for label 'A'"):
        tg.set_trigger("A", indices=5)


def test_revert_rejects_negative_after():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InvalidArgumentError, match="must be non-negative"):
        tg.revert("A", after=-0.1)
