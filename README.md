# NeonSync 🌈
> Real-time Magic Home neon sign ↔ laptop screen color sync

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run
```bash
# Opens dashboard in your browser automatically
python neon_sync.py

# Or specify your controller IP directly
python neon_sync.py --ip 192.168.1.42

# More options
python neon_sync.py --ip 192.168.1.42 --fps 15 --region center
```

### 3. Use the Dashboard
The browser dashboard opens at **http://localhost:7878**

From there you can:
- 🔍 **Scan** your network to auto-discover Magic Home devices
- ▶ **Start / Stop** sync
- 🎛 Adjust **FPS**, **Smoothing**, **Brightness**, and **Screen Region**
- 🎨 **Manually set** any color with presets or RGB sliders
- 📊 Watch the live **color history** wave

---

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--ip` | (from config) | Controller IP address |
| `--fps` | 10 | Color updates per second |
| `--region` | full | Screen region: full / left / right / top / bottom / center |
| `--port` | 7878 | Dashboard HTTP port |
| `--no-browser` | false | Don't auto-open browser |

---

## How It Works

1. **Screen capture** — Pillow grabs your screen (or a sub-region) every frame
2. **Color extraction** — The image is downsampled to 50×50 and averaged
3. **Smoothing** — Exponential moving average prevents harsh flickers
4. **Protocol** — Commands are sent over TCP port 5577 using the Magic Home raw protocol (no cloud, no app needed)

---

## Troubleshooting

**Can't connect?**
- Make sure laptop and controller are on the **same WiFi network**
- Try the **Scan** button in the dashboard to discover the IP automatically
- Ping the IP: `ping 192.168.1.X`

**Colors look washed out?**
- Lower the Brightness slider
- Increase Smoothing for less flickering

**High CPU?**
- Lower FPS to 5–8
- Use a smaller region like `center`

**macOS screen capture permission?**
- System Preferences → Privacy & Security → Screen Recording → allow Terminal/Python
