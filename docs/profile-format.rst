Profile format
==============

Input Bridge profiles are portable, versioned JSON documents containing layer
data, control bindings, user-authored scripts or relative script references,
and optional application connector references. External script paths are
resolved relative to the user-selected codebase directory; absolute paths and
paths that escape that directory are rejected.

The detailed schema and example are available as a downloadable Markdown
document:

* :download:`profile-format.md <profile-format.md>`

Importing a profile must validate its schema and show included executable
content before anything is enabled or run. Loading a profile never executes
its scripts.
