# Changelog

All notable changes to this project will be documented in this file.

---

## [0.1.0b3] - 2025-07-17
### Added
- Alias `switch_lit()` for `alter_literal()` and `switch_var()` for `alter_var()`
- `cond` keyword to set conditions in `set_trigger()`
- `all` keyword to revert all labels in `revert()`
- `ret` keyword to return a value in `trigger_return()`
- Support for switching multiple values for a single variable
- Support for multiple labels in `switch_lit()` (`alter_literal()`)

### Fixed
- Bugs in variable registration function

### Refactoring
- Cleaned up code across multiple files

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
