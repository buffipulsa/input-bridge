"""Small host actions for logical macropad events."""

from __future__ import annotations

import os
import subprocess
import sys

from ..domain.profiles import ProfileDocument


def execute_action(logical_event: str) -> None:
    """Execute the selected action for one logical event.

    The first real action is intentionally narrow: R1C1 opens/activates the
    Spotify URI registered by the Spotify Windows app.

    Parameters
    ----------
    logical_event : str
        Stable logical control identifier emitted by the event normalizer.

    Raises
    ------
    RuntimeError
        If the Spotify action is requested on a non-Windows platform.
    """

    if logical_event != "R1C1":
        return
    if os.name != "nt":
        raise RuntimeError("Spotify URI launching currently requires Windows")
    os.startfile("spotify:")


def execute_profile_action(logical_event: str, profile: ProfileDocument) -> None:
    """Execute the script bound to one logical event in a profile.

    This function is intentionally only called by an explicit execution path.
    The script is run in a child Python process without shell interpolation.

    Parameters
    ----------
    logical_event : str
        Stable logical control identifier emitted by the event normalizer.
    profile : ProfileDocument
        Profile containing the binding and script source.

    Raises
    ------
    LookupError
        If the event has no binding or its script is missing.
    subprocess.CalledProcessError
        If the script process exits unsuccessfully.
    """

    binding = next(
        (item for item in profile.bindings if item.control == logical_event),
        None,
    )
    if binding is None:
        raise LookupError(f"no profile binding for {logical_event!r}")
    if binding.action_id != "run_script" or binding.script_id is None:
        raise LookupError(f"binding for {logical_event!r} is not a script action")

    script = next(
        (item for item in profile.scripts if item.script_id == binding.script_id),
        None,
    )
    if script is None:
        raise LookupError(f"script {binding.script_id!r} was not found")

    subprocess.run(
        [sys.executable, "-c", script.source],
        check=True,
        shell=False,
    )
