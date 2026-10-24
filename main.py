#!/usr/bin/env python3
import glob
import sys

from PyQt6.QtCore import QEasingCurve, QObject, QPropertyAnimation, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

import wayland

NUM_LOCK_BIT = 0b10  # verified: bit 1 of GetKeyboardControl().led_mask
# kernel LED state, works on X11 + Wayland; inputN numbering changes between boots
NUM_LOCK_LED_GLOB = "/sys/class/leds/input*::numlock/brightness"

POLL_MS = 100
SHOW_MS = 1100
FADE_MS = 200
MARGIN = 16

ON_COLOR = "#4ade80"
OFF_COLOR = "#6b7280"


def _set_click_through(widget: QWidget):
    try:
        from Xlib.display import Display
        from Xlib.ext import shape

        wid = int(widget.winId())
        d = Display()
        window = d.create_resource_object("window", wid)
        window.shape_select_input(0)
        shape.input_shape_rectangles(window, shape.SO.Set, 0, 0, [], shape.SK.Input)
        d.sync()
    except Exception:
        pass


class NumLockOSD(QWidget):
    def __init__(self):
        super().__init__()
        self._wayland = wayland.is_wayland()
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        if self._wayland:
            flags |= Qt.WindowType.WindowTransparentForInput
        else:
            flags |= Qt.WindowType.X11BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.resize(120, 36)

        # Wayland ignores windowOpacity, so fade the contents instead
        self.opacity = QGraphicsOpacityEffect(self.label)
        self.opacity.setOpacity(0.0)
        self.label.setGraphicsEffect(self.opacity)
        self.opacity_anim = QPropertyAnimation(self.opacity, b"opacity")
        self.opacity_anim.finished.connect(self._on_anim_finished)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._fade_out)

        if self._wayland and not wayland.setup_layer_shell(self, MARGIN):
            print("layer-shell-qt unavailable, popup position is up to the compositor",
                  file=sys.stderr)

    def show_state(self, on: bool):
        color = ON_COLOR if on else OFF_COLOR
        self.label.setText(f"NUM LOCK {'ON' if on else 'OFF'}")
        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(20, 20, 20, 220);
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
                color: {color};
                border: 1px solid {color};
            }}
        """)
        if not self._wayland:
            self._position()
        self.hide_timer.stop()
        self._animate_to(1.0, QEasingCurve.Type.OutCubic)
        self.show()
        if not self._wayland:
            _set_click_through(self)
        self.hide_timer.start(SHOW_MS)

    def _fade_out(self):
        self._animate_to(0.0, QEasingCurve.Type.InCubic)

    def _animate_to(self, value: float, curve: QEasingCurve.Type):
        self.opacity_anim.stop()
        self.opacity_anim.setDuration(FADE_MS)
        self.opacity_anim.setStartValue(self.opacity.opacity())
        self.opacity_anim.setEndValue(value)
        self.opacity_anim.setEasingCurve(curve)
        self.opacity_anim.start()

    def _on_anim_finished(self):
        if self.opacity.opacity() <= 0.01:
            self.hide()

    def _position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - MARGIN
        y = screen.bottom() - self.height() - MARGIN
        self.move(x, y)


class NumLockWatcher(QObject):
    state_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._d = None
        if not glob.glob(NUM_LOCK_LED_GLOB):
            # no sysfs LED (unusual) -> fall back to asking the X server
            from Xlib import display
            self._d = display.Display()
        self._prev_state = self._read_state()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(POLL_MS)

    def _read_state(self) -> bool:
        if self._d is not None:
            return bool(self._d.get_keyboard_control().led_mask & NUM_LOCK_BIT)
        # re-glob each poll so a replugged keyboard (new inputN) keeps working
        for path in glob.glob(NUM_LOCK_LED_GLOB):
            try:
                with open(path) as f:
                    if f.read().strip() != "0":
                        return True
            except OSError:
                pass
        return False

    def _poll(self):
        state = self._read_state()
        if state != self._prev_state:
            self._prev_state = state
            self.state_changed.emit(state)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    osd = NumLockOSD()
    watcher = NumLockWatcher(app)
    watcher.state_changed.connect(osd.show_state)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
