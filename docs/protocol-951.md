# MCU-951 protocol notes

These notes describe observations from the tested `0816:2475` device. They
are not a claim that every similar macropad uses the same protocol.

## Vendor interface

The device exposes a vendor-defined HID collection on `MI_02`:

```text
usage page: 0xFF00
usage:      0x0002
input:      64 bytes
output:     64 bytes
features:   none observed
```

The tested configuration path uses report ID zero with a 64-byte payload. The
hidapi buffer therefore contains 65 bytes: a leading report-ID byte followed
by the payload.

## Key layout entries

The configuration command is `0x06`. A single key entry is written with an
internal subcommand `0x10` and contains four values:

```text
type, code1, code2, code3
```

For standard keys (`type = 32`):

```text
code1 = modifier mask
code2 = HID/QMK keycode
code3 = 0
```

The 4x4 grid is stored column-wise. The three knob actions occupy storage
indices 16 through 24.

## Safety

These notes are for the implementation in this repository. Do not send
unreviewed reports or assume that a different device accepts them.
