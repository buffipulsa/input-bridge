"""Correct and write the explicitly approved MCU-951 key mapping.

This is intentionally narrow: it targets only the vendor-defined MI_02
interface, restores the accidentally targeted R4C1 entry, and writes the
approved R1C1 mapping. It does not flash firmware or send feature reports.
"""

from __future__ import annotations

import hid

from protocol951 import build_set_key_info_report


VID = 0x0816
PID = 0x2475
VENDOR_USAGE_PAGE = 0xFF00
VENDOR_USAGE = 0x0002


def find_vendor_path() -> str:
    matches = [
        item
        for item in hid.enumerate(VID, PID)
        if item.get("interface_number") == 2
        and item.get("usage_page") == VENDOR_USAGE_PAGE
        and item.get("usage") == VENDOR_USAGE
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one MI_02 vendor interface, found {len(matches)}")
    return matches[0]["path"]


def main() -> None:
    path = find_vendor_path()
    restore_r4c1 = build_set_key_info_report(
        0, key_type=32, code1=0, code2=0x5F, code3=0
    )
    set_r1c1 = build_set_key_info_report(
        3, key_type=32, code1=0, code2=0x68, code3=0
    )

    print("Target:", path)
    print("Action 1: restore R4C1 -> P7")
    print("Action 2: set R1C1 -> F13")

    device = hid.device()
    try:
        device.open_path(path)
        for label, report in (("R4C1 restore", restore_r4c1), ("R1C1 test", set_r1c1)):
            print(f"{label} report: {report.hex(' ')}")
            written = device.write(report)
            if written != len(report):
                raise RuntimeError(f"short HID write: {written}/{len(report)} bytes")
            print(f"{label}: wrote {written} bytes.")
    finally:
        device.close()


if __name__ == "__main__":
    main()
