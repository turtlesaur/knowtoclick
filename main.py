"""KnowToClick - Background window activity signaler GUI."""

import tkinter as tk
from tkinter import ttk, messagebox

import win32api
import win32gui

from clicker import (
    enum_visible_windows,
    get_client_rect,
    screen_to_client,
    ActivitySignaler,
    MIN_INTERVAL,
)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("KnowToClick")
        self.root.resizable(False, False)

        self.signaler = None
        self.windows = []
        self._tracking = False
        self._status_after_id = None

        self._build_ui()
        self._refresh_windows()

    def _build_ui(self):
        # --- Window selection ---
        frame_top = ttk.LabelFrame(self.root, text="Target Window", padding=8)
        frame_top.pack(padx=10, pady=(10, 4), fill="x")

        self.window_list = tk.Listbox(frame_top, height=10, width=60)
        self.window_list.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_top, orient="vertical", command=self.window_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.window_list.config(yscrollcommand=scrollbar.set)

        btn_refresh = ttk.Button(self.root, text="Refresh Windows", command=self._refresh_windows)
        btn_refresh.pack(padx=10, pady=4)

        # --- Settings ---
        frame_settings = ttk.LabelFrame(self.root, text="Settings", padding=8)
        frame_settings.pack(padx=10, pady=4, fill="x")

        ttk.Label(frame_settings, text="Interval (sec):").grid(row=0, column=0, sticky="w")
        self.interval_var = tk.DoubleVar(value=5.0)
        ttk.Entry(frame_settings, textvariable=self.interval_var, width=8).grid(row=0, column=1, padx=4)

        ttk.Label(frame_settings, text="Click X:").grid(row=0, column=2, sticky="w", padx=(12, 0))
        self.x_var = tk.IntVar(value=100)
        ttk.Entry(frame_settings, textvariable=self.x_var, width=6).grid(row=0, column=3, padx=4)

        ttk.Label(frame_settings, text="Click Y:").grid(row=0, column=4, sticky="w", padx=(12, 0))
        self.y_var = tk.IntVar(value=100)
        ttk.Entry(frame_settings, textvariable=self.y_var, width=6).grid(row=0, column=5, padx=4)

        ttk.Label(frame_settings, text="Jitter:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.jitter_var = tk.DoubleVar(value=0.3)
        ttk.Entry(frame_settings, textvariable=self.jitter_var, width=8).grid(row=1, column=1, padx=4, pady=(4, 0))
        ttk.Label(frame_settings, text="(0-1, fraction of interval)").grid(
            row=1, column=2, columnspan=4, sticky="w", padx=(12, 0), pady=(4, 0)
        )

        # --- Coordinate Picker ---
        frame_picker = ttk.LabelFrame(self.root, text="Coordinate Picker", padding=8)
        frame_picker.pack(padx=10, pady=4, fill="x")

        self.btn_pick = ttk.Button(frame_picker, text="Pick Target (3s)", command=self._start_pick)
        self.btn_pick.pack(side="left", padx=4)

        self.pick_label = tk.StringVar(value="Click 'Pick Target' then hover over the spot you want to click.")
        ttk.Label(frame_picker, textvariable=self.pick_label, wraplength=400).pack(side="left", padx=8)

        # --- Mouse Tracker ---
        frame_tracker = ttk.LabelFrame(self.root, text="Live Mouse Tracker", padding=8)
        frame_tracker.pack(padx=10, pady=4, fill="x")

        self.btn_track = ttk.Button(frame_tracker, text="Start Tracking", command=self._toggle_tracking)
        self.btn_track.pack(side="left", padx=4)

        self.tracker_label = tk.StringVar(value="Screen: -  |  Client: -")
        ttk.Label(frame_tracker, textvariable=self.tracker_label, font=("Consolas", 9)).pack(
            side="left", padx=8
        )

        # --- Controls ---
        frame_ctrl = ttk.Frame(self.root, padding=8)
        frame_ctrl.pack(padx=10, pady=(4, 10), fill="x")

        self.btn_start = ttk.Button(frame_ctrl, text="Start", command=self._start)
        self.btn_start.pack(side="left", padx=4)

        self.btn_stop = ttk.Button(frame_ctrl, text="Stop", command=self._stop, state="disabled")
        self.btn_stop.pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(frame_ctrl, textvariable=self.status_var).pack(side="right", padx=4)

    # --- Window list ---

    def _refresh_windows(self):
        self.windows = enum_visible_windows()
        self.window_list.delete(0, tk.END)
        for hwnd, title in self.windows:
            self.window_list.insert(tk.END, f"[{hwnd}]  {title}")

    def _get_selected_hwnd(self):
        selection = self.window_list.curselection()
        if not selection:
            messagebox.showwarning("No selection", "Select a target window first.")
            return None
        return self.windows[selection[0]][0]

    # --- Coordinate Picker (timed snapshot) ---

    def _start_pick(self):
        """Start a 3-second countdown, then capture the cursor position."""
        self.btn_pick.config(state="disabled")
        self._pick_countdown(3)

    def _pick_countdown(self, remaining):
        if remaining > 0:
            self.pick_label.set(f"Hover over target spot... capturing in {remaining}s")
            self.root.after(1000, self._pick_countdown, remaining - 1)
        else:
            self._capture_pick()

    def _capture_pick(self):
        hwnd = self._get_selected_hwnd()
        screen_x, screen_y = win32api.GetCursorPos()

        if hwnd is not None:
            client = screen_to_client(hwnd, screen_x, screen_y)
            if client:
                cx, cy = client
                self.x_var.set(cx)
                self.y_var.set(cy)
                rect = get_client_rect(hwnd)
                size_str = f"{rect[0]}x{rect[1]}" if rect else "?"
                self.pick_label.set(
                    f"Captured: client ({cx}, {cy})  |  screen ({screen_x}, {screen_y})  |  window size: {size_str}"
                )
            else:
                self.pick_label.set(f"Window gone. Screen pos: ({screen_x}, {screen_y})")
        else:
            self.pick_label.set(f"No window selected. Screen pos: ({screen_x}, {screen_y})")

        self.btn_pick.config(state="normal")

    # --- Live Mouse Tracker ---

    def _toggle_tracking(self):
        if self._tracking:
            self._tracking = False
            self.btn_track.config(text="Start Tracking")
            self.tracker_label.set("Screen: -  |  Client: -")
        else:
            self._tracking = True
            self.btn_track.config(text="Stop Tracking")
            self._update_tracker()

    def _update_tracker(self):
        if not self._tracking:
            return

        screen_x, screen_y = win32api.GetCursorPos()
        client_str = "-"

        hwnd = self._get_selected_hwnd_silent()
        if hwnd is not None:
            client = screen_to_client(hwnd, screen_x, screen_y)
            if client:
                client_str = f"({client[0]}, {client[1]})"

        self.tracker_label.set(f"Screen: ({screen_x}, {screen_y})  |  Client: {client_str}")
        self.root.after(50, self._update_tracker)

    def _get_selected_hwnd_silent(self):
        """Like _get_selected_hwnd but returns None without a popup."""
        selection = self.window_list.curselection()
        if not selection:
            return None
        return self.windows[selection[0]][0]

    # --- Start / Stop ---

    def _start(self):
        hwnd = self._get_selected_hwnd()
        if hwnd is None:
            return

        interval = self.interval_var.get()
        if interval < MIN_INTERVAL:
            messagebox.showwarning(
                "Interval too low",
                f"Minimum interval is {MIN_INTERVAL}s to prevent flooding the message queue.",
            )
            return

        if self.signaler and self.signaler.running:
            self.signaler.stop()

        self.signaler = ActivitySignaler(
            hwnd=hwnd,
            interval=interval,
            x=self.x_var.get(),
            y=self.y_var.get(),
            jitter=self.jitter_var.get(),
        )
        self.signaler.start()

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        title = self.windows[self.window_list.curselection()[0]][1]
        self.status_var.set(f"Running -> {title[:30]}")
        self._update_status()

    def _stop(self):
        if self.signaler:
            self.signaler.stop()
        if self._status_after_id:
            self.root.after_cancel(self._status_after_id)
            self._status_after_id = None
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.status_var.set("Idle")

    def _update_status(self):
        """Periodically update the status label with click count."""
        if self.signaler and self.signaler.running:
            title = ""
            selection = self.window_list.curselection()
            if selection:
                title = self.windows[selection[0]][1][:20]
            self.status_var.set(f"Running -> {title}  [{self.signaler.click_count} clicks]")
            self._status_after_id = self.root.after(1000, self._update_status)
        else:
            if self.signaler:
                self.status_var.set(f"Stopped (window closed?) [{self.signaler.click_count} clicks]")
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
