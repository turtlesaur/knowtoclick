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

METHODS = [METHOD_POST, METHOD_SEND, METHOD_POST_FULL]


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


def make_lparam(x, y):
    """Pack x, y coordinates into an LPARAM value."""
    x = max(0, min(int(x), MAX_COORD))
    y = max(0, min(int(y), MAX_COORD))
    return win32api.MAKELONG(x, y)


def _click_post(hwnd, x, y):
    """Basic PostMessage click - just down + up."""
    lparam = make_lparam(x, y)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(random.uniform(0.03, 0.08))
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


def _click_send(hwnd, x, y):
    """SendMessage click - synchronous, blocks until the window processes it."""
    lparam = make_lparam(x, y)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(random.uniform(0.03, 0.08))
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


def _click_post_full(hwnd, x, y):
    """Full message sequence via PostMessage.

    Sends activation, focus, mouse move, then click. This mimics what Windows
    actually delivers when a real user clicks inside a window. Many game
    frameworks need these preceding messages to register the click.
    """
    lparam = make_lparam(x, y)

    # Activate the window's message processing without actually bringing it
    # to the foreground (WA_CLICKACTIVATE tells the app "a click caused this")
    win32gui.PostMessage(
        hwnd, win32con.WM_ACTIVATE,
        win32con.WA_CLICKACTIVATE, 0,
    )
    win32gui.PostMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)

    # Move the "mouse" to the target position first
    win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
    time.sleep(random.uniform(0.01, 0.03))

    # Click
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(random.uniform(0.03, 0.08))
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


# Map method name -> function
_METHOD_FUNCS = {
    METHOD_POST: _click_post,
    METHOD_SEND: _click_send,
    METHOD_POST_FULL: _click_post_full,
}


def send_background_click(hwnd, x=100, y=100, method=METHOD_POST):
    """Send a click to a window using the specified method.

    Returns True if sent successfully, False if the window is gone.
    """
    if not win32gui.IsWindow(hwnd):
        return False

    x, y = clamp_to_client_area(hwnd, x, y)
    func = _METHOD_FUNCS.get(method, _click_post)

    try:
        func(hwnd, x, y)
    except win32gui.error:
        return False

    return True


class ActivitySignaler:
    """Periodically sends background clicks to a target window."""

    def __init__(self, hwnd, interval=5.0, x=100, y=100, jitter=0.3,
                 method=METHOD_POST):
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
