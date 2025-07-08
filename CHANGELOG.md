# Changelog

All notable changes to this project will be documented in this file.

---

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