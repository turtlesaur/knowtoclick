"""Background window clicker using Win32 PostMessage."""

import random
import threading
import time

import win32api
import win32con
import win32gui


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


def make_lparam(x, y):
    """Pack x, y coordinates into an LPARAM value."""
    return win32api.MAKELONG(x, y)


def send_background_click(hwnd, x=100, y=100):
    """Send a click (down + up) to a window without focusing it.

    Uses PostMessage so the target window does not need to be in the foreground.
    """
    lparam = make_lparam(x, y)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    # Small delay between down and up to look more natural
    time.sleep(random.uniform(0.03, 0.08))
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


class ActivitySignaler:
    """Periodically sends background clicks to a target window."""

    def __init__(self, hwnd, interval=5.0, x=100, y=100, jitter=0.3):
        """
        Args:
            hwnd: Target window handle.
            interval: Base seconds between clicks.
            x, y: Click coordinates (relative to the window's client area).
            jitter: Fraction of interval to randomize (+/-). 0 = exact timing.
        """
        self.hwnd = hwnd
        self.interval = interval
        self.x = x
        self.y = y
        self.jitter = jitter
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        """Start sending clicks in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the click loop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        while not self._stop_event.is_set():
            if not win32gui.IsWindow(self.hwnd):
                break
            send_background_click(self.hwnd, self.x, self.y)
            # Randomize the wait to feel more natural
            jitter_amount = self.interval * self.jitter
            wait = self.interval + random.uniform(-jitter_amount, jitter_amount)
            self._stop_event.wait(max(0.5, wait))
