"""Write the approved neutral mapping for the 4x4 button grid only."""

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


def grid_entry(logical_index: int) -> tuple[str, int, int, int]:
    row, column = divmod(logical_index, 4)
    control = f"R{row + 1}C{column + 1}"
    storage_index = 4 * column + (3 - row)
    modifiers = 0x07 if row == 3 else 0
    keycode = 0x68 + logical_index if logical_index < 12 else 0x68 + (logical_index - 12)
    return control, storage_index, modifiers, keycode


def main() -> None:
    path = find_vendor_path()
    device = hid.device()
    try:
        device.open_path(path)
        for logical_index in range(16):
            control, storage_index, modifiers, keycode = grid_entry(logical_index)
            report = build_set_key_info_report(
                storage_index,
                key_type=32,
                code1=modifiers,
                code2=keycode,
                code3=0,
            )
            written = device.write(report)
            if written != len(report):
                raise RuntimeError(f"short write for {control}: {written}/65")
            response = device.read(64, timeout_ms=1000)
            if len(response) != 64:
                raise RuntimeError(
                    f"missing response for {control}: {len(response)}/64 bytes"
                )
            print(
                f"{control}: storage_index={storage_index} "
                f"modifiers=0x{modifiers:02X} keycode=0x{keycode:02X} "
                f"wrote={written} response={bytes(response[:4]).hex(' ')}"
            )
    finally:
        device.close()


if __name__ == "__main__":
    main()
