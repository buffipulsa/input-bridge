"""Dry-run bindings for the current macropad experiments.

Values are labels only. They are deliberately not executable commands yet.
"""

DRY_RUN_BINDINGS = {
    "keyboard:vkey=0x6D": "top_left_example",
    "keyboard:vkey=0x6B": "numpad_add_example",
    "keyboard:vkey=0x6F": "numpad_divide_example",
    "keyboard:vkey=0x69": "numpad_9_example",
    "keyboard:vkey=0x66": "numpad_6_example",
    "keyboard:vkey=0x63": "numpad_3_example",
    "keyboard:vkey=0x6E": "numpad_decimal_example",
    "keyboard:vkey=0x68": "numpad_8_example",
    "keyboard:vkey=0x65": "numpad_5_example",
    "keyboard:vkey=0x62": "numpad_2_example",
    "keyboard:vkey=0x60": "numpad_0_example",
    "keyboard:vkey=0x67": "numpad_7_example",
    "keyboard:vkey=0x64": "numpad_4_example",
    "keyboard:vkey=0x61": "numpad_1_example",
    "keyboard:vkey=0x6A": "numpad_multiply_example",
    "keyboard:vkey=0x90": "num_lock_example",
    "consumer:usage=0x00E9": "volume_up_example",
    "consumer:usage=0x00EA": "volume_down_example",
    "consumer:usage=0x00E2": "mute_example",
}

# Host-side logical bindings. These are labels only for now; no commands are
# executed by the observer.
LOGICAL_DRY_RUN_BINDINGS = {
    "R1C1": "example_action_r1c1",
    "R1C2": "example_action_r1c2",
    "R1C3": "example_action_r1c3",
    "R1C4": "example_action_r1c4",
    "R2C1": "example_action_r2c1",
    "R2C2": "example_action_r2c2",
    "R2C3": "example_action_r2c3",
    "R2C4": "example_action_r2c4",
    "R3C1": "example_action_r3c1",
    "R3C2": "example_action_r3c2",
    "R3C3": "example_action_r3c3",
    "R3C4": "example_action_r3c4",
    "R4C1": "example_action_r4c1",
    "R4C2": "example_action_r4c2",
    "R4C3": "example_action_r4c3",
    "R4C4": "example_action_r4c4",
    "K1-PRESS": "example_action_k1_press",
    "K1-CCW": "example_action_k1_ccw",
    "K1-CW": "example_action_k1_cw",
    "K2-PRESS": "example_action_k2_press",
    "K2-CCW": "example_action_k2_ccw",
    "K2-CW": "example_action_k2_cw",
    "K3-PRESS": "example_action_k3_press",
    "K3-CCW": "example_action_k3_ccw",
    "K3-CW": "example_action_k3_cw",
}
