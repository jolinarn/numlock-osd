import ctypes
import os

from PyQt6 import sip
from PyQt6.QtWidgets import QApplication

# trimmed copy of ~/discord-overlay/discord_overlay/wayland.py
_lib = None
_ANCHOR_BOTTOM = 2
_ANCHOR_RIGHT = 8
_LAYER_OVERLAY = 3
_KB_NONE = 0


class _CQMargins(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_int),
        ("top", ctypes.c_int),
        ("right", ctypes.c_int),
        ("bottom", ctypes.c_int),
    ]


def _load_lib():
    global _lib
    if _lib is not None:
        return _lib
    try:
        _lib = ctypes.cdll.LoadLibrary("libLayerShellQtInterface.so.6")
    except OSError:
        _lib = False
    return _lib


def is_wayland() -> bool:
    app = QApplication.instance()
    if app:
        return app.platformName() == "wayland"
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def setup_layer_shell(widget, margin: int) -> bool:
    """Pin the widget bottom-right on the overlay layer. Must run before first show()."""
    lib = _load_lib()
    if not lib:
        return False
    widget.winId()
    win = widget.windowHandle()
    if not win:
        return False

    get_fn = lib._ZN12LayerShellQt6Window3getEP7QWindow
    get_fn.restype = ctypes.c_void_p
    get_fn.argtypes = [ctypes.c_void_p]
    lsw = get_fn(sip.unwrapinstance(win))
    if not lsw:
        return False

    fn = lib._ZN12LayerShellQt6Window8setLayerENS0_5LayerE
    fn.argtypes = [ctypes.c_void_p, ctypes.c_int]
    fn(lsw, _LAYER_OVERLAY)

    fn = lib._ZN12LayerShellQt6Window10setAnchorsE6QFlagsINS0_6AnchorEE
    fn.argtypes = [ctypes.c_void_p, ctypes.c_int]
    fn(lsw, _ANCHOR_BOTTOM | _ANCHOR_RIGHT)

    margins = _CQMargins(0, 0, margin, margin)
    fn = lib._ZN12LayerShellQt6Window10setMarginsERK8QMargins
    fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    fn(lsw, ctypes.byref(margins))

    fn = lib._ZN12LayerShellQt6Window16setExclusiveZoneEi
    fn.argtypes = [ctypes.c_void_p, ctypes.c_int]
    fn(lsw, 0)

    fn = lib._ZN12LayerShellQt6Window24setKeyboardInteractivityENS0_21KeyboardInteractivityE
    fn.argtypes = [ctypes.c_void_p, ctypes.c_int]
    fn(lsw, _KB_NONE)

    fn = lib._ZN12LayerShellQt6Window17setActivateOnShowEb
    fn.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    fn(lsw, False)

    screen = QApplication.primaryScreen()
    if screen:
        win.setScreen(screen)
        fn = lib._ZN12LayerShellQt6Window9setScreenEP7QScreen
        fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        fn(lsw, sip.unwrapinstance(screen))

    return True
