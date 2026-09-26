"""Proposed host-event namespace for all 25 macropad controls.

This is a design document expressed as data.  It does not communicate with
the device and does not claim that modifier encoding has been validated yet.
"""

from __future__ import annotations

from .protocol951 import build_set_key_info_report, describe_report

GRID = [f"R{row}C{col}" for row in range(1, 5) for col in range(1, 5)]
KNOBS = [
    f"K{knob}-{direction}"
    for knob in range(1, 4)
    for direction in ("PRESS", "CCW", "CW")
]


def proposed_events() -> list[tuple[str, str]]:
    """Return logical control names and proposed HID event descriptions."""

    events: list[tuple[str, str]] = []

    # Twelve plain F-keys are assigned to the first three rows.
    for control, key_number in zip(GRID[:12], range(13, 25)):
        events.append((control, f"F{key_number}"))

    # A separate modifier namespace keeps the last four grid buttons unique.
    for control, key_number in zip(GRID[12:], range(13, 17)):
        events.append((control, f"CTRL+ALT+SHIFT+F{key_number}"))

    # Knobs use a second modifier-qualified namespace.  F25 does not exist,
    # so this deliberately reuses F13-F21 with a different modifier set.
    for control, key_number in zip(KNOBS, range(13, 22)):
        events.append((control, f"ALT+SHIFT+F{key_number}"))

    return events


def proposed_reports() -> list[tuple[str, str, bytes]]:
    """Build the proposed reports without communicating with the device."""

    reports: list[tuple[str, str, bytes]] = []

    for logical_index, (control, event) in enumerate(proposed_events()):
        # The physical grid is scanned bottom-to-top within each column.
        # Knob entries already use the profile's 16-24 order.
        if logical_index < 16:
            row, column = divmod(logical_index, 4)
            index = 4 * column + (3 - row)
        else:
            index = logical_index

        if logical_index < 12:
            modifiers = 0
            key_number = 13 + logical_index
        elif logical_index < 16:
            modifiers = 0x07  # Left Ctrl + Left Alt + Left Shift
            key_number = 13 + (logical_index - 12)
        else:
            modifiers = 0x06  # Left Alt + Left Shift
            key_number = 13 + (logical_index - 16)

        report = build_set_key_info_report(
            index,
            key_type=32,
            code1=modifiers,
            code2=0x68 + (key_number - 13),
        )
        reports.append((control, event, report))

    return reports


def main() -> None:
    print("Proposed reports only; no device communication")
    for index, (control, event, report) in enumerate(proposed_reports()):
        print(f"{index:2}: {control:7} -> {event:28} | {describe_report(report)}")
        print(f"    prefix: {report[:11].hex(' ')}")


if __name__ == "__main__":
    main()
