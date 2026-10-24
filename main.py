#!/usr/bin/env python3
import sys

from PyQt6.QtCore import QEasingCurve, QObject, QPropertyAnimation, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget
from Xlib import display

NUM_LOCK_BIT = 0b10  # verified: bit 1 of GetKeyboardControl().led_mask

POLL_MS = 100
SHOW_MS = 1100
FADE_MS = 200

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
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.resize(120, 36)

        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.finished.connect(self._on_anim_finished)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._fade_out)

        self.setWindowOpacity(0.0)

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
        self._position()
        self.hide_timer.stop()
        self._animate_to(1.0, QEasingCurve.Type.OutCubic)
        self.show()
        _set_click_through(self)
        self.hide_timer.start(SHOW_MS)

    def _fade_out(self):
        self._animate_to(0.0, QEasingCurve.Type.InCubic)

    def _animate_to(self, value: float, curve: QEasingCurve.Type):
        self.opacity_anim.stop()
        self.opacity_anim.setDuration(FADE_MS)
        self.opacity_anim.setStartValue(self.windowOpacity())
        self.opacity_anim.setEndValue(value)
        self.opacity_anim.setEasingCurve(curve)
        self.opacity_anim.start()

    def _on_anim_finished(self):
        if self.windowOpacity() <= 0.01:
            self.hide()

    def _position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        margin = 16
        x = screen.right() - self.width() - margin
        y = screen.bottom() - self.height() - margin
        self.move(x, y)


class NumLockWatcher(QObject):
    state_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._d = display.Display()
        self._prev_state = self._read_state()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(POLL_MS)

    def _read_state(self) -> bool:
        return bool(self._d.get_keyboard_control().led_mask & NUM_LOCK_BIT)

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
