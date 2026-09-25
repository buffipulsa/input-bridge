"""Small host actions for logical macropad events."""

from __future__ import annotations

import os


def execute_action(logical_event: str) -> None:
    """Execute the selected action for one logical event.

    The first real action is intentionally narrow: R1C1 opens/activates the
    Spotify URI registered by the Spotify Windows app.
    """

    if logical_event != "R1C1":
        return
    if os.name != "nt":
        raise RuntimeError("Spotify URI launching currently requires Windows")
    os.startfile("spotify:")
