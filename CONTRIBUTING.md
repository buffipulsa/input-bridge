# Contributing

Contributions should preserve the project's incremental, inspectable design.

Before submitting a change:

1. Keep device access read-only unless a write is essential and clearly
   isolated.
2. Do not include vendor binaries, copied web assets, firmware dumps, or
   personal device paths.
3. Add a small explanation and a reproducible test or observation.
4. Keep command execution opt-in and avoid shell interpolation.
5. Run the relevant UV command and `python -m py_compile` on changed Python
   files.

Hardware protocol claims should include the observed VID/PID, interface, and
report bytes that support them.
