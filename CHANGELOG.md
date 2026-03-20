# Changelog

All notable changes to this project will be documented in this file.

______________________________________________________________________

### [2.0.1] - 2026-03-20

#### Added

- Added `RollbackSourceError`, a new public error for cases where `rollback()` cannot find the caller's source file

#### Fixed

- Fixed `rollback()` source lookup to prevent stale `co_filename` paths after renames or cached bytecode from breaking source discovery when the module `__file__` is still available

### [2.0.0] - 2026-03-18

#### Breaking Changes

- Replaced `switch_var()` with `register_ref()` and `register_refs()` for applying label-controlled values to variables and attributes
- Replaced `exit_point()` with the `capture_return()` context manager, and updated `trigger_return()` to work only inside that context
- Renamed `trigger_func()` to `trigger_call()`
- `is_triggered()` and `is_registered()` now return a single `bool` and support `match_all` instead of returning per-item result sequences
- Updated several API names and signatures for consistency, including `new` to `new_values` and `index` to `indices` where multiple labels are supported

#### Added

- New constructors: `from_label()` and `from_labels()`
- New label registration APIs: `add_label()` and `add_labels()`
- New reference management API: `unregister_refs()`
- New context manager: `rollback()` for restoring temporary updates on exit
- Support for `reschedule` in `set_trigger()` and `revert()`
- Environment-variable-based debug configuration with `TRIGGON_LOG_VERBOSITY`, `TRIGGON_LOG_FILE`, and `TRIGGON_LOG_LABELS`
- A comprehensive automated test suite

#### Changed

- Reorganized the package into a `src/` layout and split the implementation into clearer internal modules
- Improved `TrigFunc` so deferred targets can be reused across scopes and passed more flexibly
- Improved debug logging and deferred call handling with `TrigFunc`
- Improved debug log output for readability
- When registering values, a non-string sequence can now be treated as a single value by wrapping it in any outer sequence, not just a list or tuple
- Strengthened validation and error reporting across the API
- Refreshed the README and API docstrings

### [1.0.1] - 2025-08-26

### Fixed

- Raise error when switching values in `switch_var()`.

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

### Removed

- `alter_literal()` and `alter_var()`
- The `label` argument from `exit_point()`

### Fixed

- Various bug fixes

## [0.1.0b4] - 2025-07-22

### Changed

- Supported empty sequences or dictionaries as new values
- Labels and the `index` keyword now support variables and attribute chains

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
