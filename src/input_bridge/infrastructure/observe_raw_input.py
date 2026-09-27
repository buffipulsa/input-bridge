"""Observe this macropad through Windows Raw Input.

This uses only the Windows Raw Input API through ctypes. It does not open a
HID handle and does not send USB, output, or feature reports.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import struct
import subprocess
import sys
import threading
from ctypes import wintypes
from pathlib import Path

from ..application.actions import execute_action, execute_profile_action
from ..application.bindings import DRY_RUN_BINDINGS, LOGICAL_DRY_RUN_BINDINGS
from ..application.runtime import InputEventSource, LogicalInputEvent
from ..domain.event_normalizer import MacropadEventNormalizer
from ..domain.profiles import ProfileDocument, load_profile

VID_PID = "VID_0816&PID_2475"
DEFAULT_OBSERVATION_SECONDS = 5

KEY_NAMES = {
    0x08: "backspace",
    0x09: "tab",
    0x0D: "enter",
    0x1B: "escape",
    0x20: "space",
    0x6B: "numpad_add",
    0x6F: "numpad_divide",
    0x6D: "numpad_subtract",
    0x69: "numpad_9",
    0x66: "numpad_6",
    0x63: "numpad_3",
    0x6E: "numpad_decimal",
    0x68: "numpad_8",
    0x65: "numpad_5",
    0x62: "numpad_2",
    0x60: "numpad_0",
    0x67: "numpad_7",
    0x64: "numpad_4",
    0x61: "numpad_1",
    0x6A: "numpad_multiply",
    0x90: "num_lock",
}

CONSUMER_NAMES = {
    0x00: "release",
    0xE2: "mute",
    0xE9: "volume_increment",
    0xEA: "volume_decrement",
}

CAPTURED_EVENTS: list[str] = []

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.DefWindowProcW.restype = ctypes.c_ssize_t

WM_INPUT = 0x00FF
WM_TIMER = 0x0113
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
RID_INPUT = 0x10000003
RIDI_DEVICENAME = 0x20000007
RIM_TYPEKEYBOARD = 1
RIM_TYPEHID = 2
RIM_TYPEMOUSE = 0
RIDEV_INPUTSINK = 0x00000100


class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [
        ("hDevice", wintypes.HANDLE),
        ("dwType", wintypes.DWORD),
    ]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [
        ("MakeCode", wintypes.USHORT),
        ("Flags", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("VKey", wintypes.USHORT),
        ("Message", wintypes.UINT),
        ("ExtraInformation", wintypes.ULONG),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


user32.GetRawInputDeviceList.argtypes = [
    ctypes.POINTER(RAWINPUTDEVICELIST),
    ctypes.POINTER(wintypes.UINT),
    wintypes.UINT,
]
user32.GetRawInputDeviceList.restype = wintypes.UINT
user32.GetRawInputDeviceInfoW.argtypes = [
    wintypes.HANDLE,
    wintypes.UINT,
    wintypes.LPVOID,
    ctypes.POINTER(wintypes.UINT),
]
user32.GetRawInputDeviceInfoW.restype = ctypes.c_int


def device_name(handle: wintypes.HANDLE) -> str:
    # Windows returns zero for the null-buffer size query for some HID
    # collections, so use a fixed buffer for the device interface path.
    buffer = ctypes.create_unicode_buffer(1024)
    character_count = wintypes.UINT(len(buffer))
    result = user32.GetRawInputDeviceInfoW(
        handle, RIDI_DEVICENAME, buffer, ctypes.byref(character_count)
    )
    if result < 0:
        return "<unknown device>"
    return buffer.value


def raw_input_bytes(window: wintypes.HWND, lparam: wintypes.LPARAM) -> bytes:
    size = wintypes.UINT(0)
    user32.GetRawInputData(
        lparam, RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER)
    )
    buffer = (ctypes.c_ubyte * size.value)()
    result = user32.GetRawInputData(
        lparam,
        RID_INPUT,
        buffer,
        ctypes.byref(size),
        ctypes.sizeof(RAWINPUTHEADER),
    )
    if result == 0xFFFFFFFF:
        return b""
    return bytes(buffer[:result])


def matching_raw_devices() -> list[tuple[int, str]]:
    count = wintypes.UINT(0)
    entry_size = ctypes.sizeof(RAWINPUTDEVICELIST)
    result = user32.GetRawInputDeviceList(None, ctypes.byref(count), entry_size)
    if result == 0xFFFFFFFF:
        raise ctypes.WinError(ctypes.get_last_error())

    devices = (RAWINPUTDEVICELIST * count.value)()
    result = user32.GetRawInputDeviceList(
        devices, ctypes.byref(count), entry_size
    )
    if result == 0xFFFFFFFF:
        raise ctypes.WinError(ctypes.get_last_error())

    matches = []
    print(f"Windows Raw Input device count: {result}")
    for device in devices[:result]:
        name = device_name(device.hDevice)
        if name != "<unknown device>":
            print(f"  discovered type={device.dwType} path={name}")
        if VID_PID in name.upper():
            matches.append((device.dwType, name))
    return matches


def normalized_keyboard_event(keyboard: RAWKEYBOARD) -> str:
    state = "key_up" if keyboard.Flags & 0x0001 else "key_down"
    name = KEY_NAMES.get(keyboard.VKey, f"vkey_0x{keyboard.VKey:02X}")
    return f"EVENT {state} {name} vkey=0x{keyboard.VKey:02X}"


def dry_run_keyboard_binding(keyboard: RAWKEYBOARD) -> None:
    if keyboard.Flags & 0x0001:
        return
    event_key = f"keyboard:vkey=0x{keyboard.VKey:02X}"
    CAPTURED_EVENTS.append(event_key)
    action = DRY_RUN_BINDINGS.get(event_key)
    if action:
        print(f"DRY RUN {event_key} -> {action}", flush=True)


def normalized_hid_event(payload: bytes, path: str) -> str:
    # RAWHID contains dwSizeHid and dwCount before the actual HID reports.
    if len(payload) < 8:
        return f"EVENT hid_unparsed path={path} data={payload.hex(' ')}"

    report_size, report_count = struct.unpack_from("<II", payload)
    reports = payload[8:]
    if report_count != 1 or report_size == 0 or len(reports) < report_size:
        return f"EVENT hid_unparsed path={path} data={payload.hex(' ')}"

    report = reports[:report_size]
    if "&COL03#" in path.upper() and len(report) >= 3:
        usage = int.from_bytes(report[1:3], "little")
        name = CONSUMER_NAMES.get(usage, f"usage_0x{usage:04X}")
        return f"EVENT consumer {name} usage=0x{usage:04X}"

    return f"EVENT hid_report id=0x{report[0]:02X} data={report.hex(' ')}"


def dry_run_hid_binding(payload: bytes, path: str) -> None:
    if len(payload) < 11 or "&COL03#" not in path.upper():
        return

    report_size, report_count = struct.unpack_from("<II", payload)
    if report_count != 1 or report_size < 3:
        return

    report = payload[8:8 + report_size]
    usage = int.from_bytes(report[1:3], "little")
    event_key = f"consumer:usage=0x{usage:04X}"
    if usage != 0:
        CAPTURED_EVENTS.append(event_key)
    action = DRY_RUN_BINDINGS.get(event_key)
    if action and usage != 0:
        print(f"DRY RUN {event_key} -> {action}", flush=True)


class RawInputEventSource(InputEventSource):
    """Read recognized macropad keyboard events through Windows Raw Input.

    The source listens only to the standard keyboard usage and filters events
    by the known macropad VID/PID path. It does not open HID handles or send
    USB, output, or feature reports. Consumer-control knob events remain
    unsupported here until their physical mapping is confirmed.
    """

    def __init__(self, vid_pid: str = VID_PID) -> None:
        self.vid_pid = vid_pid
        self._on_event = None
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._hwnd: wintypes.HWND | None = None
        self._ready = threading.Event()
        self._error: BaseException | None = None

    def start(self, on_event) -> None:
        """Start the Raw Input message loop on a background thread."""

        if sys.platform != "win32":
            raise RuntimeError("Windows Raw Input requires Windows")
        if self._thread is not None and self._thread.is_alive():
            return

        self._on_event = on_event
        self._ready.clear()
        self._error = None
        self._thread = threading.Thread(
            target=self._run,
            name="input-bridge-raw-input",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=2):
            raise RuntimeError("Raw Input source did not start in time")
        if self._error is not None:
            raise RuntimeError(f"Raw Input source failed: {self._error}") from self._error

    def stop(self) -> None:
        """Stop the Raw Input message loop."""

        if self._thread is None:
            return
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
        self._thread.join(timeout=2)
        if self._thread.is_alive():
            raise RuntimeError("Raw Input source did not stop in time")
        self._thread = None
        self._thread_id = None
        self._hwnd = None
        self._on_event = None

    def _run(self) -> None:
        callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        normalizer = MacropadEventNormalizer()

        @callback_type
        def window_proc(hwnd, message, _wparam, lparam):
            if message == WM_INPUT:
                data = raw_input_bytes(hwnd, lparam)
                if len(data) >= ctypes.sizeof(RAWINPUTHEADER):
                    header = RAWINPUTHEADER.from_buffer_copy(data)
                    name = device_name(header.hDevice)
                    if VID_PID in name.upper() and header.dwType == RIM_TYPEKEYBOARD:
                        payload = data[ctypes.sizeof(RAWINPUTHEADER):]
                        keyboard = RAWKEYBOARD.from_buffer_copy(payload)
                        logical_event = normalizer.feed(
                            keyboard.VKey,
                            keyboard.Flags,
                        )
                        if logical_event and self._on_event is not None:
                            self._on_event(
                                LogicalInputEvent(control=logical_event)
                            )
            elif message == WM_CLOSE:
                user32.DestroyWindow(hwnd)
            elif message == WM_DESTROY:
                user32.PostQuitMessage(0)
            return user32.DefWindowProcW(hwnd, message, _wparam, lparam)

        try:
            self._thread_id = threading.get_native_id()
            class_name = f"InputBridgeRawInputSource{self._thread_id}"
            instance = kernel32.GetModuleHandleW(None)
            window_class = WNDCLASSW()
            window_class.lpfnWndProc = window_proc
            window_class.hInstance = instance
            window_class.lpszClassName = class_name
            if not user32.RegisterClassW(ctypes.byref(window_class)):
                error = ctypes.get_last_error()
                if error != 1410:
                    raise ctypes.WinError(error)

            hwnd = user32.CreateWindowExW(
                0,
                class_name,
                class_name,
                0,
                0,
                0,
                0,
                0,
                None,
                None,
                instance,
                None,
            )
            if not hwnd:
                raise ctypes.WinError(ctypes.get_last_error())
            self._hwnd = hwnd

            registration = RAWINPUTDEVICE(
                0x01,
                0x06,
                RIDEV_INPUTSINK,
                hwnd,
            )
            if not user32.RegisterRawInputDevices(
                ctypes.byref(registration),
                1,
                ctypes.sizeof(RAWINPUTDEVICE),
            ):
                raise ctypes.WinError(ctypes.get_last_error())

            self._ready.set()
            message = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
        except (OSError, RuntimeError, ctypes.ArgumentError) as error:
            self._error = error
            self._ready.set()


def main() -> int:
    if sys.platform != "win32":
        print("This observer requires Windows.", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description="Observe and catalog one macropad control.")
    parser.add_argument(
        "label",
        nargs="*",
        help="label for the control being tested",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=DEFAULT_OBSERVATION_SECONDS,
        help=f"observation duration (default: {DEFAULT_OBSERVATION_SECONDS})",
    )
    parser.add_argument(
        "--execute-actions",
        action="store_true",
        help="execute configured host actions instead of only printing dry-run output",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        help="profile JSON to use for opt-in script actions",
    )
    args = parser.parse_args()
    observation_ms = max(0.1, args.seconds) * 1000
    event_normalizer = MacropadEventNormalizer()

    label = " ".join(args.label).strip() or input("Control label: ").strip()
    if not label:
        label = "unlabeled"

    profile: ProfileDocument | None = None
    if args.profile is not None:
        try:
            profile = load_profile(args.profile)
        except (OSError, TypeError, ValueError) as error:
            print(f"Could not load profile: {error}", file=sys.stderr)
            return 2

    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )

    @callback_type
    def window_proc(hwnd, message, wparam, lparam):
        if message == WM_INPUT:
            data = raw_input_bytes(hwnd, lparam)
            if len(data) >= ctypes.sizeof(RAWINPUTHEADER):
                header = RAWINPUTHEADER.from_buffer_copy(data)
                name = device_name(header.hDevice)
                if VID_PID in name.upper():
                    payload = data[ctypes.sizeof(RAWINPUTHEADER):]
                    if header.dwType == RIM_TYPEKEYBOARD:
                        keyboard = RAWKEYBOARD.from_buffer_copy(payload)
                        dry_run_keyboard_binding(keyboard)
                        logical_event = event_normalizer.feed(
                            keyboard.VKey, keyboard.Flags
                        )
                        if logical_event:
                            print(f"LOGICAL {logical_event}", flush=True)
                            action = LOGICAL_DRY_RUN_BINDINGS.get(logical_event)
                            if action:
                                mode = "DRY RUN" if not args.execute_actions else "CONFIGURED"
                                print(
                                    f"{mode} logical:{logical_event} -> {action}",
                                    flush=True,
                                )
                            if args.execute_actions:
                                try:
                                    if profile is None:
                                        execute_action(logical_event)
                                    else:
                                        execute_profile_action(logical_event, profile)
                                except (
                                    LookupError,
                                    OSError,
                                    RuntimeError,
                                    subprocess.CalledProcessError,
                                ) as error:
                                    print(
                                        f"ACTION failed logical:{logical_event}: {error}",
                                        flush=True,
                                    )
                                else:
                                    print(
                                        f"ACTION executed logical:{logical_event}",
                                        flush=True,
                                    )
                        print(normalized_keyboard_event(keyboard), flush=True)
                        print(
                            f"KEYBOARD path={name} "
                            f"vkey=0x{keyboard.VKey:02X} "
                            f"make=0x{keyboard.MakeCode:02X} "
                            f"flags=0x{keyboard.Flags:04X} "
                            f"message=0x{keyboard.Message:04X}",
                            flush=True,
                        )
                    elif header.dwType in (RIM_TYPEMOUSE, RIM_TYPEHID):
                        if header.dwType == RIM_TYPEHID:
                            dry_run_hid_binding(payload, name)
                            print(normalized_hid_event(payload, name), flush=True)
                        print(
                            f"RAW type={header.dwType} path={name} "
                            f"data={payload.hex(' ')}",
                            flush=True,
                        )

        elif message == WM_TIMER:
            user32.DestroyWindow(hwnd)
        elif message == WM_DESTROY:
            user32.PostQuitMessage(0)

        return user32.DefWindowProcW(hwnd, message, wparam, lparam)

    class_name = "InputBridgeRawInputObserver"
    instance = kernel32.GetModuleHandleW(None)
    window_class = WNDCLASSW()
    window_class.lpfnWndProc = window_proc
    window_class.hInstance = instance
    window_class.lpszClassName = class_name
    if not user32.RegisterClassW(ctypes.byref(window_class)):
        error = ctypes.get_last_error()
        if error != 1410:  # ERROR_CLASS_ALREADY_EXISTS
            raise ctypes.WinError(error)

    hwnd = user32.CreateWindowExW(
        0,
        class_name,
        class_name,
        0,
        0,
        0,
        0,
        0,
        None,
        None,
        instance,
        None,
    )
    if not hwnd:
        raise ctypes.WinError(ctypes.get_last_error())

    print("Matching Windows Raw Input devices:")
    for device_type, name in matching_raw_devices():
        print(f"  type={device_type} path={name}")

    registrations = (RAWINPUTDEVICE * 5)(
        RAWINPUTDEVICE(0x01, 0x06, RIDEV_INPUTSINK, hwnd),
        RAWINPUTDEVICE(0x0C, 0x01, RIDEV_INPUTSINK, hwnd),
        RAWINPUTDEVICE(0x01, 0x02, RIDEV_INPUTSINK, hwnd),
        RAWINPUTDEVICE(0x01, 0x0C, RIDEV_INPUTSINK, hwnd),
        RAWINPUTDEVICE(0xFF00, 0x02, RIDEV_INPUTSINK, hwnd),
    )
    if not user32.RegisterRawInputDevices(
        registrations, len(registrations), ctypes.sizeof(RAWINPUTDEVICE)
    ):
        raise ctypes.WinError(ctypes.get_last_error())

    print(
        f"Listening for {observation_ms / 1000:g} seconds for "
        f"Raw Input from {VID_PID}. Press keys and turn encoders.",
        flush=True,
    )
    user32.SetTimer(hwnd, 1, int(observation_ms), None)

    message = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(message))
        user32.DispatchMessageW(ctypes.byref(message))

    print(
        "CATALOG "
        + json.dumps(
            {"label": label, "events": CAPTURED_EVENTS}, separators=(",", ":")
        ),
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
