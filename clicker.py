"""Background window clicker with multiple input methods."""

import ctypes
import ctypes.wintypes
import random
import threading
import time

import win32api
import win32con
import win32gui

# PostMessage LPARAM packs x/y into 16 bits each
MAX_COORD = 65535
MIN_INTERVAL = 0.5

# Click method names
METHOD_POST = "PostMessage"
METHOD_SEND = "SendMessage"
METHOD_POST_FULL = "PostMessage (full sequence)"
METHOD_SENDINPUT = "SendInput (focus swap)"

METHODS = [METHOD_SENDINPUT, METHOD_POST_FULL, METHOD_SEND, METHOD_POST]

# --- ctypes structures for SendInput ---

INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_MOVE = 0x0001


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]

    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


def _send_input(*inputs):
    """Call the Windows SendInput API."""
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    ctypes.windll.user32.SendInput(n, arr, ctypes.sizeof(INPUT))


def _make_mouse_input(dx, dy, flags):
    mi = MOUSEINPUT()
    mi.dx = dx
    mi.dy = dy
    mi.mouseData = 0
    mi.dwFlags = flags
    mi.time = 0
    mi.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi = mi
    return inp


# --- Window enumeration helpers ---


def enum_visible_windows():
    """Return a list of (hwnd, title) for all visible windows with titles."""
    results = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                results.append((hwnd, title))
        return True

    win32gui.EnumWindows(callback, None)
    return results


def get_client_rect(hwnd):
    """Return (width, height) of a window's client area, or None if invalid."""
    if not win32gui.IsWindow(hwnd):
        return None
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    return (right - left, bottom - top)


def clamp_to_client_area(hwnd, x, y):
    """Clamp x, y to the window's actual client area bounds."""
    rect = get_client_rect(hwnd)
    if rect is None:
        return (0, 0)
    w, h = rect
    x = max(0, min(x, w - 1)) if w > 0 else 0
    y = max(0, min(y, h - 1)) if h > 0 else 0
    return (x, y)


def screen_to_client(hwnd, screen_x, screen_y):
    """Convert absolute screen coordinates to window-local client coordinates."""
    if not win32gui.IsWindow(hwnd):
        return None
    client_x, client_y = win32gui.ScreenToClient(hwnd, (screen_x, screen_y))
    return (client_x, client_y)


def client_to_screen(hwnd, x, y):
    """Convert window-local client coordinates to absolute screen coordinates."""
    if not win32gui.IsWindow(hwnd):
        return None
    return win32gui.ClientToScreen(hwnd, (x, y))


def make_lparam(x, y):
    """Pack x, y coordinates into an LPARAM value."""
    x = max(0, min(int(x), MAX_COORD))
    y = max(0, min(int(y), MAX_COORD))
    return win32api.MAKELONG(x, y)


def _to_absolute_coords(screen_x, screen_y):
    """Convert screen pixel coordinates to SendInput absolute coordinates (0-65535)."""
    w = ctypes.windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
    h = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
    abs_x = int(screen_x * 65535 / max(w - 1, 1))
    abs_y = int(screen_y * 65535 / max(h - 1, 1))
    return abs_x, abs_y


# --- Click implementations ---


def _click_post(hwnd, x, y):
    """Basic PostMessage click."""
    lparam = make_lparam(x, y)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(random.uniform(0.03, 0.08))
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


def _click_send(hwnd, x, y):
    """SendMessage click - synchronous."""
    lparam = make_lparam(x, y)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(random.uniform(0.03, 0.08))
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


def _click_post_full(hwnd, x, y):
    """Full message sequence via PostMessage."""
    lparam = make_lparam(x, y)
    win32gui.PostMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_CLICKACTIVATE, 0)
    win32gui.PostMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)
    win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
    time.sleep(random.uniform(0.01, 0.03))
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(random.uniform(0.03, 0.08))
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


def _click_sendinput(hwnd, x, y):
    """SendInput with focus swap.

    1. Save the current foreground window and cursor position
    2. Focus the target window
    3. Move cursor to the click point and fire SendInput down+up
    4. Restore the original foreground window and cursor position

    This produces real OS-level input that any engine will pick up.
    """
    # Save current state
    original_hwnd = win32gui.GetForegroundWindow()
    original_cursor = win32api.GetCursorPos()

    # Convert client coords to screen coords, then to absolute (0-65535)
    screen_pos = client_to_screen(hwnd, x, y)
    if screen_pos is None:
        return
    screen_x, screen_y = screen_pos
    abs_x, abs_y = _to_absolute_coords(screen_x, screen_y)

    try:
        # Allow our process to set the foreground window
        ctypes.windll.user32.AllowSetForegroundWindow(ctypes.windll.kernel32.GetCurrentProcessId())

        # Focus the target
        win32gui.SetForegroundWindow(hwnd)
        # Brief pause to let Windows process the focus change
        time.sleep(random.uniform(0.02, 0.05))

        # Move + click via SendInput
        move = _make_mouse_input(abs_x, abs_y, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)
        down = _make_mouse_input(abs_x, abs_y, MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE)
        _send_input(move, down)

        time.sleep(random.uniform(0.03, 0.08))

        up = _make_mouse_input(abs_x, abs_y, MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE)
        _send_input(up)

    finally:
        # Restore original window and cursor
        time.sleep(random.uniform(0.02, 0.04))
        try:
            if win32gui.IsWindow(original_hwnd) and original_hwnd != hwnd:
                win32gui.SetForegroundWindow(original_hwnd)
        except win32gui.error:
            pass
        try:
            win32api.SetCursorPos(original_cursor)
        except win32api.error:
            pass


# Map method name -> function
_METHOD_FUNCS = {
    METHOD_POST: _click_post,
    METHOD_SEND: _click_send,
    METHOD_POST_FULL: _click_post_full,
    METHOD_SENDINPUT: _click_sendinput,
}


def send_background_click(hwnd, x=100, y=100, method=METHOD_SENDINPUT):
    """Send a click to a window using the specified method.

    Returns True if sent successfully, False if the window is gone.
    """
    if not win32gui.IsWindow(hwnd):
        return False

    x, y = clamp_to_client_area(hwnd, x, y)
    func = _METHOD_FUNCS.get(method, _click_sendinput)

    try:
        func(hwnd, x, y)
    except (win32gui.error, OSError):
        return False

    return True


class ActivitySignaler:
    """Periodically sends background clicks to a target window."""

    def __init__(self, hwnd, interval=5.0, x=100, y=100, jitter=0.3,
                 method=METHOD_SENDINPUT):
        self.hwnd = hwnd
        self.interval = max(MIN_INTERVAL, float(interval))
        self.x = int(x)
        self.y = int(y)
        self.jitter = max(0.0, min(1.0, float(jitter)))
        self.method = method
        self._stop_event = threading.Event()
        self._thread = None
        self._click_count = 0

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._click_count = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def click_count(self):
        return self._click_count

    def _run(self):
        while not self._stop_event.is_set():
            if not send_background_click(self.hwnd, self.x, self.y, self.method):
                break
            self._click_count += 1
            jitter_amount = self.interval * self.jitter
            wait = self.interval + random.uniform(-jitter_amount, jitter_amount)
            self._stop_event.wait(max(MIN_INTERVAL, wait))
