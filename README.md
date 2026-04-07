# KnowToClick

A Windows background window activity signaler. Select any open window and send periodic click events to it without needing to focus the window.

## Features

- Browse and select from all open windows
- Send background click events via `PostMessage` (no window focus required)
- Configurable click interval and position
- Simple tkinter GUI with start/stop controls
- Randomized click timing to simulate natural input

## Requirements

- Windows 10/11
- Python 3.9+

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

1. Click **Refresh** to list open windows
2. Select a target window from the list
3. Set the click interval (seconds) and position (x, y)
4. Click **Start** to begin sending background clicks
5. Click **Stop** to stop

## How It Works

Uses the Win32 `PostMessage` API to send `WM_LBUTTONDOWN` / `WM_LBUTTONUP` messages directly to the target window's message queue. This does not require the window to be in the foreground.
