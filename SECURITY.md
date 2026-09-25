# Security policy

## Threat model

input-bridge can eventually turn hardware events into Python, Windows, WSL,
or other host commands. A malicious configuration is therefore equivalent to
local code execution.

## Safety principles

- Run as a standard user; administrator privileges are not required.
- Keep execution disabled by default during development.
- Prefer structured argument lists over shell command strings.
- Avoid `shell=True` unless there is a documented reason.
- Treat profiles, plugins, and imported configuration as executable content.
- Keep device writes separate from ordinary event observation.
- Do not add firmware flashing or custom-driver support without a separate
  security review.
- Never store credentials or tokens in profiles or logs.

## Reporting a vulnerability

Please do not publish an unpatched security issue with a working exploit.
Open a private security report if the repository hosting service supports it,
or contact the maintainers before public disclosure.
