"""Read-only HID discovery for the target macropad.

This script enumerates HID collections and retrieves their report descriptors.
It does not read input reports or send output/feature reports.
"""

from __future__ import annotations

import sys

VENDOR_ID = 0x0816
PRODUCT_ID = 0x2475


def display(value: object) -> str:
    """Format a descriptor value for the inspection report.

    Parameters
    ----------
    value : object
        A value returned by hidapi, possibly ``None``, an empty string, or
        bytes.

    Returns
    -------
    str
        A printable value, using ``<not reported>`` for missing values.
    """

    if value is None or value == "":
        return "<not reported>"
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value)


def main() -> int:
    try:
        import hid  # Provided by the hidapi package.
    except ImportError:
        print(
            "hidapi is not installed. Activate the project virtual environment "
            "and run: uv sync",
            file=sys.stderr,
        )
        return 1

    devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)

    print(f"Matching HID devices for VID:PID {VENDOR_ID:04X}:{PRODUCT_ID:04X}")
    print(f"Found {len(devices)} interface(s).")

    for index, device in enumerate(devices, start=1):
        print(f"\n[{index}]")
        print(f"  path:         {display(device.get('path'))}")
        print(f"  interface:    {display(device.get('interface_number'))}")
        print(f"  usage page:   {display(device.get('usage_page'))}")
        print(f"  usage:        {display(device.get('usage'))}")
        print(f"  manufacturer: {display(device.get('manufacturer_string'))}")
        print(f"  product:      {display(device.get('product_string'))}")
        print(f"  serial:       {display(device.get('serial_number'))}")
        print(f"  max input report:    {display(device.get('max_input_report_size'))}")
        print(f"  max output report:   {display(device.get('max_output_report_size'))}")
        print(f"  max feature report:  {display(device.get('max_feature_report_size'))}")

        handle = hid.device()
        try:
            handle.open_path(device["path"])
            descriptor = bytes(handle.get_report_descriptor())
        except (OSError, ValueError) as error:
            print(f"  report descriptor:   <unavailable: {error}>")
        else:
            print(f"  report descriptor:   {len(descriptor)} bytes")
            print(f"  descriptor bytes:    {descriptor.hex(' ')}")
        finally:
            handle.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
