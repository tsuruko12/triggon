from pathlib import Path
import sys
from time import monotonic, sleep

import pytest

ROOT = str(Path(__file__).resolve().parents[1] / "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from triggon import InvalidArgumentError, TrigFunc, Triggon, UpdateError
from triggon._internal.keys import REVERT, TRIGGER


def wait_until(predicate, timeout: float = 0.4, interval: float = 0.005):
    deadline = monotonic() + timeout

    while monotonic() < deadline:
        if predicate():
            return
        sleep(interval)

    assert predicate()


registered_value = 0
registered_a = 0
registered_b = 0


def _close_debug_handlers(tg: Triggon) -> None:
    logger = tg._logger
    if logger is None:
        return

    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
        logger.removeHandler(handler)


def _make_staggered_registered_refs():
    tg = Triggon.from_labels({"A": 10, "B": 20, "C": 30})
    global registered_a, registered_b
    registered_a = 0
    registered_b = 0

    class Holder:
        value = 0

    holder = Holder()

    tg.register_refs(
        {
            "A": {"registered_a": 0},
            "B": {"registered_b": 0},
            "C": {"holder.value": 0},
        }
    )

    return tg, holder


def test_switch_lit_tracks_trigger_state():
    tg = Triggon.from_label("A", new_values=10)

    assert tg.switch_lit("A", original_val=0) == 0

    tg.set_trigger("A")
    assert tg.switch_lit("A", original_val=0) == 10

    tg.revert("A")
    assert tg.switch_lit("A", original_val=0) == 0


def test_register_ref_updates_and_restores_glob():
    tg = Triggon.from_label("A", new_values=10)
    global registered_value
    registered_value = 0

    tg.register_ref("A", name="registered_value")
    assert registered_value == 0

    tg.set_trigger("A")
    assert registered_value == 10

    tg.revert("A")
    assert registered_value == 0


def test_register_refs_update_multiple_targets():
    tg = Triggon.from_labels({"A": 10, "B": 20})
    global registered_a, registered_b
    registered_a = 0
    registered_b = 0

    class Holder:
        value = 0

    holder = Holder()

    tg.register_refs({"A": {"registered_a": 0}, "B": {"registered_b": 0, "holder.value": 0}})

    tg.set_trigger("A")
    assert registered_a == 10
    assert registered_b == 0
    assert holder.value == 0

    tg.set_trigger("B")
    assert registered_a == 10
    assert registered_b == 20
    assert holder.value == 20

    tg.revert("A")
    assert registered_a == 0
    assert registered_b == 20
    assert holder.value == 20

    tg.revert("B")
    assert registered_b == 0
    assert holder.value == 0


def test_switch_lit_runs_deferred_value():
    f = TrigFunc()
    calls = []

    def make_value():
        calls.append("run")
        return 10

    tg = Triggon.from_label("A", new_values=f.make_value())

    assert tg.switch_lit("A", original_val=0) == 0
    assert calls == []

    tg.set_trigger("A")
    assert tg.switch_lit("A", original_val=0) == 10
    assert calls == ["run"]


def test_register_ref_updates_with_deferred_value():
    f = TrigFunc()
    calls = []
    global registered_value
    registered_value = 0

    def make_value():
        calls.append("run")
        return 10

    tg = Triggon.from_label("A", new_values=f.make_value())
    tg.register_ref("A", name="registered_value")

    assert registered_value == 0
    assert calls == []

    tg.set_trigger("A")
    assert registered_value == 10
    assert calls == ["run"]

    tg.revert("A")
    assert registered_value == 0
    assert calls == ["run"]


def test_register_refs_update_with_deferred_values():
    f = TrigFunc()
    calls = []
    global registered_a, registered_b
    registered_a = 0
    registered_b = 0

    class Holder:
        value = 0

    holder = Holder()

    def make_a():
        calls.append("A")
        return 10

    def make_b():
        calls.append("B")
        return 20

    tg = Triggon.from_labels({"A": f.make_a(), "B": f.make_b()})
    tg.register_refs({"A": {"registered_a": 0}, "B": {"registered_b": 0, "holder.value": 0}})

    assert registered_a == 0
    assert registered_b == 0
    assert holder.value == 0
    assert calls == []

    tg.set_trigger(("A", "B"))
    assert registered_a == 10
    assert registered_b == 20
    assert holder.value == 20
    assert calls == ["A", "B", "B"]

    tg.revert(("A", "B"))
    assert registered_a == 0
    assert registered_b == 0
    assert holder.value == 0
    assert calls == ["A", "B", "B"]


def test_register_ref_restores_deferred_value_without_running():
    f = TrigFunc()
    calls = []
    global registered_value

    def make_value():
        calls.append("run")
        return 99

    original = f.make_value()
    registered_value = original

    tg = Triggon.from_label("A", new_values=10)
    tg.register_ref("A", name="registered_value")

    tg.set_trigger("A")
    assert registered_value == 10
    assert calls == []

    tg.revert("A")
    assert registered_value is original
    assert calls == []


def test_register_refs_restore_deferred_values_without_running():
    f = TrigFunc()
    calls = []
    global registered_a, registered_b

    def make_a():
        calls.append("A")
        return 99

    def make_b():
        calls.append("B")
        return 88

    original_a = f.make_a()
    original_b = f.make_b()
    registered_a = original_a
    registered_b = original_b

    tg = Triggon.from_labels({"A": 10, "B": 20})
    tg.register_refs({"A": {"registered_a": 0}, "B": {"registered_b": 0}})

    tg.set_trigger(("A", "B"))
    assert registered_a == 10
    assert registered_b == 20
    assert calls == []

    tg.revert(("A", "B"))
    assert registered_a is original_a
    assert registered_b is original_b
    assert calls == []


def test_register_ref_stays_disabled_after_revert():
    tg = Triggon.from_label("A", new_values=10)
    global registered_value
    registered_value = 0

    tg.register_ref("A", name="registered_value")

    tg.set_trigger("A")
    assert registered_value == 10

    tg.revert("A", disable=True)
    assert registered_value == 0

    tg.set_trigger("A")
    assert registered_value == 0


def test_register_refs_stay_disabled_after_revert():
    tg = Triggon.from_labels({"A": 10, "B": 20})
    global registered_a, registered_b
    registered_a = 0
    registered_b = 0

    tg.register_refs({"A": {"registered_a": 0}, "B": {"registered_b": 0}})

    tg.set_trigger(("A", "B"))
    assert registered_a == 10
    assert registered_b == 20

    tg.revert("B", disable=True)
    assert registered_a == 10
    assert registered_b == 0

    tg.set_trigger("B")
    assert registered_a == 10
    assert registered_b == 0


def test_reschedule_replaces_pending_update():
    tg = Triggon.from_label("A", new_values=(10, 20))
    global registered_value
    registered_value = 0

    tg.register_ref("A", name="registered_value")
    tg.set_trigger("A", indices=0, after=0.20)
    sleep(0.05)

    tg.set_trigger("A", indices=1, after=0.01, reschedule=True)

    wait_until(lambda: registered_value == 20)
    sleep(0.22)

    assert tg.is_triggered("A") is True
    assert registered_value == 20


def test_switch_lit_uses_single_symbol_label():
    tg = Triggon.from_label("A", new_values=(10, 20, 30))

    tg.set_trigger("A")

    assert tg.switch_lit("*A", original_val=0) == 20


def test_switch_lit_uses_double_symbol_label():
    tg = Triggon.from_label("A", new_values=(10, 20, 30))

    tg.set_trigger("A")

    assert tg.switch_lit("**A", original_val=0) == 30


def test_register_ref_uses_symbol_label_when_active():
    tg = Triggon.from_label("A", new_values=(10, 20, 30))
    global registered_value
    registered_value = 0

    tg.set_trigger("A")
    tg.register_ref("*A", name="registered_value")

    assert registered_value == 20


def test_set_trigger_uses_single_symbol_label_for_registered_values():
    tg = Triggon.from_label("A", new_values=(10, 20, 30))
    global registered_value
    registered_value = 0

    tg.register_ref("A", name="registered_value")

    tg.set_trigger("*A")
    assert registered_value == 20


def test_set_trigger_uses_double_symbol_label_for_registered_values():
    tg = Triggon.from_label("A", new_values=(10, 20, 30))
    global registered_value
    registered_value = 0

    tg.register_ref("A", name="registered_value")

    tg.set_trigger("**A")
    assert registered_value == 30

    tg.revert("A")
    assert registered_value == 0


def test_switch_lit_respects_cond_delayed_trigger():
    tg = Triggon.from_label("A", new_values=10)
    enabled = False

    tg.set_trigger("A", cond="enabled", after=0.05)
    sleep(0.08)
    assert tg.switch_lit("A", original_val=0) == 0

    enabled = True
    tg.set_trigger("A", cond="enabled", after=0.05)
    assert tg.switch_lit("A", original_val=0) == 0
    wait_until(lambda: tg.switch_lit("A", original_val=0) == 10)


def test_switch_lit_respects_cond_delayed_revert():
    tg = Triggon.from_label("A", new_values=10)
    enabled = True

    tg.set_trigger("A")

    enabled = False
    tg.revert("A", cond="enabled", after=0.05)
    sleep(0.08)
    assert tg.switch_lit("A", original_val=0) == 10

    enabled = True
    tg.revert("A", cond="enabled", after=0.05)
    assert tg.switch_lit("A", original_val=0) == 10
    wait_until(lambda: tg.switch_lit("A", original_val=0) == 0)


def test_register_ref_respects_cond_delayed_trigger():
    tg = Triggon.from_label("A", new_values=10)
    global registered_value
    registered_value = 0
    enabled = False

    tg.register_ref("A", name="registered_value")

    tg.set_trigger("A", cond="enabled", after=0.05)
    sleep(0.08)
    assert registered_value == 0

    enabled = True
    tg.set_trigger("A", cond="enabled", after=0.05)
    assert registered_value == 0
    wait_until(lambda: registered_value == 10)


def test_register_ref_respects_cond_delayed_revert():
    tg = Triggon.from_label("A", new_values=10)
    global registered_value
    registered_value = 0
    enabled = True

    tg.register_ref("A", name="registered_value")
    tg.set_trigger("A")

    enabled = False
    tg.revert("A", cond="enabled", after=0.05)
    sleep(0.08)
    assert registered_value == 10

    enabled = True
    tg.revert("A", cond="enabled", after=0.05)
    assert registered_value == 10
    wait_until(lambda: registered_value == 0)


def test_register_refs_follow_staggered_trigger_updates():
    tg, holder = _make_staggered_registered_refs()

    tg.set_trigger("A", after=0.04)
    tg.set_trigger("B", after=0.10)
    tg.set_trigger("C", after=0.16)

    assert registered_a == 0
    assert registered_b == 0
    assert holder.value == 0

    wait_until(lambda: registered_a == 10)
    assert registered_b == 0
    assert holder.value == 0

    wait_until(lambda: registered_b == 20)
    assert holder.value == 0

    wait_until(lambda: holder.value == 30)


def test_register_refs_follow_staggered_revert_updates():
    tg, holder = _make_staggered_registered_refs()

    tg.set_trigger(("A", "B", "C"))
    assert registered_a == 10
    assert registered_b == 20
    assert holder.value == 30

    tg.revert("A", after=0.04)
    tg.revert("B", after=0.10)
    tg.revert("C", after=0.16)

    assert registered_a == 10
    assert registered_b == 20
    assert holder.value == 30

    wait_until(lambda: registered_a == 0)
    assert registered_b == 20
    assert holder.value == 30

    wait_until(lambda: registered_b == 0)
    assert holder.value == 30

    wait_until(lambda: holder.value == 0)


def test_register_ref_raises_when_attr_update_fails():
    tg = Triggon.from_label("A", new_values=10)

    class WriteProtected:
        def __init__(self):
            self._value = 0

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, new_value):
            if new_value == 10:
                raise ValueError("cannot apply new value")
            self._value = new_value

    box = WriteProtected()
    tg.register_ref("A", name="box.value")

    with pytest.raises(UpdateError, match="failed to update 'box.value'"):
        tg.set_trigger("A")


def test_register_ref_raises_when_attr_restore_fails():
    tg = Triggon.from_label("A", new_values=10)

    class WriteOnce:
        def __init__(self):
            self._value = 0

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, new_value):
            if new_value == 0 and self._value != 0:
                raise ValueError("cannot restore original value")
            self._value = new_value

    box = WriteOnce()
    tg.register_ref("A", name="box.value")

    tg.set_trigger("A")
    assert box.value == 10

    with pytest.raises(UpdateError, match="failed to update 'box.value'"):
        tg.revert("A")


def test_register_refs_raises_when_attr_update_fails():
    tg = Triggon.from_label("A", new_values=10)

    class WriteProtected:
        def __init__(self):
            self._value = 0

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, new_value):
            if new_value == 10:
                raise ValueError("cannot apply new value")
            self._value = new_value

    box = WriteProtected()
    tg.register_refs({"A": {"box.value": 0}})

    with pytest.raises(UpdateError, match="failed to update 'box.value'"):
        tg.set_trigger("A")


def test_delayed_trigger_failure_logs_update_err(monkeypatch):
    tg = Triggon.from_label("A", new_values=10, debug=True)
    logged = []

    class WriteProtected:
        def __init__(self):
            self._value = 0

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, new_value):
            if new_value == 10:
                raise ValueError("cannot apply new value")
            self._value = new_value

    box = WriteProtected()
    tg.register_ref("A", name="box.value")
    assert tg._logger is not None
    monkeypatch.setattr(tg._logger, "exception", lambda exc: logged.append(str(exc)))

    try:
        tg.set_trigger("A", after=0.01)
        wait_until(lambda: len(logged) == 1)
    finally:
        _close_debug_handlers(tg)

    assert "failed to update 'box.value'" in logged[0]
    assert "cannot apply new value" in logged[0]


def test_delayed_trigger_failure_clears_delay_state():
    tg = Triggon.from_label("A", new_values=10)

    class WriteProtected:
        def __init__(self):
            self._value = 0

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, new_value):
            if new_value == 10:
                raise ValueError("cannot apply new value")
            self._value = new_value

    box = WriteProtected()
    tg.register_ref("A", name="box.value")

    tg.set_trigger("A", after=0.01)

    wait_until(lambda: tg._label_delay_state["A"][TRIGGER].is_delay is False)

    delay_state = tg._label_delay_state["A"][TRIGGER]
    assert tg.is_triggered("A") is True
    assert box.value == 0
    assert delay_state.timer is None
    assert delay_state.labels is None

    tg.revert("A")
    assert tg.is_triggered("A") is False


def test_delayed_revert_failure_logs_update_err(monkeypatch):
    tg = Triggon.from_label("A", new_values=10, debug=True)
    logged = []

    class WriteOnce:
        def __init__(self):
            self._value = 0

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, new_value):
            if new_value == 0 and self._value != 0:
                raise ValueError("cannot restore original value")
            self._value = new_value

    box = WriteOnce()
    tg.register_ref("A", name="box.value")
    tg.set_trigger("A")
    assert tg._logger is not None
    monkeypatch.setattr(tg._logger, "exception", lambda exc: logged.append(str(exc)))

    try:
        tg.revert("A", after=0.01)
        wait_until(lambda: len(logged) == 1)
    finally:
        _close_debug_handlers(tg)

    assert "failed to update 'box.value'" in logged[0]
    assert "cannot restore original value" in logged[0]


def test_delayed_revert_failure_clears_delay_state():
    tg = Triggon.from_label("A", new_values=10)

    class WriteOnce:
        def __init__(self):
            self._value = 0

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, new_value):
            if new_value == 0 and self._value != 0:
                raise ValueError("cannot restore original value")
            self._value = new_value

    box = WriteOnce()
    tg.register_ref("A", name="box.value")
    tg.set_trigger("A")

    tg.revert("A", after=0.01)

    wait_until(lambda: tg._label_delay_state["A"][REVERT].is_delay is False)

    delay_state = tg._label_delay_state["A"][REVERT]
    assert tg.is_triggered("A") is False
    assert box.value == 10
    assert delay_state.timer is None
    assert delay_state.labels is None


@pytest.mark.parametrize(
    "call",
    [
        lambda tg: tg.switch_lit(1, original_val=0),
        lambda tg: tg.switch_lit("A", original_val=0, indices="bad"),
    ],
)
def test_switch_lit_rejects_invalid_arg_types(call):
    tg = Triggon.from_label("A", new_values=10)

    with pytest.raises(TypeError):
        call(tg)


def test_switch_lit_rejects_negative_idxs():
    tg = Triggon.from_label("A", new_values=(10, 20))

    with pytest.raises(InvalidArgumentError, match="must be non-negative"):
        tg.switch_lit("A", original_val=0, indices=-1)


@pytest.mark.parametrize("indices", [(0,), (0, 1, 0)])
def test_switch_lit_rejects_idxs_length_mismatch(indices):
    tg = Triggon.from_labels({"A": (10, 20), "B": (30, 40)})

    with pytest.raises(InvalidArgumentError, match="same length"):
        tg.switch_lit(("A", "B"), original_val=0, indices=indices)


def test_switch_lit_raises_for_out_of_range_idx():
    tg = Triggon.from_label("A", new_values=(10, 20))

    with pytest.raises(IndexError, match=r"index 5 is out of range for label 'A'"):
        tg.switch_lit("A", original_val=0, indices=5)


@pytest.mark.parametrize(
    "call",
    [
        lambda tg: tg.register_ref(1, name="registered_value"),
        lambda tg: tg.register_ref("A", name=1),
        lambda tg: tg.register_ref("A", name="registered_value", index="bad"),
    ],
)
def test_register_ref_rejects_invalid_arg_types(call):
    tg = Triggon.from_label("A", new_values=10)

    with pytest.raises(TypeError):
        call(tg)


def test_register_ref_rejects_negative_idx():
    tg = Triggon.from_label("A", new_values=(10, 20))

    with pytest.raises(InvalidArgumentError, match="must be non-negative"):
        tg.register_ref("A", name="registered_value", index=-1)


def test_register_ref_raises_for_out_of_range_idx():
    tg = Triggon.from_label("A", new_values=(10, 20))

    with pytest.raises(IndexError, match=r"index 5 is out of range for label 'A'"):
        tg.register_ref("A", name="registered_value", index=5)


@pytest.mark.parametrize(
    "call",
    [
        lambda tg: tg.register_refs([]),
        lambda tg: tg.register_refs({1: {"registered_a": 0}}),
        lambda tg: tg.register_refs({"A": []}),
        lambda tg: tg.register_refs({"A": {1: 0}}),
        lambda tg: tg.register_refs({"A": {"registered_a": "bad"}}),
    ],
)
def test_register_refs_rejects_invalid_arg_types(call):
    tg = Triggon.from_label("A", new_values=10)

    with pytest.raises(TypeError):
        call(tg)


def test_register_refs_rejects_empty_map():
    tg = Triggon.from_label("A", new_values=(10, 20))

    with pytest.raises(InvalidArgumentError, match="must not be empty"):
        tg.register_refs({})


def test_register_refs_rejects_negative_idxs():
    tg = Triggon.from_label("A", new_values=(10, 20))

    with pytest.raises(InvalidArgumentError, match="must be non-negative"):
        tg.register_refs({"A": {"registered_a": -1}})


def test_register_refs_raise_for_out_of_range_idx():
    tg = Triggon.from_label("A", new_values=(10, 20))

    with pytest.raises(IndexError, match=r"index 5 is out of range for label 'A'"):
        tg.register_refs({"A": {"registered_a": 5}})
