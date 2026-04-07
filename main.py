"""KnowToClick - Background window activity signaler GUI."""

import tkinter as tk
from tkinter import ttk, messagebox

from clicker import enum_visible_windows, ActivitySignaler


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("KnowToClick")
        self.root.resizable(False, False)

        self.signaler = None
        self.windows = []

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
        ttk.Label(frame_settings, text="(0-1, fraction of interval)").grid(row=1, column=2, columnspan=4, sticky="w", padx=(12, 0), pady=(4, 0))

        # --- Controls ---
        frame_ctrl = ttk.Frame(self.root, padding=8)
        frame_ctrl.pack(padx=10, pady=(4, 10), fill="x")

        self.btn_start = ttk.Button(frame_ctrl, text="Start", command=self._start)
        self.btn_start.pack(side="left", padx=4)

        self.btn_stop = ttk.Button(frame_ctrl, text="Stop", command=self._stop, state="disabled")
        self.btn_stop.pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(frame_ctrl, textvariable=self.status_var).pack(side="right", padx=4)

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

    def _start(self):
        hwnd = self._get_selected_hwnd()
        if hwnd is None:
            return

        if self.signaler and self.signaler.running:
            self.signaler.stop()

        self.signaler = ActivitySignaler(
            hwnd=hwnd,
            interval=self.interval_var.get(),
            x=self.x_var.get(),
            y=self.y_var.get(),
            jitter=self.jitter_var.get(),
        )
        self.signaler.start()

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        title = self.windows[self.window_list.curselection()[0]][1]
        self.status_var.set(f"Running -> {title[:30]}")

    def _stop(self):
        if self.signaler:
            self.signaler.stop()
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.status_var.set("Idle")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
