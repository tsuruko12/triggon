# triggon

[![PyPI](https://img.shields.io/pypi/v/triggon)](https://pypi.org/project/triggon/)
![Python](https://img.shields.io/pypi/pyversions/triggon)
![Python](https://img.shields.io/pypi/l/triggon)
![Package Size](https://img.shields.io/badge/size-31kB-lightgrey)
[![Downloads](https://pepy.tech/badge/triggon)](https://pepy.tech/project/triggon)

## Overview
This library dynamically switches values and functions at labeled trigger points.

> **Warning**  
> The next update will include breaking changes.  
> The `switch_var` API function and some argument names will be changed in the next update.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)
- [Author](#author)

## Features
- Switch multiple values and functions at once with a single trigger point
- Eliminates the need for `if` or `match` statements
- Switch both literal values and variables
- Trigger early returns with optional return values
- Call functions at any time
- Delay execution of almost any library and custom function

## Upcoming Features
- Add environment-variable-only debug configuration, including verbosity, file output, and target labels
- Split label and value registration into two class methods: one for a single label and one for multiple labels
- Support more flexible ways of passing functions and class methods to the deferred-execution class

## Installation
```bash
pip install triggon
```

## Usage
This section explains how to use each part of the API.

## API Reference
- [Triggon](#triggon)
  - [set_trigger](#set_trigger)
  - [is_triggered](#is_triggered)
  - [switch_lit](#switch_lit)
  - [switch_var](#switch_var)
  - [is_registered](#is_registered)
  - [revert](#revert)
  - [exit_point](#exit_point)
  - [trigger_return](#trigger_return)
  - [trigger_func](#trigger_func)
- [TrigFunc](#trigfunc)
- [Erorr](#error)
  - [InvalidArgumentError](#invalidargumenterror)
  - [InvalidClassVarError](#invalidclassvarerror)
  - [MissingLabelError](#missinglabelerror)

---

### Triggon
`self, label: str | dict[str, Any], /,`  
`new: Any = None,`  
`*, debug: bool | str | list[str] | tuple[str, ...] = False`  
`-> None`

`Triggon()` is initialized with label-value pairs.  
You can pass a single label with its value, or multiple labels using a dictionary.

If you pass multiple values to a label using a list,  
each value is correspond to index 0, 1, 2, and so on, in the order you provide.

```python
from triggon import Triggon

# Set index 0 to 100 and index 1 to 0 as their new values
tg = Triggon("num", new=[100, 0])

def example():
    x = tg.switch_lit("num", 0)    # index 0
    y = tg.switch_lit("*num", 100) # index 1

    print(f"{x} -> {y}")

example()
# Output: 0 -> 100

tg.set_trigger("num")

example()
# Output: 100 -> 0
```

When passing a list or tuple that should be used as a single value,  
make sure to wrap it in another list or tuple to avoid it being unpacked.

```python
tg = Triggon({
    "seq1": [(1, 2, 3)], # index 0 holds (1, 2, 3)  
    "seq2": [1, 2, 3],   # indexes 0, 1, and 2 hold 1, 2, and 3
})

def example():
    x = tg.switch_lit("seq1", 10) # index 0
    y = tg.switch_lit("seq2", 10) # index 0

    print(f"For 'seq1': {x}")
    print(f"For 'seq2': {y}")

tg.set_trigger(("seq1", "seq2"))

example()
# == Output ==
# For 'seq1': (1, 2, 3)
# For 'seq2': 1
```

A single index can have multiple values assigned to it.

```python
from dataclasses import dataclass

from triggon import Triggon

tg = Triggon("mode", new=True) # Set index 0 to True for label "mode"

@dataclass
class ModeFlags:
    mode_a: bool = False
    mode_b: bool = False
    mode_c: bool = False

    def set_mode(self, enable: bool):
        tg.set_trigger("mode", cond="enable")

        tg.switch_var("mode", [self.mode_a, self.mode_b, self.mode_c]) # All values share index 0

        print(
            f"mode_a is {self.mode_a}\n"
            f"mode_b is {self.mode_b}\n"
            f"mode_c is {self.mode_c}\n"
        )

s = ModeFlags()

s.set_mode(False)
# == Output ==
# mode_a is False
# mode_b is False
# mode_c is False

s.set_mode(True)
# == Output ==
# mode_a is True
# mode_b is True
# mode_c is True
```

If you want to trace labels in real time, set the `debug` flag to `True`.  
You can also control which labels are printed by passing either a single label as a string,  
or multiple labels as a list/tuple.

```python
Triggon({"A": 10, "B": 20}, debug=True)       # Prints both "A" and "B"

Triggon({"A": 10, "B": 20}, debug="A")        # Prints only label "A"

Triggon({"A": 10, "B": 20}, debug=("A", "B")) # Prints no labels
```

> ⚠️ **Note:** 
> Labels with the `*` prefix cannot be used during initialization 
> and will raise an `InvalidArgumentError`.

---

### set_trigger
`self, label: str | list[str] | tuple[str, ...], /,`  
`*,`  
`all: bool = False,`  
`index: int = None,`  
`cond: str = None,`  
`after: int | float = None`  
`-> None`

Activates the given labels for switching values.  
If the variables for the labels are already registered using `switch_var()`,  
switches the values in this function.

If `disable=True` was set in `revert()`, the labels are not activated.

#### ***all***
If `True`, activates all labels.

#### ***index***
Specifies the label index used to switch a variable's value.  
If not specified, the index given when calling `switch_var()` is used. 

This applies only to `switch_var()`, not to `switch_lit()`.

#### ***cond***
Sets a condition to activate the labels.

> **⚠️ Note:**
> This function uses `eval()` internally to process the given argument.  
> **Only comparison expressions or single boolean values are allowed**  
> (e.g., `x > 0 > y`, `value == 10`).  
> If the argument is a single literal or variable,  
> its value must be a bool; Otherwise, `InvalidArgumentError` is raised.  
> Function calls also raise this error.

#### ***after***
Sets the delay in seconds before labels become active.  
If specified again while a delay is active, the initial duration is kept.

> **⚠️ Note:**
> Execution actually occurs **about 0.011 seconds later** than the specified time.

```python
import random

from triggon import Triggon

tg = Triggon({
    "timeout": None, 
    "mark": ("〇", "✖"), 
    "add": (1, 0),
})

mark = None
point = None
correct = 0
tg.switch_var({"mark": mark, "add": point}) # Register the variables

print("How many can you get right in 10 seconds?")
tg.set_trigger("timeout", after=10) # Activate the label "time" after 10s

for _ in range(15):
    x = random.randint(1, 10)
    y = random.randint(1, 10)

    answer = int(input(f"{x} × {y} = ") or 0)
    tg.set_trigger(("mark", "add"), cond="answer == x*y")          # "mark" -> "〇", "add" -> 1
    tg.set_trigger(("mark", "add"), index=1, cond="answer != x*y") # "mark" -> "✖", "add" -> 0
    print(mark)

    correct += point

    if tg.is_triggered("timeout"): # Check if the label "timeout" is active
        print("Time's up!")
        print(f"You got {correct} correct!")
        break
```

```python
tg = Triggon("msg", new="Call me?")

def sample(print_msg: bool):
    # Activate "msg" if print_msg is True
    tg.set_trigger("msg", cond="print_msg")

    # Print the message if triggered
    print(tg.switch_lit("msg", ""))

sample(False) # Output: ""
sample(True)  # Output: Call me? 
```

---

### is_triggered
`self, label: str | list[str] | tuple[str, ...]`  
`-> bool | list[bool] | tuple[bool, ...]`

Returns `True` or `False` for each label, depending on whether it is active.  
The return type depends on the given arguments.

```python
from triggon import Triggon

tg = Triggon({"A": None, "B": None, "C": None, "D": None})

tg.set_trigger(("A", "D"))

print(tg.is_triggered("A"))                # Output: True
print(tg.is_triggered(["C", "D"]))         # Output: [False, True]
print(tg.is_triggered("A", "B", "C", "D")) # Output: (True, False, False, True)
```

---

### switch_lit
`self, label: str | list[str] | tuple[str, ...], /,`  
`org: Any,`  
`*, index: int = None`  
`-> Any`

Switches the value for the given label when it is active.  
If multiple labels are passed and more than one of them are active,  
the one with the lower index in the sequence takes priority.

**Direct variable references are not allowed.**

If the return value is a function delayed by the `TrigFunc` class,  
it is automatically executed and its result is returned.

When the `index` keyword argument is specified for multiple labels,  
it is applied to all labels.

```python
from triggon import Triggon, TrigFunc

F = TrigFunc() # Wrapper for delayed function execution
tg = Triggon("text", new=F.print("After")) 

def example():
    tg.switch_lit("text", org=F.print("Before"))

example() # Output: Before

tg.set_trigger("text")
example() # Output: After
```

You can also use the `*` character as a prefix to specify the index.  
For example, `"label"` refers to index 0, and `"*label"` refers to index 1.
`*` used elsewhere (not as a prefix) is ignored and has no special meaning.
If both the keyword and `*` are used, **the keyword takes priority.**  

> **Note:**   
> For better readability when working with multiple indices, 
> it's recommended to use the `index` keyword argument.

```python
# Set the value to "A" for index 0 and to "B" for index 1
tg = Triggon("char", new=("A", "B"))

def example():
    tg.set_trigger("char")

    print(tg.switch_lit("char", 0))           # index 0 (no '*' — defaults to index 0)
    print(tg.switch_lit("*char", 1))          # index 1 (using '*')
    print(tg.switch_lit("*char", 0, index=0)) # index 0 ('index' keyword takes priority over '*')
    print(tg.switch_lit("char", 1, index=1))  # index 1 (using 'index' keyword)

example()
# == Output ==
# A
# B
# A
# B
```

```python
tg = Triggon({"A": True, "B": False})

def sample():
    # Switch to the new value if any label is active.
    # If both are active, the earlier one takes priority.
    x = tg.switch_lit(["A", "B"], None)

    print(x)

sample()            # Output: None 

tg.set_trigger("A") # Output: True
sample()

tg.set_trigger("B") # Output: True
sample()
```

---

### switch_var
`self, label: str | dict[str, Any], var: Any = None, /,`  
`*, index: int = None`  
`-> Any`

Registers the given variables with the specified labels and indices.  
When the labels are active, their values are switched.  
If the variables are already registered, switching is handled by `set_trigger()`.

**Global variables and class attributes are supported, but local variables are not.**  
When class attributes are registered from the global scope,  
`InvalidClassVarError` is raised.

This function returns the value of the variable when a single label is passed.  
Otherwise, it returns `None`.  
If the return value is a function delayed by the `TrigFunc` class,  
it is automatically executed and its result is returned.

When the `index` keyword argument is specified with multiple labels,  
the same index is applied to all of them.  

You can also use the `*` character as a prefix to specify the index.  
For example, `"label"` refers to index 0, and `"*label"` refers to index 1.  
`*` used elsewhere (not as a prefix) is ignored and has no special meaning.  
If both the keyword and `*` are used, **the keyword takes priority.**  

When specifying different indices for multiple labels, use `*` instead.

```python
import random

from triggon import Triggon

tg = Triggon({
    "level_1": ["an uncommon", 80],
    "level_2": ["a rare", 100],
    "level_3": ["a legendary", 150],
})

level = None
attack = None

def spin_gacha():
    items = ["level_1", "level_2", "level_3"]
    result = random.choice(items)

    tg.set_trigger(result)

    tg.switch_var(result, level)
    tg.switch_var(result, attack, index=1)

    # Outputs vary randomly.
    # Example: result = 'level_2'
    print(f"You pulled {level} sword!") # Output: You pulled a rare sword!
    print(f"Attack Power: {attack}")    # Output: Attack Power: 100 

spin_gacha()
```

Also, you can assign multiple values to a single variable.

```python
import math

from triggon import Triggon, TrigFunc

F = TrigFunc()
tg = Triggon("var", new=["ABC", True, F.math.sqrt(100)])

x = None

tg.set_trigger("var")

value = tg.switch_var("var", x)
print(value) # Output: "ABC"

tg.set_trigger("var", index=1)
print(x)     # Output: True

# If the return value is a function delayed by `TrigFunc`,
# set_trigger() does not call it.
tg.set_trigger("var", index=2)
print(x) # Output: <function TrigFunc...>

# In that case, you need to call it manually
if tg.is_triggered("var"):
    print(x()) # Output: 10.0

# switch_var() calls it and returns the result
value = tg.switch_var("var", x, index=2)
print(value) # Output: 10.0
```

> **Notes:** 
> Values are typically updated when `set_trigger()` is called.  
> However, on the first call, 
> the value won't change unless the variable has been registered via `switch_var()`.  
> In that case, the value is changed by `switch_var()`.  
> Once registration is complete, each call to `set_trigger()` immediately updates the value.  
>
> In some environments (e.g., Jupyter or REPL),  
> calls to `switch_var()` may not be detected due to source code unavailability.
>
> This function only supports  
> literal values, variables, or simple attribute chains for labels and the `index` keyword.  
> Other types will raise `InvalidArgumentError`.

---

### is_registered
`self, *variable: str`  
`-> bool | list[bool] | tuple[bool, ...]`

Returns `True` or `False` for each variable, depending on whether it has been registered.  
The return type depends on the given arguments.

Raises `InvalidArgumentError` if the arguments are not variables.

```python
tg = Triggon("var", None)

@dataclass
class Sample:
    x: int = 0
    y: int = 0
    z: int = 0

    def func(self):
        tg.switch_var("var", [smp.x, smp.z])
        print(tg.is_registered(["self.y", "self.z"]))

smp = Sample()
smp.func() # Output: [False, True]

print(tg.is_registered("smp.x"))                # Output: True
print(tg.is_registered("Sample.x", "Sample.y")) # Output: [True, False]
```

---

### revert
`self, label: str | list[str] | tuple[str, ...] = None, /,`  
`*,`  
`all: bool = False,`  
`disable: bool = False,`  
`cond: str = None,`  
`after: int | float = None`  
`-> None`

Deactivates the given labels and restores their original values.

The state remains effective until the next call to `set_trigger()`.  
All values associated with the specified labels are reverted.

#### ***all***
If `True`, Deactivates all labels.

#### ***disable***
If `True`, permanently disables the labels.  

In this state, `set_trigger()` does not activate them.

```python
tg = Triggon("flag", new="Active")

def sample():
    tg.set_trigger("flag") # Activate "flag" on each call

    x = tg.switch_lit("flag", org="Inactive")
    print(x)

sample() # Output: Active

# The effect persists until the next call to set_trigger()
tg.revert("flag")
sample() # Output: Active

# Permanently disable "flag"
tg.revert("flag", disable=True)
sample() # Output: Inactive
```

#### ***cond***
Sets a condition to dactivate the labels.

> **⚠️ Note:**
> This function uses `eval()` internally to process the given argument.  
> **Only comparison expressions or single boolean values are allowed**  
> (e.g., `x > 0 > y`, `value == 10`).  
> If the argument is a single literal or variable,  
> its value must be a bool; Otherwise, `InvalidArgumentError` is raised.  
> Function calls also raise this error.

#### ***after***
Sets the delay in seconds before labels become inactive.  
If specified again while a delay is active, the initial duration is kept.

> **⚠️ Note:**
> Execution actually occurs **about 0.011 seconds later** than the specified time.

```python
from dataclasses import dataclass

from triggon import Triggon

tg = Triggon("hi", new="Hello")

@dataclass
class User:
    name: str = "Guest"
    init_done: bool = False

    def initialize(self):
        # Set the trigger for the first-time greeting
        tg.set_trigger("hi")

        self.init_done = True
        self.greet()

    def greet(self):
        msg = tg.switch_lit("hi", org="Welcome back")
        print(f"{msg}, {self.name}!")

    def entry(self):
        if self.init_done:
            self.greet()
        else:
            self.initialize()
            tg.revert("hi") # Revert to the original value

user = User()
user.entry() # Output: Hello, Guest!
user.entry() # Output: Welcome back, Guest!
```

```python
tg = Triggon({"name": "John", "state": True})

@dataclass
class User:
    name: str = None
    online: bool = False

    def login(self):
        # Set the variable for each label
        tg.switch_var({"name": self.name, "state": self.online})
        tg.set_trigger(["name", "state"])

user = User()
print(f"User name: {user.name}\nOnline: {user.online}")
# == Output ==
# User name: None
# Online: False

user.login()
print(f"User name: {user.name}\nOnline: {user.online}")
# == Output ==
# User name: John
# Online: True
```

---

### exit_point
`self, func: TrigFunc`  
`-> Any`

Defines the exit point where an early return is triggered by `trigger_return()`.  
The `func` argument must be a `TrigFunc` instance that wraps the target function.  

> **Note:** `exit_point()` is not required if `trigger_return()` is not triggered.

---

### trigger_return
`self, label: str | list[str] | tuple[str, ...], /,`  
`ret: Any = ...,`  
`*, index: int = None`  
`-> Any`

Triggers an early return with a value when any given label is active.  
The return value should be set at initialization.  
If no value is needed, you can set it to `None`,  
or just omit it (unless you’re using a dictionary).

You can also set the return value with the `ret` keyword argument.  
**This takes priority over the value from initialization**.  
This is useful when you need to set a return value dynamically.

If the return value is a function delayed by the `TrigFunc` class,  
it is automatically executed and its result is returned.

```python
from triggon import Triggon, TrigFunc

tg = Triggon("ret", None)

def sample(num):
    added = num + 5
    tg.set_trigger("ret", cond="added < 10")

    # Triggers an early return if 'added' is less than 10
    tg.trigger_return("ret")

    result = added / 10
    return result

F = TrigFunc() # Variable for delay

result = tg.exit_point(F.sample(10))
print(result) # Output: 1.5

result = tg.exit_point(F.sample(3))
print(result) # Output: None
```

```python
tg = Triggon("skip") # If no return value is needed, just pass the label
F = TrigFunc()

def sample():    
    # If "skip" is active, call the function 
    # and return early with its result
    ret_value = tg.trigger_func("skip", F.func())
    tg.trigger_return("skip", ret=ret_value)

    print("No return value")

def func():
    return "return value"

value = sample()
print(value)
# == Output ==
# No return value
# None

tg.set_trigger("skip") # Activate "skip"
value = tg.exit_point(F.sample())
print(value)
# == Output ==
# return value
```

---

### trigger_func
`self, label: str | list[str] | tuple[str, ...], /,`  
`func: TrigFunc`  
`-> Any`

Triggers a function when any given label is active.  
The `func` argument must be a `TrigFunc` instance that wraps the target function.

The return value should be set at initialization,  
but since the set value is never returned, any value can be used safely.
You can also omit it (unless you’re using a dictionary).  
**If the function returns a value, that value will also be returned**.

```python
from triggon import Triggon, TrigFunc

tg = Triggon({
    "skip": None,
    "call": None,
})

def func_a():
    tg.set_trigger(all=True) # Activate all labels

    print("If the 'call' is active, go to func_b().")

    tg.trigger_func("call", F.func_b())

    print("This message may be skipped depending on the trigger.")


def func_b():
    print("You've entered func_b()!")
    tg.trigger_return("skip")

F = TrigFunc()
tg.exit_point(F.func_a())
# == Output ==
# If the 'call' is active, go to func_b().
# You've entered func_b()!
```

---

### TrigFunc
This class wraps a function to delay its execution.  
Create an instance without any arguments and then, use the variable  
to wrap the target function.

It can delay most functions from existing libraries as well as your own,  
but not instance methods.

> ⚠️ **Note:**  
> `TrigFunc` does not support creating an instance and immediately chaining its methods  
> (e.g., `F.Sample(10).method()`).  
>  
> You must first create the instance normally, assign it to a variable,  
> and then call its methods through `TrigFunc`  
> (e.g., `smp = Sample(10)` → `F.smp.method()`).

---

### Error

#### ***InvalidArgumentError***
Raised when the number of arguments or their usage is incorrect.

#### ***InvalidClassVarError***
Raised when class attributes are registered from the global scope in `switch_var()`.

#### ***MissingLabelError***
Raised when the specific label has not been registered.

## License
This project is licensed under the MIT License.  
See [LICENSE](./LICENSE) for details.

## Author
Created by Tsuruko  
GitHub: [@tsuruko12](https://github.com/tsuruko12)  
X: [@tool_tsuruko12](https://x.com/tsuruko)
