# Contributing

Thank you for contributing to input-bridge. The project is developed
incrementally so that the hardware behavior, host-side event model, actions,
and UI remain understandable and independently testable.

## Development setup

Use [UV](https://docs.astral.sh/uv/) and the project-local environment. Do not
install project dependencies globally.

```powershell
uv sync
```

The project currently targets Python `>=3.14,<3.15`. If UV's cache and the
project are on different filesystems, use a project-local cache:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv sync
```

## Project structure

- `src/input_bridge/domain` contains hardware-independent concepts such as
  normalized events, layers, profiles, and protocol data.
- `src/input_bridge/application` contains action dispatch and application
  services.
- `src/input_bridge/infrastructure` contains Windows/HID integration and
  inspection tools.
- `src/input_bridge/ui` contains the PySide6 user interface.
- `docs` contains public documentation and Sphinx configuration.
- `tests` contains automated tests.

Keep device protocol, event normalization, action execution, layer selection,
and UI concerns separate. Prefer a small explicit change over a speculative
framework or broad refactor.

## Development workflow

Before changing repository files:

1. Read the relevant implementation and documentation.
2. Identify the behavior or contract being changed.
3. Propose the smallest focused implementation step.
4. Explain important assumptions and safety implications.
5. Add or update a reproducible test, observation, or documentation example.

For hardware behavior that is not understood yet, use a focused experiment
and record the observed VID/PID, interface, usage, report size, and relevant
report bytes. Do not infer a protocol from a visually similar device.

## Verification

Run checks relevant to the files changed. The usual source checks are:

```powershell
.\.venv\Scripts\ruff.exe check src
.\.venv\Scripts\python.exe -m compileall -q src
```

For documentation changes, also build the Sphinx documentation with warnings
treated as errors:

```powershell
.\.venv\Scripts\python.exe -m sphinx -W --keep-going -b html docs docs\_build\html
```

When behavior depends on the physical macropad, prefer a short reproducible
observation such as:

```powershell
uv run observe-raw-input "manual-test" --seconds 5
```

Keep action execution disabled unless a test explicitly requires it. Use the
project's dry-run mode wherever possible.

## HID and device safety

Read-only enumeration and observation are the default. Before any device
write, obtain explicit approval for that specific operation and verify the
target VID, PID, interface, usage page, usage, report size, and mapping.

Do not:

- send guessed input, output, or feature reports;
- modify persistent device mappings without a documented recovery path;
- flash firmware or enter a bootloader;
- install or execute vendor configuration software;
- add custom drivers or administrator requirements without a separate design
  and security review.

Keep backups and recovery information available before any approved broad
configuration change.

## Host actions, profiles, and scripts

Profiles, plugins, imported configuration, and saved scripts are executable
content from a security perspective. Treat them as equivalent to local code.

- Keep dry-run behavior as the default.
- Make real action execution explicitly opt in.
- Prefer built-in actions or allowlisted script paths where practical.
- Represent subprocesses as argument lists, not interpolated shell strings.
- Avoid `shell=True` unless there is a documented reason.
- Run as a standard user and do not request elevation by default.
- Never store credentials, tokens, or other secrets in profiles or logs.
- Preserve a global disable or emergency-stop path as execution features grow.

Application-specific integrations, such as Maya, should use an explicit
connector or bridge appropriate to that application. A normal external Python
process should not assume it can import application-owned modules such as
`maya.cmds`.

## Documentation and public repository boundaries

Use NumPy-style docstrings for public Python APIs and keep Sphinx documentation
consistent with implemented behavior. Document contracts and independently
observed protocol facts rather than assumptions or copied vendor material.

Do not commit:

- private agent instructions or planning notes;
- personal machine paths, usernames, device instance paths, or serial numbers;
- credentials, tokens, local configuration, or logs containing sensitive data;
- vendor binaries, copied web assets, firmware dumps, or unrelated captures.

Private development guidance such as `AGENTS.md` and `dev_docs` is intentionally
excluded through `.git/info/exclude`, not `.gitignore`.

## Git workflow

Organize changes into small, coherent commits. Before committing:

1. Review the working tree and staged file list.
2. Inspect the staged diff for scope, paths, and sensitive data.
3. Run the relevant verification commands.
4. Summarize what is complete and propose a concise commit message.
5. Wait for explicit approval before running `git commit`.

Do not include unrelated changes. Do not push, amend, squash, rebase, reset, or
rewrite history without explicit approval.
