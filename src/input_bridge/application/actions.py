"""Small host actions for logical macropad events."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence

from ..domain.profiles import BindingDefinition, ProfileDocument


def find_profile_binding(
    logical_event: str,
    profile: ProfileDocument,
    trigger: str = "press",
    active_layer_path: Sequence[str] = (),
) -> BindingDefinition | None:
    """Find the profile binding for a control and trigger.

    Parameters
    ----------
    logical_event : str
        Stable logical control identifier.
    profile : ProfileDocument
        Profile containing the bindings to search.
    trigger : str, default="press"
        Trigger type to match.
    active_layer_path : Sequence[str], optional
        Current layer path. A binding applies when its path is a prefix of
        this path; the most specific matching binding wins.

    Returns
    -------
    BindingDefinition or None
        The matching binding, if one exists.
    """

    active_path = tuple(active_layer_path)
    candidates = [
        item
        for item in profile.bindings
        if (
            item.control == logical_event
            and item.trigger == trigger
            and tuple(item.layer_path) == active_path[: len(item.layer_path)]
        )
    ]
    return max(candidates, key=lambda item: len(item.layer_path), default=None)


def describe_profile_action(
    logical_event: str,
    profile: ProfileDocument,
    trigger: str = "press",
    active_layer_path: Sequence[str] = (),
) -> str:
    """Describe a profile action without executing it.

    Parameters
    ----------
    logical_event : str
        Stable logical control identifier.
    profile : ProfileDocument
        Profile containing the action definitions.
    trigger : str, default="press"
        Trigger type to match.
    active_layer_path : Sequence[str], optional
        Current layer path used to select the most specific binding.

    Returns
    -------
    str
        Human-readable action description suitable for a dry-run UI.
    """

    binding = find_profile_binding(
        logical_event,
        profile,
        trigger,
        active_layer_path,
    )
    if binding is None:
        return "Unassigned"
    if binding.action_id == "open_spotify":
        return "Open Spotify"
    if binding.action_id == "run_script":
        if binding.script_id is None:
            return "Script: missing script id"
        script = next(
            (item for item in profile.scripts if item.script_id == binding.script_id),
            None,
        )
        if script is None:
            return f"Script: missing {binding.script_id}"
        return f"Script: {script.name}"
    return f"Action: {binding.action_id}"


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


def execute_profile_action(
    logical_event: str,
    profile: ProfileDocument,
    trigger: str = "press",
    active_layer_path: Sequence[str] = (),
) -> None:
    """Execute the script bound to one logical event in a profile.

    This function is intentionally only called by an explicit execution path.
    The script is run in a child Python process without shell interpolation.

    Parameters
    ----------
    logical_event : str
        Stable logical control identifier emitted by the event normalizer.
    profile : ProfileDocument
        Profile containing the binding and script source.
    trigger : str, default="press"
        Trigger type to match.
    active_layer_path : Sequence[str], optional
        Active layer path used to select the most specific binding.

    Raises
    ------
    LookupError
        If the event has no binding or its script is missing.
    subprocess.CalledProcessError
        If the script process exits unsuccessfully.
    """

    binding = find_profile_binding(
        logical_event,
        profile,
        trigger,
        active_layer_path,
    )
    if binding is None:
        raise LookupError(f"no profile binding for {logical_event!r}")
    if binding.action_id == "open_spotify":
        if os.name != "nt":
            raise RuntimeError("Spotify URI launching currently requires Windows")
        os.startfile("spotify:")
        return
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
