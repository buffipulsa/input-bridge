Profile format
==============

Input Bridge profiles are portable, versioned JSON documents containing layer
data, control bindings, user-authored scripts, and optional application
connector references.

The detailed schema and example are available as a downloadable Markdown
document:

* :download:`profile-format.md <profile-format.md>`

Importing a profile must validate its schema and show included executable
content before anything is enabled or run. Loading a profile never executes
its scripts.
