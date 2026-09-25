# input-bridge

Host-side software for a programmable USB macropad with 16 keys and three
rotary encoders.

The project targets the tested device identified by:

```text
Vendor ID: 0x0816
Product ID: 0x2475
```

The macropad stores only neutral HID mappings. The actual actions run on the
host computer, allowing profiles for Maya, VS Code, Unreal, and other tools.

## Current status

- HID collections and the vendor-defined interface have been identified.
- The 4x4 grid and all nine knob actions have been remapped to unique events.
- Windows Raw Input is normalized into IDs such as `R1C1`, `K2-CW`, and
  `K3-PRESS`.
- A dry-run action dispatcher is available.
- `R1C1` can optionally open Spotify on Windows.
- Layer/profile and PySide6 UI work is next.

## Setup with UV

Windows PowerShell:

```powershell
uv sync
uv run python .\inspect_macropad.py
```

The project uses a local virtual environment and does not require global
Python packages. If UV's cache location is not writable on your machine, use:

```powershell
$env:UV_CACHE_DIR=".uv-cache"
uv sync
```

## Observe events

```powershell
uv run python .\observe_raw_input.py "manual-test" --seconds 5
```

The default is dry-run mode. To execute the currently configured Spotify
action for `R1C1`:

```powershell
uv run python .\observe_raw_input.py "spotify-test" --seconds 5 --execute-actions
```

## Safety

The `write_*.py` scripts modify persistent mappings in the device. They are
not needed for normal event observation and should only be run after reviewing
their target interface and report bytes.

The project does not flash firmware, install drivers, or require administrator
privileges. External action execution is deliberately opt-in. Treat imported
profiles, plugins, and arbitrary command definitions as executable code.

## Project layout

```text
inspect_macropad.py       Read-only HID enumeration and descriptors
observe_raw_input.py      Windows Raw Input observer
event_normalizer.py       HID sequence to logical-control conversion
protocol951.py             Offline/report helpers for the tested device
read_*.py                  Read-only device inspection helpers
write_*.py                 Persistent device mapping writers
bindings.py                Dry-run logical bindings
actions.py                 Host actions
neutral_mapping.py         Proposed 25-control mapping
```

## Scope

This is an independent interoperability project. It does not include vendor
software, firmware, copied assets, or proprietary binaries. Similar-looking
macropads should not be assumed to use the same protocol.

See [docs/protocol-951.md](docs/protocol-951.md) for the current protocol
notes and [SECURITY.md](SECURITY.md) for the threat model.

## License

This project is released under the MIT License. See [LICENSE](LICENSE).
