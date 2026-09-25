"""Read active profile metadata and all 25 stored key entries."""

from __future__ import annotations

import hid


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


def request(device: hid.device, payload: list[int]) -> bytes:
    report = bytes([0, 0x06, *payload, *([0] * (63 - len(payload)))])
    written = device.write(report)
    if written != 65:
        raise RuntimeError(f"short HID write: {written}/65 bytes")
    response = bytes(device.read(64, timeout_ms=1000))
    if len(response) != 64:
        raise RuntimeError(f"short HID response: {len(response)}/64 bytes")
    return response


def main() -> None:
    device = hid.device()
    try:
        path = find_vendor_path()
        device.open_path(path)

        config = request(device, [5])
        print("CONFIG:", config.hex(" "))
        print(f"profile={config[19]} layer={config[21]} layers={config[20]}")

        raw = bytearray()
        for offset in (0, 56):
            response = request(device, [8, 58, offset & 0xFF, offset >> 8, 0, 0])
            print(f"LAYOUT offset={offset}:", response.hex(" "))
            raw.extend(response[8:])

        print("KEY ENTRIES:")
        for index in range(25):
            values = tuple(raw[index * 4:index * 4 + 4])
            print(f"{index:2}: {values}")
    finally:
        device.close()


if __name__ == "__main__":
    main()
