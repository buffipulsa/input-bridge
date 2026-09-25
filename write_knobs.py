"""Write the approved neutral mapping for the three encoder actions."""

from __future__ import annotations

import hid

from protocol951 import build_set_key_info_report


VID = 0x0816
PID = 0x2475
VENDOR_USAGE_PAGE = 0xFF00
VENDOR_USAGE = 0x0002


def find_vendor_path() -> str:
    matches = [
        item for item in hid.enumerate(VID, PID)
        if item.get("interface_number") == 2
        and item.get("usage_page") == VENDOR_USAGE_PAGE
        and item.get("usage") == VENDOR_USAGE
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one MI_02 vendor interface, found {len(matches)}")
    return matches[0]["path"]


def main() -> None:
    path = find_vendor_path()
    device = hid.device()
    try:
        device.open_path(path)
        for action_index in range(9):
            storage_index = 16 + action_index
            knob = action_index // 3 + 1
            action = ("PRESS", "CCW", "CW")[action_index % 3]
            keycode = 0x68 + action_index  # F13 through F21
            report = build_set_key_info_report(
                storage_index,
                key_type=32,
                code1=0x06,  # Left Alt + Left Shift
                code2=keycode,
                code3=0,
            )
            written = device.write(report)
            if written != len(report):
                raise RuntimeError(f"short write for K{knob}-{action}: {written}/65")
            response = device.read(64, timeout_ms=1000)
            if len(response) != 64:
                raise RuntimeError(
                    f"missing response for K{knob}-{action}: {len(response)}/64 bytes"
                )
            print(
                f"K{knob}-{action}: storage_index={storage_index} "
                f"modifiers=0x06 keycode=0x{keycode:02X} "
                f"wrote={written} response={bytes(response[:4]).hex(' ')}"
            )
    finally:
        device.close()


if __name__ == "__main__":
    main()
