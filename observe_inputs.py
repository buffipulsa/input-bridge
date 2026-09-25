"""Passively observe input reports from one standard HID collection.

This script never writes to the device and never requests a feature report.
The vendor-defined interface is excluded intentionally.
"""

from __future__ import annotations

import sys
import time


VENDOR_ID = 0x0816
PRODUCT_ID = 0x2475
OBSERVATION_SECONDS = 10


def report_id_for(device: dict[str, object]) -> int:
    """Return the report ID identified in the inspected descriptor."""

    if device.get("interface_number") == 1:
        return 0

    return {
        (0x0001, 0x0006): 1,
        (0x000C, 0x0001): 3,
        (0x0001, 0x0080): 4,
        (0x0001, 0x000C): 5,
        (0x0001, 0x0002): 2,
    }[(device["usage_page"], device["usage"])]


def main() -> int:
    try:
        import hid
    except ImportError:
        print("hidapi is not installed; run: uv sync", file=sys.stderr)
        return 1

    devices = [
        device
        for device in hid.enumerate(VENDOR_ID, PRODUCT_ID)
        if device.get("usage_page") != 0xFF00
    ]

    if not devices:
        print("No standard HID collections found.")
        return 1

    print("Standard HID collections available for passive observation:")
    for index, device in enumerate(devices, start=1):
        print(
            f"  {index}: interface={device.get('interface_number')} "
            f"usage_page=0x{device.get('usage_page', 0):04X} "
            f"usage=0x{device.get('usage', 0):04X} "
            f"product={device.get('product_string')}"
        )

    try:
        selection = int(input("Select a collection number: "))
        device = devices[selection - 1]
    except (ValueError, EOFError, IndexError):
        print("Invalid selection.", file=sys.stderr)
        return 1

    handle = hid.device()
    try:
        handle.open_path(device["path"])
        report_id = report_id_for(device)
        print(
            f"Listening for {OBSERVATION_SECONDS} seconds. "
            "Press one key or turn one encoder at a time.\n"
            f"Polling input report ID {report_id}."
        )

        end_time = time.monotonic() + OBSERVATION_SECONDS
        last_report: bytes | None = None
        while time.monotonic() < end_time:
            # This is a standard HID GET_REPORT request for an input report.
            # It does not send output or feature data to the device.
            report = handle.get_input_report(report_id, 64)
            report_bytes = bytes(report)
            if report_bytes and report_bytes != last_report:
                print(report_bytes.hex(" "))
                last_report = report_bytes
            else:
                time.sleep(0.05)
    except (OSError, ValueError) as error:
        print(f"Could not observe this collection: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nObservation stopped.")
    finally:
        handle.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
