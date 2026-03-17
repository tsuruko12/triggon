import logging
import sys
import threading
from contextlib import contextmanager
from collections.abc import Iterator, KeysView, Mapping, Sequence, ValuesView
from dataclasses import dataclass
from typing import Any, Self

from ._internal import (
    _Internal,
    check_after,
    check_bool,
    check_cond,
    check_debug,
    check_idxs,
    check_items,
    check_str_sequence,
    collect_rollback_refs,
    revert_targets,
    to_dict,
    unwrap_value,
)
from ._internal._types.aliases import (
    DebugArg,
    DelayKey,
    IndexArg,
    LabelArg,
    LabelToRefs,
    NameArg,
)
from ._internal._types.structs import (
    DebugConfig,
    DelayState,
    RefMeta,
    RefsByKind,
)
from ._internal.frames import get_callsite, get_target_frame
from ._internal.keys import (
    ATTR,
    GLOB_VAR,
    LOG_VERBOSITY,
    REVERT,
    TRIGGER,
)
from ._internal.sentinel import _NO_VALUE
from .core.mixins import _Core
from .errors.public import InactiveCaptureError, InvalidArgumentError, RollbackNotSupportedError
from .trigfunc import TRIGFUNC_ATTR, TrigFunc


class _EarlyReturn(Exception):
    """Internal signal used to perform an early return inside capture_return()."""


@dataclass(slots=True)
class EarlyReturnResult:
    """Result returned by capture_return()."""

    triggered: bool = False
    value: Any = None


class Triggon(_Core, _Internal):
    """Manage labels, triggers, and value switching for registered targets."""

    debug: DebugConfig
    _logger: logging.Logger | None
    _label_is_active: dict[str, bool]
    _label_delay_state: dict[str, dict[DelayKey, DelayState]]
    _label_is_perm_disabled: dict[str, bool]
    _new_values: dict[str, tuple[Any, ...]]
    _label_refs: dict[str, RefsByKind]
    _id_meta: dict[int, RefMeta]
    _latest_id: int
    _return_val_stack: list[Any]
    _lock: threading.Lock

    def __init__(
        self,
        label: LabelArg | None = None,
        /,
        new_values: Any = _NO_VALUE,
        *,
        label_values: Mapping[str, Any] | None = None,
        debug: DebugArg = False,
    ) -> None:
        """Initialize a Triggon instance.

        Args:
            label (str | None):
                A single label name to register. Labels must not start with `*`.
            new_values (Any):
                The value associated with `label`. If omitted, `None` is used.
                Non-string sequences are normalized into indexed values.
                Wrap a sequence in another sequence to treat it as a single value.
            label_values (Mapping[str, Any] | None):
                A mapping from label names to values used to register one or more labels.
            debug (bool | str | Sequence[str], optional):
                Controls debug logging. If False, environment variables are not
                used. If True, detailed settings can be configured with
                environment variables. Target labels can be specified either by
                this argument or by environment variables.

        Raises:
            InvalidArgumentError:
                If no labels are provided, or if `label_values` is combined
                with `label` or `new_values`, or if any label starts with `*`.
        """

        if label_values is None:
            if label is None:
                raise InvalidArgumentError("no labels specified")
            check_str_sequence(arg_name="label", args=label, allow_multi=False)

            labels = label
            if new_values is _NO_VALUE:
                new_values = (None,)
            else:
                new_values = (new_values,)
        else:
            if label is not None or new_values is not _NO_VALUE:
                raise InvalidArgumentError(
                    "cannot specify 'label' or 'new_values' when 'label_values' is provided"
                )
            check_items(arg_name="label_values", arg=label_values)

            labels = label_values.keys()
            new_values = label_values.values()

        check_debug(debug)

        labels, _ = self.resolve_labels_and_idxs(
            labels,
            idxs=None,
            allow_symbol=False,
            is_init=True,
        )

        self._new_values = {}
        self._label_is_active = {}
        self._label_delay_state = {}
        self._label_is_perm_disabled = {}
        self._label_refs = {}
        self._id_meta = {}
        self._latest_id = 1
        self._return_val_stack = []
        self._lock = threading.Lock()

        self._normalize_label_values(labels, new_values)
        self.configure_debug(debug)

    def _normalize_label_values(
        self,
        labels: tuple[str, ...],
        values: tuple[Any, ...] | ValuesView[Any],
        add: bool = False,
    ) -> None:
        if add and self.debug[LOG_VERBOSITY] == 3:
            debug_on = True
            frame = get_target_frame(depth=2)
            callsite = get_callsite(frame)
        else:
            debug_on = False

        label_values = {}

        for label, val in zip(labels, values):
            if label in self._new_values:
                continue

            self._add_new_labels(label)
            if debug_on:
                self.log_added_label(label, callsite)

            if isinstance(val, Sequence) and not isinstance(val, (str, bytes, bytearray)):
                if len(val) >= 1:
                    label_values[label] = tuple(val)
                    continue

            label_values[label] = (val,)

        self._new_values.update(label_values)

    def _add_new_labels(self, label: str) -> None:
        self._label_is_active[label] = False
        self._label_is_perm_disabled[label] = False
        self._label_delay_state[label] = {
            TRIGGER: DelayState(),
            REVERT: DelayState(),
        }
        self._label_refs[label] = {GLOB_VAR: [], ATTR: []}

    @classmethod
    def from_label(
        cls,
        label: str,
        /,
        new_values: Any,
        *,
        debug: DebugArg = False,
    ) -> Self:
        """Create an instance from a single label.

        Args:
            label (str):
                The label name to register. Labels must not start with `*`.
            new_values (Any):
                The value associated with `label`. Non-string sequences are
                treated as indexed values. Wrap a sequence in another sequence to
                treat it as a single value.
            debug (bool | str | Sequence[str], optional):
                Controls debug logging. If False, environment variables are not
                used. If True, detailed settings can be configured with
                environment variables. Target labels can be specified either by
                this argument or by environment variables.

        Returns:
            Self: A new `Triggon` instance.

        Raises:
            InvalidArgumentError:
                If `label` is invalid, including when it starts with `*`.
        """

        return cls(label, new_values, debug=debug)

    @classmethod
    def from_labels(
        cls,
        label_values: Mapping[str, Any],
        /,
        *,
        debug: DebugArg = False,
    ) -> Self:
        """Create an instance from one or more labels.

        Args:
            label_values (Mapping[str, Any]):
                A mapping from label names to their associated values. If a
                value is a non-string sequence, each element becomes an indexed
                value for that label. Wrap a sequence in another sequence to
                treat it as a single value. Mapping keys must not start with `*`.
            debug (bool | str | Sequence[str], optional):
                Controls debug logging. If False, environment variables are not
                used. If True, detailed settings can be configured with
                environment variables. Target labels can be specified either by
                this argument or by environment variables.

        Returns:
            Self: A new `Triggon` instance.

        Raises:
            InvalidArgumentError:
                If `label_values` is invalid, including when any label starts with `*`.
        """

        return cls(label_values=label_values, debug=debug)

    def add_label(self, label: str, /, new_values: Any = None) -> None:
        """Register one additional label.

        If `label` is already registered, this method does nothing and keeps
        the existing values and state for that label.

        Args:
            label (str):
                The label name to add. Labels must not start with `*`.
            new_values (Any, optional):
                The value associated with `label`. If omitted, `None` is used.
                Non-string sequences are treated as indexed values.
                Wrap a sequence in another sequence to treat it as a single value.

        Raises:
            InvalidArgumentError:
                If `label` is invalid, including when it starts with `*`.
        """

        check_str_sequence(arg_name="label", args=label, allow_multi=False)
        self._register_labels(label, (new_values,))

    def add_labels(self, label_values: Mapping[str, Any], /) -> None:
        """Register additional labels from a mapping.

        Labels that are already registered are ignored and keep their existing
        values and state.

        Args:
            label_values (Mapping[str, Any]):
                A mapping from label names to their associated values. If a
                value is a non-string sequence, each element becomes an indexed
                value for that label. Wrap a sequence in another sequence to
                treat it as a single value. Mapping keys must not start with `*`.

        Raises:
            InvalidArgumentError:
                If `label_values` is empty or includes an invalid label,
                including when any label starts with `*`.
        """

        check_items(arg_name="label_values", arg=label_values)
        self._register_labels(label_values.keys(), label_values.values())

    def _register_labels(
        self,
        labels: str | KeysView[str],
        values: Any,
    ) -> None:
        labels_tup, _ = self.resolve_labels_and_idxs(
            labels, idxs=None, allow_symbol=False, is_init=True
        )
        self._normalize_label_values(labels_tup, values, add=True)

    def set_trigger(
        self,
        labels: LabelArg | None = None,
        /,
        *,
        indices: IndexArg | None = None,
        all: bool = False,
        cond: str = "",
        after: int | float = 0,
        reschedule: bool = False,
    ) -> None:
        """Activate labels.

        If an applied value is deferred by `TrigFunc`, it is executed
        during the update, and its result is used.

        Args:
            labels (str | Sequence[str], optional):
                The labels to activate. Ignored when `all` is True. If a label starts
                with `*`, the number of leading `*` characters is treated as its index.
            indices (int | Sequence[int], optional):
                The indices of the values to use for each label. Each index
                selects which indexed value of the corresponding label is used.
                When provided, the number of indices must match the number of
                labels. These explicit values take precedence over any `*`
                prefix in `labels`.
            all (bool, optional):
                If True, activate all registered labels.
            cond (str, optional):
                An expression that is evaluated at call time. The labels are
                activated only if it evaluates to True.
            after (int | float, optional):
                Delay in seconds before the labels become active. Even when a
                smaller value is given, the actual delay is about 0.011
                seconds or longer.
            reschedule (bool, optional):
                If True, replace any existing scheduled trigger for the same
                labels.

        Raises:
            InvalidArgumentError:
                If no labels are specified when `all` is False, or if any
                argument is invalid, or if `cond` uses an unsupported
                expression.
            IndexError:
                If any resolved index is out of range for its label.
            NameError:
                If `cond` refers to a name that does not exist.
            AttributeError:
                If `cond` accesses an attribute that does not exist.
            UnregisteredLabelError:
                If any given label is not registered.
        """

        if not all:
            if labels is None:
                raise InvalidArgumentError("no labels specified")

            check_str_sequence(arg_name="labels", args=labels)
            labels_iter = labels
        else:
            labels_iter = self._new_values.keys()

        check_idxs(indices)
        check_bool(arg_name="all", arg=all)
        check_cond(cond)
        check_after(after)
        check_bool(arg_name="reschedule", arg=reschedule)

        labels, indices = self.resolve_labels_and_idxs(labels_iter, indices)

        label_to_idx = to_dict(labels, indices)
        self.set_label_flags(label_to_idx, cond, after, reschedule, set_true=True)

    def is_triggered(self, *labels: LabelArg, match_all: bool = True) -> bool:
        """Return whether labels are active.

        Args:
            labels (str | Sequence[str]):
                One or more labels to check. Labels must not start with `*`.
            match_all (bool, optional):
                If True, return True only when all given labels are active.
                If False, return True when any given label is active.

        Returns:
            bool: Whether the requested labels are active.

        Raises:
            InvalidArgumentError:
                If no labels are specified, if `match_all` is invalid, or if
                any label starts with `*`.
            UnregisteredLabelError:
                If any given label is not registered.
        """

        unwrapped_labels = unwrap_value(labels)
        check_str_sequence(arg_name="labels", args=unwrapped_labels)
        check_bool(arg_name="match_all", arg=match_all)

        labels, _ = self.resolve_labels_and_idxs(unwrapped_labels, idxs=None, allow_symbol=False)

        if match_all:
            return all(self._label_is_active[label] for label in labels)
        return any(self._label_is_active[label] for label in labels)

    def switch_lit(
        self,
        labels: LabelArg,
        /,
        original_val: Any,
        *,
        indices: IndexArg | None = None,
    ) -> Any:
        """Return the active label value or the original value.

        If an applied value is deferred by `TrigFunc`, it is executed
        and its result is returned.

        Args:
            labels (str | Sequence[str]):
                Labels used to select the replacement value. If multiple labels
                are active, the first active label after normalization is used.
                If a label starts with `*`, the number of leading `*`
                characters is treated as its index.
            original_val (Any):
                The value to return when none of the labels is active.
            indices (int | Sequence[int], optional):
                The indices of the values to use for each label. Each index
                selects which indexed value of the corresponding label is used.
                When provided, the number of indices must match the number of
                labels. These explicit values take precedence over any `*`
                prefix in `labels`.

        Returns:
            Any: The switched value if a label is active, otherwise
            `original_val`.

        Raises:
            InvalidArgumentError:
                If `labels` or `indices` are invalid.
            IndexError:
                If any resolved index is out of range for its label.
            UnregisteredLabelError:
                If any given label is not registered.
        """

        check_str_sequence(arg_name="labels", args=labels)
        check_idxs(indices)

        labels, indices = self.resolve_labels_and_idxs(labels, indices)

        target_label = None
        idx = None
        # Find the first active label with the lowest index
        for i, label in zip(indices, labels):
            if self._label_is_active[label]:
                target_label = label
                idx = i
                break

        debug_on = self.debug[LOG_VERBOSITY] >= 2

        if target_label is None:
            if debug_on:
                self.store_debug_state(original_val)
            return original_val

        assert idx is not None
        new_value = self._new_values[target_label][idx]

        if hasattr(new_value, TRIGFUNC_ATTR):
            new_value = new_value._run()
        if debug_on:
            self.store_debug_state(original_val, new_value, target_label, idx)

        return new_value

    def register_ref(
        self,
        label: str,
        /,
        name: str,
        *,
        index: int | None = None,
    ) -> None:
        """Register a variable or attribute for a label.

        If the label is already active when the target is registered, the
        target is updated immediately. If the applied value is deferred by
        `TrigFunc`, it is executed and its result is used.

        Args:
            label (str):
                The label to associate with the variable or attribute. If the
                label starts with `*`, the number of leading `*` characters is
                treated as its index.
            name (str):
                The target name to register. This may be a variable name or an
                attribute path.
            index (int | None, optional):
                The index of the value to use from the given label. This
                selects which indexed value is applied if the target is
                registered while the label is already active.

        Raises:
            InvalidArgumentError:
                If `name` starts from a local variable, if the attribute path is
                invalid, or if `index` is invalid.
            IndexError:
                If the resolved index is out of range for the label.
            NameError:
                If the root name in `name` does not exist.
            UnregisteredLabelError:
                If any given label is not registered.
        """

        check_str_sequence(arg_name="label", args=label, allow_multi=False)
        check_str_sequence(arg_name="name", args=name, allow_multi=False)
        check_idxs(index)

        label_tup, index_tup = self.resolve_labels_and_idxs(label, index)

        label_to_refs = {label_tup[0]: {name: index_tup[0]}}
        self.register_target_refs(label_to_refs)

    def register_refs(self, label_to_refs: LabelToRefs, /) -> None:
        """Register multiple variables or attributes at once.

        If a label is already active when a target is registered, the target is
        updated immediately. If the applied value is deferred by `TrigFunc`,
        it is executed and its result is used.

        Args:
            label_to_refs (Mapping[str, Mapping[str, int]]):
                A mapping from labels to target names and the index of the
                value to use if the label is already active when the target is
                registered. Each target name may be a variable name or an
                attribute path. Labels must not start with `*`.

        Raises:
            InvalidArgumentError:
                If `label_to_refs` is empty, has an invalid structure, contains an invalid
                index, or contains a label that starts with `*`.
            IndexError:
                If any registered index is out of range for its label.
            NameError:
                If the root name of a target does not exist.
            UnregisteredLabelError:
                If any given label is not registered.
        """

        check_items(arg_name="label_to_refs", arg=label_to_refs)

        for label, refs in label_to_refs.items():
            self.resolve_labels_and_idxs(label, idxs=None, allow_symbol=False)
            for i in refs.values():
                self.validate_idx_range(label, i)

        self.register_target_refs(label_to_refs)

    def is_registered(
        self,
        *names: NameArg,
        label: str | None = None,
        match_all: bool = True,
    ) -> bool:
        """Return whether variable or attribute names are registered.

        Registration is checked by target name within the current file and
        callsite scope, not by the current value or object state of the
        target.

        Args:
            names (str | Sequence[str]):
                One or more target names to check.
            label (str | None, optional):
                Restrict the lookup to references registered for a specific
                label. Labels must not start with `*`.
            match_all (bool, optional):
                If True, return True only when all given names are registered.
                If False, return True when any given name is registered.

        Returns:
            bool: Whether the requested names are registered.

        Raises:
            InvalidArgumentError:
                If no names are specified, if an argument is invalid, or if
                `label` starts with `*`.
            UnregisteredLabelError:
                If `label` is given but is not registered.
        """

        unwrapped_names = unwrap_value(names)
        if isinstance(unwrapped_names, str):
            unwrapped_names = (unwrapped_names,)
        check_str_sequence(arg_name="names", args=unwrapped_names)

        if label is not None:
            check_str_sequence(arg_name="label", args=label, allow_multi=False)
            self.resolve_labels_and_idxs(label, idxs=None, allow_symbol=False)
        check_bool(arg_name="match_all", arg=match_all)

        frame = get_target_frame()
        callsite = get_callsite(frame)

        target_ids = self.get_ids_by_file(callsite.file)
        target_var_refs, target_attr_refs = self.get_refs(label)

        if match_all:
            for name in unwrapped_names:
                registered = self.is_registered_name(
                    name,
                    target_ids,
                    target_var_refs,
                    target_attr_refs,
                    callsite.scope_name,
                )
                if not registered:
                    return False
            return True

        # match_all=False
        for name in unwrapped_names:
            registered = self.is_registered_name(
                name,
                target_ids,
                target_var_refs,
                target_attr_refs,
                callsite.scope_name,
            )
            if registered:
                return True
        return False

    def unregister_refs(self, names: NameArg, /, *, labels: LabelArg | None = None) -> None:
        """Unregister variable or attribute names from labels.

        When `labels` is omitted, the given names are removed from all
        registered labels. Each name may be a variable name or an attribute
        path. Removal is based on the registered target name within the
        current file and callsite scope, not on the current value or object
        state.

        Args:
            names (str | Sequence[str]):
                One or more target names to unregister.
            labels (str | Sequence[str] | None, optional):
                Labels from which to remove the given names. If omitted, all
                registered labels are targeted. Labels must not start with `*`.

        Raises:
            InvalidArgumentError:
                If `names` or `labels` is invalid, or if any given label starts
                with `*`.
            UnregisteredLabelError:
                If any given label is not registered.
        """

        check_str_sequence(arg_name="names", args=names)

        if labels is not None:
            check_str_sequence(arg_name="labels", args=labels)
            labels, _ = self.resolve_labels_and_idxs(labels, idxs=None, allow_symbol=False)
        else:
            labels = tuple(self._label_refs.keys())

        if isinstance(names, str):
            names = (names,)

        frame = get_target_frame()
        callsite = get_callsite(frame)
        target_ids = self.get_ids_by_file(callsite.file)

        for label in labels:
            with self._lock:
                self.unregister_target_refs(label, names, target_ids, callsite)

    def revert(
        self,
        labels: LabelArg | None = None,
        /,
        *,
        all: bool = False,
        disable: bool = False,
        cond: str = "",
        after: int | float = 0,
        reschedule: bool = False,
    ) -> None:
        """Deactivate labels.

        Args:
            labels (str | Sequence[str] | None):
                The labels to deactivate. Ignored when `all` is True.
                Labels must not start with `*`.
            all (bool, optional):
                If True, deactivate all registered labels.
            disable (bool, optional):
                If True, permanently disable the target labels so later
                `set_trigger()` calls do not activate them.
            cond (str, optional):
                An expression that is evaluated at call time. The labels are
                deactivated only if it evaluates to True.
            after (int | float, optional):
                Delay in seconds before the labels are deactivated. Even when a
                smaller value is given, the actual delay is about 0.011
                seconds or longer.
            reschedule (bool, optional):
                If True, replace any existing scheduled revert for the same
                labels.

        Raises:
            InvalidArgumentError:
                If no labels are specified when `all` is False, or if any
                argument is invalid, or if `cond` uses an unsupported
                expression.
            NameError:
                If `cond` refers to a name that does not exist.
            AttributeError:
                If `cond` accesses an attribute that does not exist.
            UnregisteredLabelError:
                If any given label is not registered.
        """

        if not all:
            if labels is None:
                raise InvalidArgumentError("no labels specified")

            check_str_sequence(arg_name="labels", args=labels)
            labels_iter, _ = self.resolve_labels_and_idxs(labels, idxs=None, allow_symbol=False)
        else:
            labels_iter = self._new_values.keys()

        check_bool(arg_name="all", arg=all)
        check_bool(arg_name="disable", arg=disable)
        check_cond(cond)
        check_after(after)
        check_bool(arg_name="reschedule", arg=reschedule)

        label_to_idx = to_dict(labels_iter, values=None)
        self.set_label_flags(
            label_to_idx,
            cond,
            after,
            reschedule,
            set_true=False,
            disable=disable,
        )

    @staticmethod
    @contextmanager
    def rollback(targets: NameArg | None = None) -> Iterator[None]:
        """Temporarily mutate names and restore their original values on exit.

        The original values are restored when leaving the context, even if an
        exception is raised inside it.

        Args:
            targets (str | Sequence[str] | None):
                Names to restore when leaving the context. Each name may be a
                variable name or an attribute path such as `obj.value`. If
                omitted, assignment targets inside the `with` block are
                collected automatically. Undefined names and unsupported
                targets are ignored.

        Raises:
            RollbackNotSupportedError:
                If the current runtime is earlier than CPython 3.13.
            InvalidArgumentError:
                If `targets` is empty.
            AttributeError:
                If a given attribute path cannot be resolved.
            UpdateError:
                If a target cannot be restored when exiting the context.
        """

        if sys.version_info < (3, 13):
            raise RollbackNotSupportedError()

        if targets is not None:
            check_str_sequence(arg_name="targets", args=targets)
            if isinstance(targets, str):
                targets = (targets,)

        # Add 1 to depth to account for @contextmanager
        frame = get_target_frame(depth=2)
        name_to_refs = collect_rollback_refs(frame, targets)

        try:
            yield
        finally:
            revert_targets(frame, name_to_refs)

    @contextmanager
    def capture_return(self) -> Iterator[EarlyReturnResult]:
        """Capture an early return triggered by `trigger_return()`.

        `trigger_return()` is active only inside this context. If it is
        triggered, the yielded result object is updated with `triggered=True`
        and the captured value. If the captured value is deferred by
        `TrigFunc`, it is executed and its result is stored.

        Yields:
            EarlyReturnResult: The result object for the captured return.
        """

        # Initialize the default return value to None
        self._return_val_stack.append(None)
        result = EarlyReturnResult()

        try:
            yield result
        except _EarlyReturn:
            result.triggered = True

            value = self._return_val_stack[-1]
            if value is not None and hasattr(value, TRIGFUNC_ATTR):
                result.value = value._run()
            else:
                result.value = value
        finally:
            self._return_val_stack.pop()

    def trigger_return(
        self,
        labels: LabelArg,
        /,
        *,
        value: Any = None,
    ) -> None:
        """Trigger an early return when one of the labels is active.

        This method is available only inside `capture_return()`. If no given
        label is active, nothing happens and `None` is returned.

        Args:
            labels (str | Sequence[str]):
                Labels to check for the early return. Labels must not start
                with `*`.
            value (Any, optional):
                The value to capture when an active label is found.
                If the captured value is deferred by `TrigFunc`, it is
                executed by `capture_return()`.

        Raises:
            InactiveCaptureError:
                If `capture_return()` is not active.
            InvalidArgumentError:
                If `labels` is invalid, or if any label starts
                with `*`.
            UnregisteredLabelError:
                If any given label is not registered.
        """

        if not self._return_val_stack:
            raise InactiveCaptureError()

        check_str_sequence("labels", labels)

        labels, _ = self.resolve_labels_and_idxs(labels, idxs=None, allow_symbol=False)

        target_label = None

        for label in labels:
            if self._label_is_active[label]:
                target_label = label
                break

        if target_label is None:
            return

        self._return_val_stack[-1] = value

        if self.debug[LOG_VERBOSITY] != 0:
            frame = get_target_frame()
            callsite = get_callsite(frame)
            self.log_early_return(target_label, value, callsite)

        raise _EarlyReturn

    def trigger_call(
        self,
        labels: LabelArg,
        /,
        target: TrigFunc,
    ) -> Any:
        """Run a target deferred by `TrigFunc` when one of the labels is active.

        Args:
            labels (str | Sequence[str]):
                Labels to check before running `target`. Labels must not start
                with `*`.
            target (TrigFunc):
                A target deferred by `TrigFunc` to run.

        Returns:
            Any | None:
                The result of `target._run()` if any of the given labels is active;
                otherwise, `None`.

        Raises:
            TypeError:
                If `target` is not deferred by `TrigFunc`, or if it does not
                satisfy the call requirements for this method.
            InvalidArgumentError:
                If `labels` is invalid or any label starts with `*`.
            UnregisteredLabelError:
                If any given label is not registered.
        """

        if not hasattr(target, TRIGFUNC_ATTR):
            raise TypeError("target must be deferred by TrigFunc")

        check_str_sequence(arg_name="labels", args=labels)
        labels, _ = self.resolve_labels_and_idxs(labels, idxs=None, allow_symbol=False)

        target_label = None
        for label in labels:
            if self._label_is_active[label]:
                target_label = label
                break
        if target_label is None:
            return

        if self.debug[LOG_VERBOSITY] != 0:
            assert target._trigcall is not None
            target_name = target._trigcall.name
            frame = get_target_frame()
            callsite = get_callsite(frame)

            self.log_trigger_call(target_label, target_name, callsite)

        return target._run()
