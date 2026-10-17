# Spotify integration

The repository includes a ready-made profile at
`examples/profiles/spotify.input-bridge.json` with a `Spotify` layer. It is an
optional example integration, not a required part of Input Bridge.

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

Import it in the layer editor, select the Spotify layer, and enable Execute
Actions only when you are ready to control playback.

## Authentication

The profile stores its Python source in the profile's `scripts` section; Input
Bridge does not contain a Spotify integration module. The script uses
Spotipy's PKCE OAuth flow.

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
| R2C1 | Volume down |
| R2C2 | Volume up |
| R2C3 | Shuffle |
| R2C4 | Repeat |
| K2-CW | Volume up |
| K2-CCW | Volume down |

Spotify playback requires an active playback device and a Spotify Premium
account.
