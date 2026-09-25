"""Print one offline MCU-951 key-mapping report for review."""

from .protocol951 import build_set_key_info_report, describe_report


def main() -> None:
    # R1C1 is profile index 0.  F13 is a candidate neutral host event;
    # this script only constructs the report and never communicates with
    # the macropad.
    report = build_set_key_info_report(
        0,
        key_type=32,  # configurator's Standard key type
        code1=0,       # no modifiers
        code2=0x68,    # USB HID usage for F13
    )
    print("CANDIDATE ONLY: R1C1 -> F13")
    print(describe_report(report))
    print("hex:", report.hex(" "))


if __name__ == "__main__":
    main()
