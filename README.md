# Num Lock OSD

A tiny on-screen display for Linux that flashes **NUM LOCK ON** / **NUM LOCK OFF** whenever you toggle Num Lock. Handy when your keyboard's Num Lock LED is dead or missing.

![PyQt6](https://img.shields.io/badge/PyQt6-grey?logo=qt) ![Linux](https://img.shields.io/badge/Linux-grey?logo=linux&logoColor=white)

## Features

- Reads Num Lock state from the kernel (`/sys/class/leds/*::numlock`), so it works on X11 and Wayland
- Small pill in the bottom-right corner, green for ON, gray for OFF
- Fade in/out animations, auto-hides after about a second
- Click-through — doesn't steal focus or block input
- Keeps working if the keyboard is unplugged and plugged back in

## Requirements

- Linux (X11 or Wayland)
- Python 3.10+
- PyQt6
- python-xlib (for X11 click-through)
- layer-shell-qt (for Wayland placement; without it the compositor decides where the popup goes)

## Installation

```bash
git clone https://github.com/jolinarn/numlock-osd.git
cd numlock-osd
```

Install the dependencies:

```bash
# Arch / CachyOS
sudo pacman -S python-pyqt6 python-xlib layer-shell-qt

# or with pip
pip install -r requirements.txt
```

## Usage

```bash
cd ~/numlock-osd
python3 main.py
```

Press Num Lock and the OSD will appear.

### Autostart (KDE / GNOME)

Create `~/.config/autostart/numlock-osd.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Num Lock OSD
Exec=bash -c "cd ~/numlock-osd && python3 -u main.py"
Icon=input-keyboard
X-GNOME-Autostart-enabled=true
```

## License

MIT
