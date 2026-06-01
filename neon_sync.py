"""
NeonSync - Magic Home Screen Color Sync
Syncs your neon sign color to your laptop display in real time.
Usage: python neon_sync.py [--ip 192.168.1.X] [--fps 10] [--region full|left|right|top|bottom]
"""

import argparse
import time
import json
import os
import sys
import socket
import struct
import threading
import http.server
import webbrowser
from collections import deque

try:
    import numpy as np
    from PIL import ImageGrab
except ImportError:
    print("Installing required packages...")
    os.system(f"{sys.executable} -m pip install numpy pillow flux_led")
    import numpy as np
    from PIL import ImageGrab


# ─── Magic Home Protocol (raw TCP, no external dep needed) ───────────────────

class MagicHomeBulb:
    PORT = 5577

    def __init__(self, ip: str, timeout: float = 3.0):
        self.ip = ip
        self.timeout = timeout
        self._sock = None
        self._lock = threading.Lock()

    def connect(self) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((self.ip, self.PORT))
            self._sock = s
            return True
        except Exception as e:
            print(f"[!] Connect failed: {e}")
            return False

    def _send(self, data: bytes):
        try:
            if self._sock is None:
                self.connect()
            self._sock.sendall(data)
        except Exception:
            self._sock = None
            if self.connect():
                self._sock.sendall(data)

    def _checksum(self, data: bytes) -> int:
        return sum(data) & 0xFF

    def turn_on(self):
        msg = bytes([0x71, 0x23, 0x0F])
        msg += bytes([self._checksum(msg)])
        self._send(msg)

    def turn_off(self):
        msg = bytes([0x71, 0x24, 0x0F])
        msg += bytes([self._checksum(msg)])
        self._send(msg)

    def set_rgb(self, r: int, g: int, b: int):
        r, g, b = int(r), int(g), int(b)
        msg = bytes([0x31, r, g, b, 0x00, 0xF0, 0x0F])
        msg += bytes([self._checksum(msg)])
        self._send(msg)

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None


# ─── Auto-discovery ──────────────────────────────────────────────────────────

def discover_devices(timeout: float = 3.0) -> list:
    """Broadcast scan for Magic Home devices on LAN."""
    results = []
    msg = b'\x48\x46\x41\x59\x42\x55\x4C\x42'
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)
    try:
        sock.sendto(msg, ('255.255.255.255', 48899))
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(1024)
                results.append({'ip': addr[0], 'raw': data.decode('utf-8', errors='ignore')})
            except socket.timeout:
                break
    except Exception as e:
        print(f"[!] Discovery error: {e}")
    finally:
        sock.close()
    return results


# ─── Screen Capture & Color Extraction ──────────────────────────────────────

REGIONS = {
    'full':   None,       # full screen
    'left':   'left',
    'right':  'right',
    'top':    'top',
    'bottom': 'bottom',
    'center': 'center',
}

def get_screen_bbox(region: str):
    try:
        from PIL import ImageGrab as _ig
        full = _ig.grab()
        w, h = full.size
    except Exception:
        return None

    if region == 'full' or region is None:
        return None
    elif region == 'left':
        return (0, 0, w // 2, h)
    elif region == 'right':
        return (w // 2, 0, w, h)
    elif region == 'top':
        return (0, 0, w, h // 2)
    elif region == 'bottom':
        return (0, h // 2, w, h)
    elif region == 'center':
        return (w // 4, h // 4, 3 * w // 4, 3 * h // 4)
    return None


def get_average_color(region: str = 'full', sample_size: int = 50):
    bbox = get_screen_bbox(region)
    img = ImageGrab.grab(bbox=bbox, all_screens=False)
    img = img.resize((sample_size, sample_size))
    arr = np.array(img)
    r = int(arr[:, :, 0].mean())
    g = int(arr[:, :, 1].mean())
    b = int(arr[:, :, 2].mean())
    return r, g, b


def smooth_color(history: deque, r: int, g: int, b: int, strength: float = 0.4):
    """Exponential moving average for smooth transitions."""
    if not history:
        history.append((r, g, b))
        return r, g, b
    pr, pg, pb = history[-1]
    sr = int(pr + (r - pr) * strength)
    sg = int(pg + (g - pg) * strength)
    sb = int(pb + (b - pb) * strength)
    history.append((sr, sg, sb))
    return sr, sg, sb


# ─── State (shared with HTTP dashboard) ─────────────────────────────────────

state = {
    "running": False,
    "ip": "",
    "fps": 10,
    "region": "full",
    "smoothing": 0.4,
    "brightness": 1.0,
    "current_rgb": [0, 0, 0],
    "status": "idle",
    "discovered": [],
    "color_locked": False,
}

sync_thread = None
bulb: MagicHomeBulb = None
stop_event = threading.Event()
color_history = deque(maxlen=5)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "neon_sync_config.json")


def save_config():
    cfg = {k: state[k] for k in ["ip", "fps", "region", "smoothing", "brightness"]}
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        state.update({k: cfg[k] for k in cfg if k in state})


def sync_loop():
    global bulb
    bulb = MagicHomeBulb(state["ip"])
    if not bulb.connect():
        state["status"] = "error: could not connect"
        state["running"] = False
        return

    bulb.turn_on()
    state["status"] = "syncing"
    color_history.clear()

    while not stop_event.is_set():
        if state["color_locked"]:
            time.sleep(0.2)
            continue
        try:
            r, g, b = get_average_color(state["region"])
            r, g, b = smooth_color(color_history, r, g, b, state["smoothing"])
            # Apply brightness
            br = state["brightness"]
            r2, g2, b2 = int(r * br), int(g * br), int(b * br)
            bulb.set_rgb(r2, g2, b2)
            state["current_rgb"] = [r2, g2, b2]
        except Exception as e:
            state["status"] = f"error: {e}"
            break

        time.sleep(1.0 / max(1, state["fps"]))

    bulb.close()
    state["status"] = "stopped"
    state["running"] = False


def start_sync():
    global sync_thread
    state["color_locked"] = False  # always clear lock on start
    if state["running"]:
        return
    if not state["ip"]:
        state["status"] = "error: no IP set"
        return
    stop_event.clear()
    state["running"] = True
    state["status"] = "connecting..."
    sync_thread = threading.Thread(target=sync_loop, daemon=True)
    sync_thread.start()
    save_config()


def stop_sync():
    stop_event.set()
    state["running"] = False


# ─── HTTP API for Dashboard ──────────────────────────────────────────────────

class APIHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # silence

    def do_GET(self):
        if self.path == "/api/state":
            self._json(state)
        elif self.path == "/api/discover":
            found = discover_devices()
            state["discovered"] = found
            self._json(found)
        elif self.path == "/api/start":
            start_sync()
            self._json({"ok": True})
        elif self.path == "/api/stop":
            stop_sync()
            self._json({"ok": True})
        elif self.path == "/api/unlock":
            state["color_locked"] = False
            if not state["running"] and state["ip"]:
                start_sync()
            elif state["running"]:
                state["status"] = "syncing"
            self._json({"ok": True})
        elif self.path == "/" or self.path == "/index.html":
            dashboard = os.path.join(os.path.dirname(__file__), "dashboard.html")
            if os.path.exists(dashboard):
                with open(dashboard, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(content)
            else:
                self._json({"error": "dashboard.html not found"})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/config":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            for k in ["ip", "fps", "region", "smoothing", "brightness"]:
                if k in body:
                    state[k] = body[k]
            save_config()
            self._json({"ok": True})
        elif self.path == "/api/color":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            r, g, b = body["r"], body["g"], body["b"]
            # Always try to send, even if sync is stopped
            try:
                global bulb
                if not bulb or not bulb._sock:
                    if state["ip"]:
                        bulb = MagicHomeBulb(state["ip"])
                        bulb.connect()
                        bulb.turn_on()
                bulb.set_rgb(r, g, b)
                state["current_rgb"] = [r, g, b]
                state["color_locked"] = True  # lock screen sync
                state["status"] = "locked"
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        elif self.path == "/api/unlock":
            state["color_locked"] = False
            # restart sync if not already running
            if not state["running"] and state["ip"]:
                start_sync()
            elif state["running"]:
                state["status"] = "syncing"
            self._json({"ok": True})
        else:
            self.send_response(404)
            self.end_headers()

    def _json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NeonSync - Magic Home Screen Sync")
    parser.add_argument("--ip", default="", help="Controller IP address")
    parser.add_argument("--fps", type=int, default=10, help="Updates per second")
    parser.add_argument("--region", default="full", choices=list(REGIONS.keys()))
    parser.add_argument("--port", type=int, default=7878, help="Dashboard HTTP port")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    load_config()
    if args.ip:
        state["ip"] = args.ip
    if args.fps:
        state["fps"] = args.fps
    if args.region:
        state["region"] = args.region

    print(f"""
╔══════════════════════════════════════╗
║        NeonSync  v1.0                ║
║  Magic Home Screen Color Sync        ║
╚══════════════════════════════════════╝
  Dashboard → http://localhost:{args.port}
  Press Ctrl+C to quit
""")

    server = http.server.HTTPServer(("localhost", args.port), APIHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    if not args.no_browser:
        time.sleep(0.5)
        webbrowser.open(f"http://localhost:{args.port}")

    # Auto-start if IP given via CLI
    if state["ip"]:
        start_sync()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
        stop_sync()
        server.shutdown()


if __name__ == "__main__":
    main()