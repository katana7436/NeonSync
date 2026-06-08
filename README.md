<div align="center">
    # 🌈 NeonSync

    
<img width="1365" height="767" alt="image" src="https://github.com/user-attachments/assets/41ab5e5a-6a8a-4dc7-bf8f-6ca05c6f02b3" />

# 🌈 NeonSync

**Real-time Magic Home neon sign ↔ laptop screen color sync**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat)](https://github.com)
[![Protocol](https://img.shields.io/badge/Protocol-Magic%20Home%20TCP-ff2d78?style=flat)](https://github.com)
[![License](https://img.shields.io/badge/License-MIT-00ffcc?style=flat)](LICENSE)

*Turn your neon sign into an ambient light that reacts to everything on your screen — movies, games, music visualizers, anything.*

</div>

---

## ✨ Features

- 🎨 **Real-time screen sync** — samples your display and sends colors to your sign at up to 30fps
- 🔒 **Color lock** — freeze the sign on any color with one click, then resume screen sync instantly
- 🎛 **Live dashboard** — beautiful browser UI with color history, RGB bars, and manual controls
- 🔍 **Auto-discovery** — scans your network for Magic Home controllers automatically
- 🌈 **12 color presets** — one-click neon colors for instant vibes
- ⚡ **No cloud** — communicates directly over local TCP, no internet required
- 💾 **Persistent config** — remembers your IP, FPS, region, and brightness between sessions

---

## 📸 Preview

> Dashboard running at `localhost:7878`

| Live Sync | Color Lock | History Wave |
|-----------|------------|--------------|
| Orb reflects real-time screen color | Lock to any color with one click | Scrolling color history visualization |

---

## 🚀 Quick Start

### Requirements
- Python 3.8+
- A [Magic Home](https://play.google.com/store/apps/details?id=com.zengge.hao) compatible WiFi LED controller
- Your laptop and controller on the **same WiFi network**

### Install & Run

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/NeonSync.git
cd NeonSync

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch
python neon_sync.py
```

The dashboard opens automatically at **http://localhost:7878**

---

## 🎮 Usage

### Finding your controller IP
1. Click **Scan** in the dashboard to auto-discover devices
2. Or open the **Fing** app on your phone and look for a device named `LEDnet`, `LEDENET`, or similar
3. Or run this in terminal:
```bash
python -c "
import socket
subnet = '192.168.1'  # change to match your network
for i in range(1, 255):
    s = socket.socket()
    s.settimeout(0.5)
    if s.connect_ex((f'{subnet}.{i}', 5577)) == 0:
        print(f'Found: {subnet}.{i}')
    s.close()
"
```

### Dashboard controls

| Control | Description |
|---------|-------------|
| **Scan** | Auto-discover Magic Home devices on your network |
| **▶ Start** | Begin syncing screen colors to the sign |
| **■ Stop** | Stop syncing |
| **Screen Region** | Choose which part of the screen to sample |
| **Update Rate** | How many color updates per second (1–30 fps) |
| **Smoothing** | How gradually colors transition (0 = instant, 1 = very slow) |
| **Brightness** | Scale down the output brightness |
| **Presets** | Send a fixed color instantly |
| **↺ Follow Screen** | Exit color lock and resume screen sync |

---

## ⚙️ CLI Options

```bash
python neon_sync.py [options]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--ip` | saved config | Controller IP address |
| `--fps` | 10 | Updates per second |
| `--region` | full | Screen region: `full` / `left` / `right` / `top` / `bottom` / `center` |
| `--port` | 7878 | Dashboard HTTP port |
| `--no-browser` | false | Don't auto-open browser |

---

## 🔧 How It Works

```
┌─────────────────┐     PIL ImageGrab     ┌──────────────────┐
│   Your Screen   │ ──────────────────▶  │  Color Extractor │
└─────────────────┘                       └────────┬─────────┘
                                                   │ Average RGB
                                          ┌────────▼─────────┐
                                          │ Smoothing Filter  │
                                          │  (EMA blending)   │
                                          └────────┬─────────┘
                                                   │ Smooth RGB
                                          ┌────────▼─────────┐
                                          │  Magic Home TCP   │
                                          │  Port 5577        │
                                          └────────┬─────────┘
                                                   │ Raw bytes
                                          ┌────────▼─────────┐
                                          │   Neon Sign 🌈    │
                                          └──────────────────┘
```

1. **Screen capture** — Pillow grabs your screen (or a sub-region) each frame
2. **Downsampling** — resized to 50×50 pixels for fast average color calculation
3. **Smoothing** — exponential moving average prevents harsh flickers
4. **Protocol** — raw TCP bytes sent on port 5577 (Magic Home protocol, no cloud needed)

---

## 🛠 Troubleshooting

**`pip` not recognized**
→ Reinstall Python and check **"Add Python to PATH"** during setup

**Can't connect to controller**
→ Make sure laptop and sign are on the same WiFi
→ Try pinging the IP: `ping 192.168.X.X`
→ Test port directly: `python -c "import socket; s=socket.socket(); s.connect(('YOUR_IP', 5577)); print('OK')"`

**Colors look washed out**
→ Lower Brightness slider
→ Reduce Smoothing for snappier response

**High CPU usage**
→ Lower FPS to 5–8
→ Use `center` region instead of full screen

**macOS screen capture permission**
→ System Preferences → Privacy & Security → Screen Recording → allow Terminal

---

## 📦 Dependencies

| Package | Use |
|---------|-----|
| `Pillow` | Screen capture |
| `numpy` | Fast pixel averaging |

No external Magic Home library needed — protocol is implemented from scratch.

---

## 📄 License

MIT © 2025 — free to use, modify, and share.

---

<div align="center">
Made with 🌈 for neon lovers
</div>
