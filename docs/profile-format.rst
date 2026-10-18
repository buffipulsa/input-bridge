Profile format
==============

Input Bridge profiles are portable, versioned JSON documents containing layer
data, control bindings, relative references to user-authored scripts, and
optional application connector references. External script paths are resolved
relative to the user-selected codebase directory; absolute paths and paths
that escape that directory are rejected. Embedded script source is supported
only for legacy profile compatibility.

The detailed schema and example are available as a downloadable Markdown
document:

* :download:`profile-format.md <profile-format.md>`

Importing a profile must validate its schema and show referenced executable
content before anything is enabled or run. Loading a profile never executes
its scripts.

External user code
-------------------

New profiles should reference user-authored Python files with a relative
``path`` such as ``spotify/controls.py``. The path is resolved from the
codebase directory configured in Preferences, which defaults to
``%LOCALAPPDATA%\\InputBridge\\code`` on Windows. Use a preferred Python IDE
to edit those files. Legacy profiles with embedded ``source`` remain
supported.
