# Spotify integration

The repository includes a ready-made profile at
`examples/profiles/spotify.input-bridge.json` with a `Spotify` layer and the
external script at `examples/code/spotify/controls.py`. It is an optional
example integration, not a required part of Input Bridge.

## Install

Users who want Spotify support should install the optional dependency:

```powershell
uv sync --extra spotify
```

Users who do not use Spotify can use the normal `uv sync` command without
installing Spotipy.

Copy `examples/profiles/spotify.input-bridge.json` into:

```text
%LOCALAPPDATA%\InputBridge\profiles
```

Copy the `examples/code/spotify` directory into the user codebase configured
in Preferences. The default codebase is:

```text
%LOCALAPPDATA%\InputBridge\code
```

Import it in the layer editor, select the Spotify layer, and enable Execute
Actions only when you are ready to control playback.

## Authentication

The profile references `spotify/controls.py`; Input Bridge does not contain a
Spotify integration module. The script uses Spotipy's PKCE OAuth flow. You can
edit the file in any Python IDE and reuse it from other profiles.

Register this redirect URI in the Spotify application settings:

```text
http://127.0.0.1:8888/callback
```

On the first Spotify control, Input Bridge prompts for the Client ID, stores
that non-secret value under `%LOCALAPPDATA%\InputBridge\secrets`, and opens a
browser for consent. The PKCE token cache is stored in the same local secrets
folder. Do not copy or commit that folder. No client secret or environment
variable is required.

## Command mappings

| Control | Command |
| --- | --- |
| R1C1 | Open Spotify |
| R1C2 | Previous track |
| R1C3 | Play/Pause |
| R1C4 | Next track |
| R2C1 | Shuffle |
| R2C2 | Repeat |
| K2-CW | Volume up |
| K2-CCW | Volume down |

Spotify playback requires an active playback device and a Spotify Premium
account.
