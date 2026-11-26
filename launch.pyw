"""Launch from pythonw and report startup problems in a native dialog."""
import ctypes
import os
from pathlib import Path
import sys
import traceback


try:
    from app import main
    exit_code = main()
except Exception:
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
