"""Read one key-layout block through the documented MCU-951 command."""

from __future__ import annotations

import hid

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
    # This is the configurator's get-key-layout request for offset 0,
    # layer 0: command 0x06, subcommand 0x08, length 58.
    payload = bytearray(63)
    payload[0] = 0x08
    payload[1] = 58
    payload[2] = 0
    payload[3] = 0
    payload[5] = 0
    report = bytes([0, 0x06]) + bytes(payload)

    device = hid.device()
    try:
        path = find_vendor_path()
        print("Target:", path)
        print("Read request:", report.hex(" "))
        device.open_path(path)
        written = device.write(report)
        print(f"Request wrote {written} bytes.")
        response = device.read(64, timeout_ms=1000)
        print(f"Response length: {len(response)} bytes")
        print("Response:", bytes(response).hex(" "))
    finally:
        device.close()


if __name__ == "__main__":
    main()
