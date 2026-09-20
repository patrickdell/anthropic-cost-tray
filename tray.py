"""System tray spend meter: icon goes green -> yellow -> red as today's spend nears BUDGET.

    $env:ANTHROPIC_ADMIN_KEY="sk-ant-admin..."
    pythonw tray.py          (python tray.py to see errors)
"""
import os
import threading
from datetime import datetime, timezone

import pystray
from PIL import Image, ImageDraw, ImageFont

from cost_report import fetch

BUDGET = float(os.environ.get("BUDGET_USD", 5))
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", 300))

stop = threading.Event()
refresh = threading.Event()


def color(frac):
    frac = max(0.0, min(1.0, frac))
    green, yellow, red = (46, 160, 67), (230, 180, 30), (215, 40, 40)
    a, b, t = (green, yellow, frac * 2) if frac < 0.5 else (yellow, red, frac * 2 - 1)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def short_text(spend):
    """At most 3 chars so it stays legible at 16px: 12 / 4.7 / .05"""
    if spend >= 10:
        return f"{spend:.0f}"
    if spend >= 1:
        return f"{spend:.1f}"
    return f".{min(99, round(spend * 100)):02d}" if spend >= 0.005 else "0"


def make_icon(spend):
    S = 256  # draw big, downscale for smooth edges
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=48, fill=color(spend / BUDGET))
    text = short_text(spend)
    try:
        font = ImageFont.truetype("arialbd.ttf", 200 if len(text) <= 2 else 160)
    except OSError:
        font = ImageFont.load_default()
    d.text((S // 2, S // 2 + 6), text, fill="white", font=font, anchor="mm",
           stroke_width=5, stroke_fill=(0, 0, 0, 200))
    return img.resize((64, 64), Image.LANCZOS)


def poll(icon, key):
    while not stop.is_set():
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            # API rejects a range starting inside the current UTC day, so start a day early
            buckets = sorted(fetch(key, 1), key=lambda b: b["starting_at"])
            # Today's UTC bucket may not exist yet (e.g. just after 00:00 UTC): fall back to the latest day
            b = next((b for b in reversed(buckets) if b["starting_at"][:10] == today), buckets[-1])
            day = b["starting_at"][:10]
            spend = sum(float(r["amount"]) for r in b["results"])  # amounts are USD
            icon.icon = make_icon(spend)
            label = "today" if day == today else f"{day} (no data yet today)"
            icon.title = f"Anthropic {label}: ${spend:.2f} / ${BUDGET:.2f}"
        except Exception as e:
            icon.title = f"Anthropic cost: error - {e}"[:127]
        refresh.wait(POLL_SECONDS)
        refresh.clear()


SERVICE, ACCOUNT = "anthropic-cost-tray", "admin-api-key"
OLD_KEY_FILE = os.path.join(os.environ.get("APPDATA", "."), "anthropic-cost", "key.txt")


def get_key():
    """Env var, else Windows Credential Manager, else ask once with a password box and store it there."""
    import keyring
    key = os.environ.get("ANTHROPIC_ADMIN_KEY")
    if key:
        return key
    key = keyring.get_password(SERVICE, ACCOUNT)
    if key:
        return key
    if os.path.exists(OLD_KEY_FILE):  # migrate from the old plaintext file, then delete it
        key = open(OLD_KEY_FILE).read().strip()
        if key:
            keyring.set_password(SERVICE, ACCOUNT, key)
            os.remove(OLD_KEY_FILE)
            return key
    import tkinter as tk
    from tkinter import simpledialog
    root = tk.Tk()
    root.withdraw()
    key = simpledialog.askstring("Anthropic cost", "Paste your Admin API key:", show="*")
    root.destroy()
    key = key.strip() if key else None
    if key:
        keyring.set_password(SERVICE, ACCOUNT, key)
    return key


def main():
    import ctypes
    # Named mutex, held for process lifetime: one instance only (ERROR_ALREADY_EXISTS = 183)
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "AnthropicCostTray")
    if ctypes.windll.kernel32.GetLastError() == 183:
        raise SystemExit
    key = get_key()
    if not key:
        raise SystemExit
    menu = pystray.Menu(
        pystray.MenuItem("Refresh now", lambda: refresh.set()),
        pystray.MenuItem("Quit", lambda icon: (stop.set(), refresh.set(), icon.stop())),
    )
    icon = pystray.Icon("anthropic-cost", make_icon(0), "Anthropic cost: loading...", menu)
    icon.run(setup=lambda i: (setattr(i, "visible", True),
                              threading.Thread(target=poll, args=(i, key), daemon=True).start()))


if __name__ == "__main__":
    main()
