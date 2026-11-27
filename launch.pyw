"""Launch from pythonw and report startup problems in a native dialog."""
import ctypes
import os
from pathlib import Path
import sys
import traceback


def configure_qt():
    # Resolve plugins from the PyQt wheel used by this interpreter.
    import PyQt5

    plugins = Path(PyQt5.__file__).resolve().parent / "Qt5" / "plugins"
    if not (plugins / "platforms" / "qwindows.dll").is_file():
        raise RuntimeError("找不到 PyQt5 的 qwindows.dll，请重新运行「安装依赖和模型.ps1」。")
    os.environ["QT_PLUGIN_PATH"] = str(plugins)
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins / "platforms")
    os.environ["QT_QPA_PLATFORM"] = "windows"


try:
    configure_qt()
    if sys.argv[1:] == ["--check-qt"]:
        from PyQt5.QtWidgets import QApplication

        qt_app = QApplication([sys.argv[0]])
        exit_code = 0 if qt_app.platformName() == "windows" else 1
    else:
        from app import main

        exit_code = main()
except Exception:
    if sys.argv[1:] == ["--check-qt"]:
        traceback.print_exc()
        sys.exit(1)
    log = Path(os.environ["LOCALAPPDATA"]) / "ShengMu" / "startup-error.log"
    message = "麦来无法启动。请检查 Python 和依赖是否已安装。"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        message += f"\n\n错误日志：{log}"
    except OSError:
        pass
    ctypes.windll.user32.MessageBoxW(None, message, "麦来 · YapDash", 0x10)
    exit_code = 1

sys.exit(exit_code)
