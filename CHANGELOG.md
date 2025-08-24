# Changelog

All notable changes to this project will be documented in this file.

---
## [1.0.0] - 2025-08-23
### Added
- New helper functions: `is_triggered()` and `is_registered()`
- `debug` keyword argument now supports sorting printed labels
- Support for switching between values and functions

#### TrigFunc
- Support for delaying functions from existing libraries

#### set_trigger
- `all` keyword argument to activate all labels at once
- `index` keyword argument to specify the index value of labels when switching variables
- `after` keyword argument to specify a delay time before labels become active

#### switch_lit
- Automatic execution of functions delayed by `TrigFunc` when returning a value

#### switch_var
- Automatic execution of functions delayed by `TrigFunc` when returning a value

#### revert
- `cond` keyword argument to set a condition for deactivating labels
- `after` keyword argument to specify a delay time before labels become inactive

#### trigger_return
- Support for passing multiple labels to the `label` argument
- Automatic execution of functions delayed by `TrigFunc` when returning a value

#### trigger_func
- Support for passing multiple labels to the `label` argument

### Changed
- Some cases that previously raised `InvalidArgumentError` now raise `TypeError`
- Improved debug output
- Strengthened error checking in all functions.

### Refactored
- Cleaned up code across multiple files

### Removed
- `alter_literal()` and `alter_var()`
- The `label` argument from `exit_point()`

### Fixed
- Various bug fixes

### Known Issues
- `switch_var()` may not work correctly when used multiple times in a single comparison expression  
  (since the value is updated in real time)

## [0.1.0b4] - 2025-07-22
### Changed
- Supported empty sequences or dictionaries as new values
- Labels and the `index` keyword now support variables and attribute chains

### Refactored
- Cleaned up code across multiple files

### Fixed
- Fixed bugs related to `debug` mode usage
- Fixed a bug that caused `IndexError` in certain cases

## [0.1.0b3] - 2025-07-17

### Added
- Aliases: `switch_lit()` → `alter_literal()`, `switch_var()` → `alter_var()`
- `cond` keyword argument in `set_trigger()` for setting conditions
- `all` keyword argument in `revert()` for reverting all labels
- `ret` keyword argument in `trigger_return()` for returning a value
- Support for switching multiple values for a single variable
- Support for multiple labels in `switch_lit()` (`alter_literal()`)

### Refactored
- Cleaned up code across multiple files

### Fixed
- Bugs in variable registration function

## ⚠️ Known issues
- Using a tuple as a value may raise an error.
- `switch_var()` may cause unexpected behavior in specific cases.
- In debug mode, it may cause unexpected behavior under specific conditions.

## [0.1.0b2] - 2025-07-09
### Added
- `revert()` now accepts multiple labels as a list or tuple

### Fixed
- Bug in variable registration logic inside `alter_var()` (some variables were not properly tracked)

## [0.1.0b1] - 2025-07-08
### Added
- `alter_var()` now returns the value when a single label is passed

### Fixed
- Bug where an incorrect frame was retrieved in a specific situation
