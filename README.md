# triggon

## Overview
Dynamically switch multiple values at specific trigger points.

> ⚠️ **This library is currently in beta. APIs may change in future releases, and bugs may still be present.**

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)
- [Author](#author)


## Features
- Switch multiple values at once with a single trigger point.
- No `if` or `match` statements needed.
- Switch both literal values and variables.
- Trigger early returns with optional return values.
- Automatically jump to other functions at a trigger point.

## Installation
```bash
pip install triggon
```

## Usage
This section explains how to use each function.

### Triggon
`Triggon(self, label: str | dict[str, Any], /, new: Any=None, *, debug: bool=False)`

`Triggon()` is initialized with label-value pairs.  
You can pass a single label with its value, or multiple labels using a dictionary.

If you pass multiple values to a label using a list,  
each value will correspond to index 0, 1, 2, and so on, in the order you provide.

```python
from triggon import Triggon

# Set index 0 to 100 and index 1 to 0 as their new values
tg = Triggon("num", new=[100, 0])

def example():
    x = tg.alter_literal("num", 0)    # index 0
    y = tg.alter_literal("*num", 100) # index 1

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
    x = tg.alter_literal("seq1", 10) # index 0
    y = tg.alter_literal("seq2", 10) # index 0

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

tg = Triggon("mode", new=True) # Set index 0 to True for label 'mode'

@dataclass
class ModeFlags:
    mode_a: bool = False
    mode_b: bool = False
    mode_c: bool = False

    def set_mode(self, enable: bool):
        if enable:
            tg.set_trigger("mode")

        tg.alter_var("mode", [self.mode_a, self.mode_b, self.mode_c]) # All values share index 0

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

If you want to trace label activity in real time, set the `debug` keyword to `True`.

> ⚠️ **Note:** 
Labels with the `*` prefix cannot be used during initialization 
and will raise an `InvalidArgumentError`.

### set_trigger
`def set_trigger(self, label: str | list[str] | tuple[str, ...], /) -> None`

Marks the specified label(s) as triggered, 
allowing their values to be updated on the next call.  
All values associated with the specified label will be changed, regardless of their index.  
The `label` parameter accepts a single string or a list/tuple of labels.

If any of the specified labels have been disabled using `revert()`, 
this function has no effect on them.

```python
from triggon import Triggon

tg = Triggon({
    "milk": 3,
    "banana": 0.4,
    "msg": "We're having a sale for milk today!",
})

def example():
    msg = tg.alter_literal("msg", org="We're open as usual today.")
    print(msg)

    milk = tg.alter_literal('milk', 4)
    banana = tg.alter_literal('banana', 0.6)

    print(f"Milk: ${milk}")
    print(f"Banana: ${banana}")

example()
# == Output ==
# We're open as usual today.
# Milk: $4
# Banana: $0.6

tg.set_trigger(["milk", "msg"]) # Triggers for 'milk' and 'msg' are activated here.

example()
# == Output ==
# We're having a sale for milk today!
# Milk: $3
# Banana: $0.6
```

### alter_literal
`def alter_literal(self, label: str, /, org: Any, *, index: int=None) -> Any`

Changes a literal value when the flag is set to `True`.  
You can also use this function directly inside a print().  
When using a dictionary for `label`, the `index` keyword cannot be used.

```python
from triggon import Triggon

tg = Triggon("text", new="After") 

def example():
    text = tg.alter_literal("text", org="Before", index=0)
    print(text)  

    # You can also write: 
    # print(tg.alter_literal('text', 'Before'))

    tg.set_trigger("text")

example() # Output: Before
example() # Output: After
```

Alternatively, you can use the `*` character as a prefix to specify the index.  
For example, `"label"` refers to index 0, and `"*label"` refers to index 1.

You can use the `index` keyword or the `*` prefix.  
When both are provided, the keyword takes precedence.  
`*` used elsewhere (not as a prefix) is ignored and has no special meaning.

```python
# Set the value to 'A' for index 0 and to 'B' for index 1
tg = Triggon("char", new=("A", "B"))

def example():
    tg.set_trigger("char")

    print(tg.alter_literal("char", 0))           # index 0 (no '*' — defaults to index 0)
    print(tg.alter_literal("*char", 1))          # index 1 (using '*')
    print(tg.alter_literal("*char", 0, index=0)) # index 0 ('index' keyword takes precedence over '*')
    print(tg.alter_literal("char", 1, index=1))  # index 1 (using 'index' keyword)

example()
# == Output ==
# A
# B
# A
# B
```

> **Note:** 
For better readability when working with multiple indices, 
it's recommended to use the `index` keyword.

### alter_var
`def alter_var(self, label: str | dict[str, Any], var: Any=None, /, *, index: int=None) -> None`

Changes variable value(s) directly when the flag is set to `True`.  
It supports global variables and class attributes, but not local variables.

You can pass multiple labels and variables using a dictionary.    
The `index` keyword cannot be used in that case.  
If the target index is 1 or greater, 
add a `*` prefix to the label corresponding to the index  
(e.g., `*label` for index 1, `**label` for index 2).

In such cases, it is recommended to use individual calls to this function  
with the `index` keyword instead, for better readability.

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

    tg.alter_var(result, level)
    tg.alter_var(result, attack, index=1)

    # Outputs vary randomly.
    # Example: result = 'level_2'
    print(f"You pulled {level} sword!") # Output: You pulled a rare sword!
    print(f"Attack Power: {attack}")    # Output: Attack Power: 100 

spin_gacha()
```

```python
from dataclasses import dataclass

from triggon import Triggon

tg = Triggon("even", [0, 2, 4])

@dataclass
class Example:
    a: int = 1
    b: int = 3
    c: int = 5

    def change_field_values(self, change: bool):
        if change:
            tg.set_trigger("even")

        tg.alter_var({
            "even": self.a,    # index 0
            "*even": self.b,   # index 1
            "**even": self.c,  # index 2
        })

exm = Example()

exm.change_field_values(False)
print(f"a: {exm.a}, b: {exm.b}, c: {exm.c}")
# Output: a: 1, b: 3, c: 5

exm.change_field_values(True)
print(f"a: {exm.a}, b: {exm.b}, c: {exm.c}")
# Output: a: 0, b: 2, c: 4
```

> **Notes:** 
Values are typically updated when `set_trigger()` is called.  
However, on the first call, 
the value won't change unless the variable has been registered via `alter_var()`.  
In that case, the value is changed by `alter_var()`.  
Once registration is complete, each call to `set_trigger()` immediately updates the value.  

The `index` keyword does not accept a variable — only integer literals are allowed.

### revert
`def revert(self, label: str, /, *, disable: bool=False) -> None`

Reverts all values previously changed by `alter_literal()` or `alter_var()`  
to their original state.  
The reversion remains effective until the next call to `set_trigger()`.  
All values associated with the specified label will be reverted, 
regardless of their index.

If the `disable` keyword is set to `True`, the reversion becomes permanent.

```python
from triggon import Triggon

tg = Triggon("hi", new="Hello")

@dataclass
class User:
    name: str = "Guest"
    init_done: bool = False

    def initialize(self):
        tg.set_trigger("hi") # Set the trigger for the first-time greeting

        self.init_done = True
        self.greet()

    def greet(self):
        msg = tg.alter_literal("hi", org="Welcome back")
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
tg = Triggon("A", "Updated value")

x = "Original value"
tg.alter_var("A", x)

def example():
    print(x)

    tg.set_trigger("A")

    print(x)

    tg.revert("A", disable=True)

example()
# == Output ==
# Original value
# Updated value

example()
# == Output ==
# Original value
# Original value
```

### exit_point
`def exit_point(self, label: str, func: TrigFunc, /) -> None | Any`

Defines the exit point where an early return is triggered by `trigger_return()`.  
The `func` argument must be a `TrigFunc` instance that wraps the target function.  

An index with the `*` prefix can be used, but it is ignored.

### trigger_return
`trigger_return(self, label: str, /, *, index: int=None, do_print: bool=False) -> None | Any`

Triggers an early return with any value when the flag is set to `True`.  
The return value must be set during initialization.  
If nothing needs to be returned, set it to `None`.

If the `do_print` keyword is set to `True`, the return value will be printed.  
If the value is not a string, an `InvalidArgumentError` is raised.

```python
from triggon import Triggon, TrigFunc

# Define label and early-return value
tg = Triggon("skip", new="(You don't have enough money...)")
F = TrigFunc() # Wraps the target function for early return

def check_funds(money: int):
    if money < 300:
        tg.set_trigger("skip")

    print(f"You now have {money}G.")
    board_ship()

def board_ship():
    print("It'll cost you 300G to board the ship.")

    # Triggers early return and prints the value if the flag is set
    tg.trigger_return("skip", do_print=True) 

    print("Enjoy the ride!")  

tg.exit_point("skip", F.check_funds(500))
# == Output ==
# You now have 500G.
# It'll cost you 300G to board the ship.
# Enjoy the ride!

tg.exit_point("skip", F.check_funds(200))
# == Output ==
# You now have 200G.
# It'll cost you 300G to board the ship.
# (You don't have enough money...)
```

### trigger_func
`def trigger_func(self, label: str, func: TrigFunc, /) -> None | Any`

Triggers a function when the flag is set to `True`.  
The `func` argument must be a `TrigFunc` instance that wraps the target function.

The label must be initialized with `None` when creating the `Triggon` instance.  
An index with the `*` prefix can be used, but it is ignored.

If the function returns a value, it will also be returned.

```python
from triggon import Triggon, TrigFunc

tg = Triggon({
    "skip": None,
    "call": None,
})
F = TrigFunc()

def example():
    tg.set_trigger(["skip", "call"]) # Set triggers for early return and function call

    print("If the 'call' flag is active, jump to example_2().")

    tg.trigger_func("call", F.example_2()) # Use the TrigFunc instance F for example_2()

    print("This message may be skipped depending on the trigger.")


def example_2():
    print("You’ve reached the example_2() function!")
    tg.trigger_return("skip")

tg.exit_point("skip", F.example())
# == Output ==
# If the 'call' flag is active, jump to example_2().
# You’ve reached the example_2() function!
```

### TrigFunc
This class wraps a function to delay its execution.   
You can create an instance without any arguments and use it to wrap the target function.

> ⚠️ **Note:**  
When using this class,  
you must create an instance first (e.g., F = TrigFunc()) before using it.

### Error
- `InvalidArgumentError`  
Raised when the number of arguments, their types, or usage is incorrect.

## License
This project is licensed under the MIT License.  
See [LICENSE](./LICENSE) for details.

## Author
Created by Tsuruko  
GitHub: [@tsuruko12](https://github.com/tsuruko12)  
X: [@tool_tsuruko12](https://x.com/tsuruko)
