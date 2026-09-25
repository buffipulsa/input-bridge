"""Read-only probe for the macropad's vendor-defined HID interface.

This sends only standard HID GET_INPUT_REPORT requests. It does not send
output reports, feature reports, configuration commands, or firmware data.
"""

from __future__ import annotations

import sys
import time


VID = 0x0816
PID = 0x2475
VENDOR_USAGE_PAGE = 0xFF00
POLL_SECONDS = 5


def main() -> int:
    try:
        import hid
    except ImportError:
        print("hidapi is not installed; run: uv sync", file=sys.stderr)
        return 1

    devices = [
        device
        for device in hid.enumerate(VID, PID)
        if device.get("usage_page") == VENDOR_USAGE_PAGE
    ]
    if not devices:
        print("No vendor-defined HID interface found.", file=sys.stderr)
        return 1

    device = devices[0]
    handle = hid.device()
    try:
        handle.open_path(device["path"])
        print(f"Polling MI_02 for {POLL_SECONDS} seconds.")
        end_time = time.monotonic() + POLL_SECONDS
        while time.monotonic() < end_time:
            try:
                report = handle.get_input_report(0, 64)
            except (OSError, ValueError) as error:
                print(f"GET_INPUT_REPORT failed: {error}")
                break

            if report:
                print(bytes(report).hex(" "), flush=True)
            time.sleep(0.05)
    finally:
        handle.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
