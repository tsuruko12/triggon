# triggon

[![PyPI](https://img.shields.io/pypi/v/triggon)](https://pypi.org/project/triggon/)
![Python](https://img.shields.io/pypi/pyversions/triggon)
![Python](https://img.shields.io/pypi/l/triggon)
![Package Size](https://img.shields.io/badge/size-37.1kB-lightgrey)
[![Downloads](https://pepy.tech/badge/triggon)](https://pepy.tech/project/triggon)

## Overview

Triggon is a Python library for reducing repetitive conditional logic and boilerplate around temporary state changes. It lets you switch values by label, run deferred calls, restore temporary updates, and exit early with a custom return value. The goal is to make branching logic easier to write, reuse, and manage from one place.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
  - [Triggon](#triggon)
  - [TrigFunc](#trigfunc)
  - [Debug Logging](#debug-logging)
  - [Errors](#errors)
- [License](#license)
- [Author](#author)

## Features

- Switch multiple values and update registered variables or attributes at once, without writing `if` statements
- Execute deferred functions and methods through `TrigFunc`
- Exit early with a custom return value inside a context manager
- Schedule trigger and revert operations with conditions or delays
- Roll back temporary changes with a context manager

## Installation

```bash
pip install triggon
```

## Quick Start

```python
from triggon import Triggon

tg = Triggon.from_labels(
    {
        "prod": "https://api.example.com",
        "dev": "http://localhost:8000",
    }
)


def get_base_url() -> str:
    return tg.switch_lit(("prod", "dev"), original_val="http://127.0.0.1:5000")


print(get_base_url())
# http://127.0.0.1:5000

tg.set_trigger("dev")
print(get_base_url())
# http://localhost:8000
```

## API Reference

### Triggon

Use one of the recommended constructors:

```python
Triggon.from_label(label, /, new_values, *, debug=False) -> Triggon
Triggon.from_labels(label_values, /, *, debug=False) -> Triggon
```

`from_label()` registers a single label and its values.\
`from_labels()` registers labels from a mapping, including multiple labels at once.

Direct construction via `Triggon(...)` is also supported if needed.

Notes:

- A non-string sequence provided as a label value is unpacked into indexed values for that label
- To treat a non-string sequence as a single value, wrap it in an outer sequence
- In methods such as `set_trigger()`, `revert()`, `switch_lit()`, and `register_ref()`, `*` can be used as an index shorthand: `*A` means label `A` at index `1`, and `**A` means index `2`
- `debug` accepts `False`, `True`, a single label name, or a sequence of label names

```python
from triggon import Triggon

tg = Triggon.from_label("A", new_values=[1, 2, 3]) # one label with multiple indexed values

tg = Triggon.from_labels(
    {
        "A": 10,
        "B": 20,
    }
)
```

#### `add_label()` and `add_labels()`

`add_label()` adds a single label and its values.

`add_labels()` adds one or more labels and their values from a mapping.

```python
add_label(label, /, new_values=None) -> None
add_labels(label_values, /) -> None
```

If a label is already registered, it is ignored.

#### `set_trigger()`

Activate one or more labels and update the values of variables or attributes registered with `register_ref` or `register_refs`.

```python
set_trigger(
    labels=None,
    /,
    *,
    indices=None,
    all=False,
    cond="",
    after=0,
    reschedule=False,
) -> None
```

`labels` accepts a single label or a sequence of labels.

`indices` accepts a single index or a sequence of indices.

If the update value applied when a label is triggered is deferred by `TrigFunc`, it is executed automatically and its result is used instead.

For `*`-prefixed labels, the number of `*` symbols determines the index, but explicit `indices` take precedence.

Keyword arguments:

- `indices`: explicit indices specifying which value to use for each label
- `all`: activate all registered labels
- `cond`: only activate the labels if the condition evaluates to true
- `after`: delay label activation in seconds
- `reschedule`: replace an existing scheduled activation for the same labels

```python
from triggon import Triggon

tg = Triggon.from_labels({"A": 10, "B": 20})

tg.set_trigger(all=True)

print(tg.switch_lit("A", original_val=1))
# 10
print(tg.switch_lit("B", original_val=2))
# 20
```

```python
from time import sleep

x = 0

tg = Triggon.from_label("A", new_values=50)
tg.register_ref("A", name="x")

tg.set_trigger("A", after=0.5)

print(x)
# 0
sleep(0.6)
print(x)
# 50
```

#### `is_triggered()`

Check whether one or more labels are currently active.

```python
is_triggered(*labels, match_all=True) -> bool
```

`labels` accepts either multiple positional labels or a single sequence of labels.

If `match_all` is `True`, this method returns `True` only if all given labels are active. If `False`, it returns `True` if any given label is active.

```python
tg = Triggon.from_labels({"A": 1, "B": 2})
tg.set_trigger("B")

print(tg.is_triggered("A"))
# False
print(tg.is_triggered("A", "B", match_all=False))
# True
```

#### `switch_lit()`

Return the value registered for the selected label, or `original_val` if none of the given labels are active.

```python
switch_lit(labels, /, original_val, *, indices=None) -> Any
```

`labels` accepts a single label or a sequence of labels.

`indices` accepts a single index or a sequence of indices.

If more than one label is active, the first active label in the sequence is used.\
If the value selected for that label is deferred by `TrigFunc`, it is executed automatically and its result is returned.

Use `indices` to explicitly specify which value to use for each label.\
For `*`-prefixed labels, the number of `*` symbols determines the index, but explicit `indices` take precedence.

```python
tg = Triggon.from_labels({"A": "dev", "B": "prod"})

tg.set_trigger(all=True)

print(tg.switch_lit(("B", "A"), original_val="local"))
# prod
print(tg.switch_lit(("A", "B"), original_val="local"))
# dev
```

#### `register_ref()` and `register_refs()`

Register global variables or attribute paths so `set_trigger()` can update them automatically when their labels become active.
If a label is already active, registration updates the target immediately.

```python
register_ref(label, /, name, *, index=None) -> None
register_refs(label_to_refs, /) -> None
```

Notes:

- Local variables themselves cannot be registered
- Attribute roots may come from the current local scope or the global scope
- If the value applied to the target is deferred by `TrigFunc`, it is executed during the update
- Matching is based on the current file and the scope where you call the method

In `register_ref()`, use `index` to specify which indexed value to apply if the label is already active when the target is registered.\
If the label is prefixed with `*`, the number of `*` symbols determines the index, but an explicit `index` takes precedence.

```python
from triggon import Triggon

tg = Triggon.from_labels({"enabled": True, "name": "prod"})

flag = False


class Config:
    value = "local"


tg.set_trigger("enabled")
tg.register_ref("enabled", name="flag") # updates immediately because "enabled" is already active
tg.register_ref("name", name="Config.value")

print(flag)
# True

tg.set_trigger("name")
print(Config.value)
# prod
```

Use `register_refs()` to register multiple targets at once.\
The mapping uses the form `{label: {target_name: index}}`.

```python
tg.register_refs(
    {
        "enabled": {"flag": 0},
        "name": {"Config.value": 0},
    }
)
```

#### `is_registered()`

Check whether target names are registered in the current file and callsite scope.

```python
is_registered(*names, label=None, match_all=True) -> bool
```

`names` accepts either multiple positional target names or a single sequence of target names.

This checks registered names only, not the current value or object state of the target.

Keyword arguments:

- `label`: limit the check to names registered under a specific label
- `match_all`: return `True` only if all given names are registered. Use `False` to check whether any given name is registered.

```python
from triggon import Triggon

tg = Triggon.from_label("A", None)

a = 0
b = 0
tg.register_ref("A", name="a")

print(tg.is_registered("a", "b"))
# False
print(tg.is_registered("a", "b", match_all=False))
# True
```

#### `unregister_refs()`

Remove one or more registered names from the selected labels.

```python
unregister_refs(names, /, *, labels=None) -> None
```

`names` accepts a single registered name or a sequence of them.

`labels` accepts a single label or a sequence of labels.

If `labels` is given, the specified names are removed only from those labels.\
Otherwise, they are removed from all labels they are registered under.

#### `revert()`

Deactivate labels and restore registered targets to their original values.

```python
revert(
    labels=None,
    /,
    *,
    all=False,
    disable=False,
    cond="",
    after=0,
    reschedule=False,
) -> None
```

`labels` accepts a single label or a sequence of labels.

Keyword arguments:

- `all`: deactivate all registered labels
- `disable`: keep the specified labels disabled
- `cond`: only deactivate the labels if the condition evaluates to true
- `after`: delay label deactivation in seconds
- `reschedule`: replace an existing scheduled deactivation for the same labels

```python
from triggon import Triggon

tg = Triggon.from_label("status", new_values="active")

tg.set_trigger("status")
print(tg.switch_lit("status", original_val="inactive"))
# active

tg.revert("status")
print(tg.switch_lit("status", original_val="inactive"))
# inactive
```

```python
tg = Triggon.from_label("status", new_values="active")


def get_status():
    tg.set_trigger("status")
    return tg.switch_lit("status", "inactive")


print(get_status())
# "active"

tg.revert("status", disable=True)
print(get_status())
# inactive
```

#### `capture_return()` and `trigger_return()`

Returns early within a scoped context when specified labels are active.

```python
capture_return() -> ContextManager[EarlyReturnResult]
trigger_return(labels, /, *, value=None) -> None
```

`labels` accepts a single label or a sequence of labels.

Use `capture_return()` as a context manager, and call `trigger_return()` inside it when you want to exit early.

Available fields in `EarlyReturnResult`:

- `triggered`: whether `trigger_return()` was triggered
- `value`: the captured return value

For `trigger_return()`, use `value` to specify the return value.

Notes:

- `trigger_return()` works only inside `capture_return()`
- Deferred `TrigFunc` values are executed by `capture_return()` before the result is stored

```python
from triggon import Triggon

tg = Triggon.from_label("stop", new_values=True)


def task():
    print("start")
    tg.trigger_return("stop", value="stopped")
    print("end")


def main():
    with tg.capture_return() as result:
        task()
        print("after task")
    return result


result = main()
# start
# end
# after task
print(result.triggered)
# False
print(result.value)
# None

tg.set_trigger("stop")

result = main()
# start
print(result.triggered)
# True
print(result.value)
# stopped
```

#### `trigger_call()`

Execute a deferred `TrigFunc` target when any of the given labels is active.

```python
trigger_call(labels, /, target) -> Any
```

`labels` accepts a single label or a sequence of labels.

`target` must be a deferred `TrigFunc` call chain ending in a call.

```python
from triggon import TrigFunc, Triggon

tg = Triggon.from_label("debug", new_values=True)
f = TrigFunc()


def show_debug():
    print("debug mode")


tg.trigger_call("debug", target=f.show_debug())
# no output

tg.set_trigger("debug")
tg.trigger_call("debug", target=f.show_debug())
# debug mode
```

#### `rollback()`

Temporarily change target values and restore them automatically when the context exits.

```python
rollback(targets=None) -> ContextManager[None]
```

Notes:

- Requires CPython 3.13 or later
- You can pass explicit target names such as `"x"` or `"obj.value"`
- If `targets` is omitted, targets assigned inside the block are collected automatically

```python
from triggon import Triggon

x = 1

with Triggon.rollback():
    x = 99
    print(x)
    # 99

print(x)
# 1
```

### TrigFunc

`TrigFunc` records deferred function or method calls without executing them immediately.\
The recorded chain can later be used by `switch_lit()`, `trigger_call()`, or `trigger_return()`.

```python
TrigFunc()
```

Typical uses:

- Store a deferred value in label data for `switch_lit()`
- Run a deferred call through `trigger_call()`
- Return a deferred value through `trigger_return()`

Deferred names are resolved from the captured local scope, global scope, and builtins when the chain is executed.\
A `TrigFunc` instance can also be reused across scopes.

```python
from triggon import TrigFunc, Triggon

def greet(name):
    return f"hello, {name}"


f = TrigFunc()
tg = Triggon.from_label("greet", new_values=f.greet("world"))

tg.set_trigger("greet")
print(tg.switch_lit("greet", original_val=None))
# hello, world
```

### Debug Logging

Enable debug output by passing `debug=` to `Triggon(...)`, `from_label()`, or `from_labels()`.

- `debug=False`: disable logging
- `debug=True`: use settings from the environment, defaulting to verbosity `3`
- `debug="A"` or `debug=("A", "B")`: restrict output to selected labels

Environment variables:

- `TRIGGON_LOG_VERBOSITY`
  - `0`: off
  - `1`: trigger, revert, early-return, and trigger-call events
  - `2`: also log value updates
  - `3`: also log delayed actions and register/unregister events
- `TRIGGON_LOG_FILE`: write logs to a file instead of stderr
- `TRIGGON_LOG_LABELS`: comma-separated label filter used when `debug=True`

### Errors

- `InvalidArgumentError`: a public API received invalid arguments or an invalid argument combination
- `UnregisteredLabelError`: an operation refers to a label that has not been registered
- `InactiveCaptureError`: `trigger_return()` was called outside `capture_return()`
- `RollbackNotSupportedError`: `rollback()` was used on a runtime earlier than CPython 3.13
- `RollbackSourceError`: the caller's source file could not be found during `rollback()`
- `UpdateError`: a registered target could not be updated or restored

## License

This project is licensed under the MIT License.
See [LICENSE](./LICENSE) for details.

## Author

Created by Tsuruko
GitHub: [@tsuruko12](https://github.com/tsuruko12)
X: [@tool_tsuruko12](https://x.com/tool_tsuruko12)
