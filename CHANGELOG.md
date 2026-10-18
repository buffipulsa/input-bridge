# Changelog

All notable user-facing changes are documented here.

## [Unreleased]

### Added

- External user codebases for Python scripts, configurable from Preferences.
- Safe relative-path validation for profile-referenced Python files.
- Reusable Python control template at `examples/code/template/controls.py`.
- Spotify example code at `examples/code/spotify/controls.py`.

### Changed

- Migrated the Spotify example profile from embedded source to an external
  `spotify/controls.py` reference.
- Spotify setup now uses PySide6 for its Client ID dialog.
- Updated profile and integration documentation for external scripts.
- Stabilized encoder cards and pad button sizes so controls do not stretch with
  the window.

### Removed

- Removed the Inspector panel and its in-application script editor. Scripts
  are now intended to be maintained in the user's preferred Python IDE.
