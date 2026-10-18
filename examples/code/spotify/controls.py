"""Spotify controls for the example Input Bridge profile.

The file is intentionally a normal Python module so it can be edited in a
user's preferred IDE. Input Bridge executes it in a child process and passes
the selected control through ``INPUT_BRIDGE_CONTROL``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import spotipy
from PySide6.QtWidgets import QApplication, QInputDialog
from spotipy.oauth2 import SpotifyPKCE

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "user-modify-playback-state user-read-playback-state"
SECRETS_FOLDER_NAME = "secrets"
CLIENT_ID_FILENAME = "spotify-client-id.txt"
PKCE_CACHE_FILENAME = "spotify-pkce-cache"
VOLUME_STEP = 10
REPEAT_STATES = ("off", "context", "track")

CONTROL_ACTIONS = {
    "R1C1": "spotify_open",
    "R1C2": "spotify_previous",
    "R1C3": "spotify_play_pause",
    "R1C4": "spotify_next",
    "R2C1": "spotify_shuffle",
    "R2C2": "spotify_repeat",
    "K2-CW": "spotify_volume_up",
    "K2-CCW": "spotify_volume_down",
}


def get_action_for_control(control: str | None) -> str:
    """Return the Spotify action assigned to an Input Bridge control."""

    action = CONTROL_ACTIONS.get(control)
    if action is None:
        raise RuntimeError(f"Unknown Spotify control: {control}")
    return action


def get_secrets_directory() -> Path:
    """Return the user-local directory for Spotify setup data."""

    local_app_data = os.environ.get("LOCALAPPDATA")
    app_data = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return app_data / "InputBridge" / SECRETS_FOLDER_NAME


def load_client_id(secrets_directory: Path) -> str:
    """Load or interactively collect the Spotify client ID."""

    client_id_path = secrets_directory / CLIENT_ID_FILENAME
    client_id = (
        client_id_path.read_text(encoding="utf-8").strip()
        if client_id_path.exists()
        else ""
    )
    if client_id:
        return client_id

    QApplication.instance() or QApplication([])
    client_id, accepted = QInputDialog.getText(
        None,
        "Spotify setup",
        "Spotify Client ID:",
    )

    if not accepted or not client_id.strip():
        raise RuntimeError("Spotify setup was cancelled")

    secrets_directory.mkdir(parents=True, exist_ok=True)
    client_id_path.write_text(client_id.strip(), encoding="utf-8")
    return client_id.strip()


def create_spotify_client(secrets_directory: Path) -> spotipy.Spotify:
    """Create an authenticated Spotipy client using PKCE."""

    client_id = load_client_id(secrets_directory)
    cache_path = secrets_directory / PKCE_CACHE_FILENAME
    return spotipy.Spotify(
        auth_manager=SpotifyPKCE(
            client_id=client_id,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            cache_path=str(cache_path),
        )
    )


def open_spotify() -> None:
    """Open the Spotify desktop application on Windows."""

    if os.name != "nt":
        raise RuntimeError("Spotify launching requires Windows")
    os.startfile("spotify:")


def start_playback_on_available_device(spotify: spotipy.Spotify) -> None:
    """Start playback on the active device or the first available device."""

    devices = spotify.devices().get("devices", [])
    target = next((device for device in devices if device.get("is_active")), None)
    target = target or next(iter(devices), None)
    if target is None or not target.get("id"):
        raise RuntimeError("Spotify has no available playback device; open Spotify first")
    spotify.start_playback(device_id=target["id"])


def toggle_playback(spotify: spotipy.Spotify, playback: dict[str, Any] | None) -> None:
    """Pause or resume the current playback, starting it if needed."""

    if playback is None:
        start_playback_on_available_device(spotify)
        return
    if playback.get("is_playing"):
        spotify.pause_playback()
    else:
        spotify.start_playback()


def change_volume(spotify: spotipy.Spotify, playback: dict[str, Any], action: str) -> None:
    """Adjust the active device volume by the configured step."""

    current = (playback.get("device") or {}).get("volume_percent")
    if not isinstance(current, int):
        raise TypeError("Spotify did not report the active volume")
    delta = VOLUME_STEP if action == "spotify_volume_up" else -VOLUME_STEP
    spotify.volume(max(0, min(100, current + delta)))


def execute_action(spotify: spotipy.Spotify, action: str) -> None:
    """Execute one mapped Spotify action."""

    if action == "spotify_open":
        open_spotify()
        return

    playback = spotify.current_playback()
    if action == "spotify_play_pause":
        toggle_playback(spotify, playback)
        return
    if playback is None:
        raise RuntimeError("Spotify has no active playback device; press Play/Pause first")
    if action == "spotify_previous":
        spotify.previous_track()
    elif action == "spotify_next":
        spotify.next_track()
    elif action in {"spotify_volume_down", "spotify_volume_up"}:
        change_volume(spotify, playback, action)
    elif action == "spotify_shuffle":
        spotify.shuffle(not bool(playback.get("shuffle_state")))
    elif action == "spotify_repeat":
        current = playback.get("repeat_state", "off")
        try:
            next_state = REPEAT_STATES[(REPEAT_STATES.index(current) + 1) % len(REPEAT_STATES)]
        except ValueError:
            next_state = REPEAT_STATES[0]
        spotify.repeat(next_state)


def main() -> None:
    """Resolve the Input Bridge control and execute its Spotify action."""

    action = get_action_for_control(os.environ.get("INPUT_BRIDGE_CONTROL"))
    if action == "spotify_open":
        open_spotify()
        return
    secrets_directory = get_secrets_directory()
    spotify = create_spotify_client(secrets_directory)
    execute_action(spotify, action)


if __name__ == "__main__":
    main()
