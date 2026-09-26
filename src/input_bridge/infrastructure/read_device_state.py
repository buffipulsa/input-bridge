"""Inspect vendor-interface metadata without communicating with the device.

The vendor protocol for reading persistent state has not been verified. This
module intentionally uses only hid.enumerate and never opens a HID handle or
sends an input, output, or feature report.
"""

from __future__ import annotations

import hid

VID = 0x0816
PID = 0x2475
VENDOR_USAGE_PAGE = 0xFF00
VENDOR_USAGE = 0x0002


def find_vendor_devices() -> list[dict[str, object]]:
    """Return matching vendor-defined HID interface metadata."""

    return [
        item
        for item in hid.enumerate(VID, PID)
        if item.get("interface_number") == 2
        and item.get("usage_page") == VENDOR_USAGE_PAGE
        and item.get("usage") == VENDOR_USAGE
    ]


def main() -> None:
    """Print vendor-interface metadata without sending device commands."""

    matches = find_vendor_devices()
    print(f"Read-only vendor interface inspection for {VID:04X}:{PID:04X}")
    if not matches:
        print("No matching MI_02 vendor interface found.")
        return

    for index, device in enumerate(matches, start=1):
        print(f"[{index}]")
        for field in (
            "path",
            "interface_number",
            "usage_page",
            "usage",
            "manufacturer_string",
            "product_string",
            "serial_number",
            "max_input_report_size",
            "max_output_report_size",
            "max_feature_report_size",
        ):
            print(f"  {field}: {device.get(field, '<not reported>')}")

    print(
        "Persistent device state was not requested because the vendor "
        "read protocol is unverified."
    )


if __name__ == "__main__":
    main()
