"""Convert proposed HID keyboard sequences into stable macropad IDs."""

from __future__ import annotations


VK_F13 = 0x7C
VK_F24 = 0x87
KEY_UP_FLAG = 0x0001

_MODIFIER_BITS = {
    0x11: 0x01,  # VK_CONTROL as reported by this device
    0x10: 0x02,  # VK_SHIFT as reported by this device
    0x12: 0x04,  # VK_MENU / Alt as reported by this device
    0xA2: 0x01,  # VK_LCONTROL
    0xA3: 0x10,  # VK_RCONTROL
    0xA0: 0x02,  # VK_LSHIFT
    0xA1: 0x20,  # VK_RSHIFT
    0xA4: 0x04,  # VK_LMENU / left Alt
    0xA5: 0x40,  # VK_RMENU / right Alt
    0x5B: 0x08,  # VK_LWIN
    0x5C: 0x80,  # VK_RWIN
}


class MacropadEventNormalizer:
    """Track modifier state and emit logical IDs on F13-F24 key-downs."""

    def __init__(self) -> None:
        self._modifiers = 0

    def feed(self, vkey: int, flags: int) -> str | None:
        """Consume one Raw Input keyboard event."""

        modifier_bit = _MODIFIER_BITS.get(vkey, 0)
        is_key_up = bool(flags & KEY_UP_FLAG)

        if modifier_bit:
            if is_key_up:
                self._modifiers &= ~modifier_bit
            else:
                self._modifiers |= modifier_bit
            return None

        if is_key_up or not VK_F13 <= vkey <= VK_F24:
            return None

        f_number = vkey - VK_F13 + 13
        if self._modifiers == 0:
            index = f_number - 13
            return f"R{index // 4 + 1}C{index % 4 + 1}"

        if self._modifiers == 0x07 and 13 <= f_number <= 16:
            return f"R4C{f_number - 12}"

        if self._modifiers == 0x06 and 13 <= f_number <= 21:
            knob_action = f_number - 13
            knob = knob_action // 3 + 1
            action = ("PRESS", "CCW", "CW")[knob_action % 3]
            return f"K{knob}-{action}"

        return None
