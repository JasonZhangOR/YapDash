import audioop
import base64
from contextlib import closing
import ctypes
from ctypes import wintypes
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
import threading
import time
import winsound
from urllib.parse import urlsplit

from PyQt5 import QtCore as C, QtGui as G, QtWidgets as Q

from sharing import Words, clean, serve
from speakers import Activity, distance, fingerprint, is_active
from replay import VoiceReplay
from sensevoice import MODEL_DIR, MODEL_FILES, SenseVoice
import delta_pack
from phonetics import fold, match_words


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "models" / MODEL_DIR
DATA = Path(os.environ["LOCALAPPDATA"]) / "ShengMu"
BRAND = "麦来 · YapDash"
DEFAULT_DANMAKU_COLOR = "#fff28a"
EFFECTS = {"normal": "普通弹幕", "gold": "金色弹幕", "urgent": "醒目提醒",
           "comic": "漫画爆炸字", "sticker": "歪章贴纸", "signal": "方向路牌", "prank": "单挑大字"}
POSITIONS = {"scroll": "从右往左", "top": "顶部正中", "bottom": "底部悬浮",
             "right": "右侧弹入", "left": "左侧弹入", "auto": "跟随语音方向"}
DEFAULT_EFFECT = ["normal", 0, "区"]
CUE_PATTERN = re.compile(r"左手边|左边|左侧|左面|右手边|右边|右侧|右面")
BURST_WINDOW_SECONDS = 5.0
MAX_BURST_CAPTIONS = 2
DELTA_LATIN_NAMES = frozenset(word.casefold() for word in delta_pack.LATIN_NAMES)
APP_STYLE = """
QWidget#appWindow {background:#111116}
QWidget {color:#efedf5}
QDialog,QMessageBox,QMenu {background:#1a1922}
QLabel {background:transparent}
QLabel#brandTitle {font-size:21px;font-weight:700;color:#f5f1ff}
QLabel#brandEnglish {font-size:14px;font-weight:600;color:#c4a8fa}
QLabel#pageTitle {font-size:25px;font-weight:700;color:#f5f1ff}
QLabel#homeStatus {font-size:30px;font-weight:700;color:#faf7ff}
QLabel#sectionText {font-size:15px;font-weight:600;color:#eae4fb}
QLabel#secondaryText {color:#aba6bd}
QLabel#recentText {font-size:20px;color:#f0ebfc}
QLabel#recentText[empty="true"] {font-size:16px;color:#a49bb7}
QLabel#keyboardHint {color:#b6adc8;background:#211d2c;border:1px solid #3b334a;
                    border-radius:5px;padding:3px 7px}
QLabel#guideStep {color:#c4a8fa;font-weight:600}
QLabel#guideBody {font-size:15px;color:#d5cde6}
QFrame#connectionCard {background:#1c1928;border:1px solid #332b48;border-radius:16px}
QFrame#recentCard {background:#181820;border:1px solid #2c2937;border-radius:13px}
QFrame#settingsRail {background:#18171f;border:1px solid #2c2937;border-radius:12px}
QFrame#panelLine {background:#2e293d;max-height:1px}
QFrame#statusDot {background:#736d84;border-radius:4px}
QFrame#statusDot[active="true"] {background:#a7eac6}
QPushButton#debugToggle:checked {background:#44345e;border:1px solid #78619c}
QLineEdit,QPlainTextEdit,QListWidget,QComboBox,QSpinBox {
    background:#1c1b25;border:1px solid #373345;border-radius:8px;padding:8px;
    selection-background-color:#544077}
QComboBox QAbstractItemView {
    background:#1c1b25;color:#efedf5;border:1px solid #554967;padding:4px;
    selection-background-color:#4b3866;selection-color:#ffffff;outline:0}
QListWidget#settingsNavigation {background:transparent;border:0;padding:0;outline:0}
QListWidget#settingsNavigation::item {padding:11px 10px;border-radius:7px;margin:2px 0}
QListWidget#settingsNavigation::item:selected {background:#342849;color:#f5edff}
QListWidget#settingsNavigation::item:hover:!selected {background:#242130}
QListWidget::item {padding:5px 8px;border-radius:5px}
QListWidget::item:selected {background:#45345e;color:#f5edff}
QPushButton {background:#242231;color:#efedf8;border:1px solid #383347;
             border-radius:8px;padding:9px 14px;font-weight:600}
QPushButton:hover {background:#322c42;border-color:#574b6e}
QPushButton[variant="primary"] {background:#c4a8fa;color:#221737;border-color:#c4a8fa}
QPushButton[variant="primary"]:hover {background:#d5bfff}
QPushButton[variant="quiet"] {background:transparent;color:#cbb5f7;border:1px solid transparent}
QPushButton[variant="quiet"]:hover {background:#2a2238}
QPushButton:disabled {color:#827b91;background:#1e1c28;border-color:#302b3b}
QPushButton:focus,QComboBox:focus,QLineEdit:focus {border:1px solid #c4a8fa}
QProgressBar {background:#302840;border:0;border-radius:4px;max-height:7px}
QProgressBar::chunk {background:#c4a8fa;border-radius:4px}
QScrollArea {background:transparent;border:0}
QScrollArea#settingsScroll,QWidget#settingsBody,QWidget#settingsViewport {background:#111116}
QScrollBar:vertical {background:#1c1a24;width:10px;margin:0;border:0}
QScrollBar::handle:vertical {background:#50455f;border-radius:4px;min-height:26px}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:none}
QMenu::item:selected {background:#342849}
"""


def brand_icon():
    pixmap = G.QPixmap(64, 64)
    pixmap.fill(C.Qt.transparent)
    painter = G.QPainter(pixmap)
    painter.setRenderHint(G.QPainter.Antialiasing)
    painter.setPen(C.Qt.NoPen)
    painter.setBrush(G.QColor("#c4a8fa"))
    painter.drawRoundedRect(2, 2, 60, 60, 15, 15)
    ink = G.QColor("#2b1c45")
    painter.setBrush(ink)
    painter.drawRoundedRect(33, 13, 12, 23, 6, 6)
    painter.setPen(G.QPen(ink, 3, C.Qt.SolidLine, C.Qt.RoundCap))
    painter.drawArc(C.QRectF(27, 19, 24, 25), 180 * 16, 180 * 16)
    painter.drawLine(39, 44, 39, 51)
    painter.drawLine(32, 51, 46, 51)
    painter.drawLine(14, 23, 25, 23)
    painter.drawLine(10, 30, 22, 30)
    painter.drawLine(16, 37, 24, 37)
    painter.end()
    return G.QIcon(pixmap)


def running_processes():
    class Entry(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD),
                    ("pid", wintypes.DWORD), ("default_heap", ctypes.c_size_t),
                    ("module", wintypes.DWORD), ("threads", wintypes.DWORD),
                    ("parent", wintypes.DWORD), ("priority", ctypes.c_long),
                    ("flags", wintypes.DWORD), ("name", wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    for function in (kernel.Process32FirstW, kernel.Process32NextW):
        function.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
        function.restype = wintypes.BOOL
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    entry = Entry()
    entry.size = ctypes.sizeof(entry)
    try:
        if not kernel.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise ctypes.WinError(ctypes.get_last_error())
        processes = []
        while True:
            processes.append((entry.name, entry.pid, entry.parent))
            if not kernel.Process32NextW(snapshot, ctypes.byref(entry)):
                return processes
    finally:
        kernel.CloseHandle(snapshot)


class AudioMeter(Q.QWidget):
    def __init__(self):
        super().__init__()
        self.levels = [0] * 26
        self.setMinimumHeight(72)
        self.setMinimumWidth(160)
        self.setAccessibleName("监听音量")

    def setValue(self, volume):
        if not volume:
            self.levels = [int(level * 0.75) for level in self.levels[1:]] + [0]
        else:
            self.levels = self.levels[1:] + [volume]
        self.update()

    def reset(self):
        self.levels = [0] * len(self.levels)
        self.update()

    def paintEvent(self, _):
        painter = G.QPainter(self)
        painter.setRenderHint(G.QPainter.Antialiasing)
        painter.setPen(C.Qt.NoPen)
        step = self.width() / len(self.levels)
        for index, level in enumerate(self.levels):
            height = 5 + min(100, level) / 100 * (self.height() - 12)
            painter.setBrush(G.QColor("#c4a8fa" if level > 0 else "#3e3454"))
            painter.drawRoundedRect(C.QRectF(index * step + 1, (self.height() - height) / 2,
                                             max(2, min(6, step - 3)), height), 2, 2)


class QuickStart(Q.QDialog):
    STEPS = (
        ("选择声音来源",
         "先打开 KOOK 或 Oopz，进入语音房。在设置的「音频与诊断」里选择对应应用，"
         "回首页点「开始监听」。队友说话时，首页的音量条会动。"),
        ("决定哪些话要上屏",
         f"新词库已经带了 {len(delta_pack.WORDS)} 个三角洲关键词。在「设置 → 关键词」里可以增删或批量粘贴。"
         "比如只配置「牢赛」，队友说「东楼有牢赛」，上屏的是整句话。"),
        ("自己试播一次",
         "下面的按钮可以直接试播整句，当前不用进语音房。娱乐模式下，在游戏里按 "
         "Ctrl+Shift+F8 可以试播大字「区」。纯净模式用普通弹幕显示原句。"),
        ("和朋友一起配词",
         "在「设置 → 共享」里生成建议链接，朋友提的改动由你通过后才生效。"
         "要一起即时改词，可以手动生成限时共编链接。"),
    )

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle("快速上手 | " + BRAND)
        self.resize(560, 330)
        self.setMinimumWidth(480)
        self.index = 0
        layout = Q.QVBoxLayout(self)
        layout.setContentsMargins(26, 23, 26, 23)
        layout.setSpacing(14)
        self.step = Q.QLabel()
        self.step.setObjectName("guideStep")
        layout.addWidget(self.step)
        self.heading = Q.QLabel()
        self.heading.setObjectName("pageTitle")
        layout.addWidget(self.heading)
        self.body = Q.QLabel()
        self.body.setObjectName("guideBody")
        self.body.setWordWrap(True)
        layout.addWidget(self.body)
        self.preview = Q.QPushButton("试播「东楼有牢赛」")
        self.preview.clicked.connect(lambda: self.window.emit_overlay("试播：东楼有牢赛"))
        layout.addWidget(self.preview, 0, C.Qt.AlignLeft)
        layout.addStretch(1)
        actions = Q.QHBoxLayout()
        skip = Q.QPushButton("跳过")
        skip.setProperty("variant", "quiet")
        skip.clicked.connect(self.reject)
        actions.addWidget(skip)
        actions.addStretch(1)
        self.previous = Q.QPushButton("上一步")
        self.previous.clicked.connect(lambda: self.go(self.index - 1))
        actions.addWidget(self.previous)
        self.next = Q.QPushButton()
        self.next.setProperty("variant", "primary")
        self.next.clicked.connect(self.advance)
        actions.addWidget(self.next)
        layout.addLayout(actions)
        self.go(0)

    def go(self, index):
        self.index = index
        heading, body = self.STEPS[index]
        self.step.setText(f"快速上手 · {index + 1} / {len(self.STEPS)}")
        self.heading.setText(heading)
        self.body.setText(body)
        self.preview.setVisible(index == 2)
        self.previous.setEnabled(index > 0)
        self.next.setText("完成" if index == len(self.STEPS) - 1 else "下一步")
        self.next.setDefault(True)

    def advance(self):
        if self.index + 1 == len(self.STEPS):
            self.accept()
        else:
            self.go(self.index + 1)


def direction(text):
    cue = CUE_PATTERN.search(text)
    return ("right" if cue[0].startswith("右") else "left") if cue else None


def effect_fields(state, word):
    style, cooldown, glyph, *rest = state["effects"].get(word, DEFAULT_EFFECT)
    return style, cooldown, glyph, rest[0] if rest else "scroll"


class Artwork(Q.QWidget):
    def __init__(self, text, style, size, position, width, text_color, parent):
        super().__init__(parent)
        self.setAttribute(C.Qt.WA_NoSystemBackground)
        self.text = text
        self.art_style = style
        self.position = position
        self.text_color = text_color
        self.font = G.QFont("Microsoft YaHei UI")
        self.font.setPixelSize(size + 2)
        self.font.setWeight(G.QFont.Black)
        margins = 72 if style == "comic" else 50
        metrics = G.QFontMetrics(self.font)
        self.text = metrics.elidedText(text, C.Qt.ElideRight, max(40, width - margins))
        self.setFixedSize(metrics.horizontalAdvance(self.text) + margins, metrics.height() + 38)

    def paintEvent(self, _):
        painter = G.QPainter(self)
        painter.setRenderHint(G.QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        x, y = self.width() / 2 - 7, self.height() / 2 - 9
        style = self.art_style
        if style == "comic":
            polygon = G.QPolygonF([C.QPointF(x * px, y * py) for px, py in (
                (-1, 0), (-.83, -.34), (-.93, -.88), (-.53, -.64), (-.42, -.99),
                (-.05, -.76), (.25, -1), (.38, -.67), (.79, -.92), (.74, -.43),
                (1, 0), (.8, .35), (.88, .89), (.48, .69), (.24, 1), (-.09, .74),
                (-.38, .99), (-.55, .67), (-.93, .87), (-.82, .32))])
            painter.setBrush(G.QColor("#ffdb63"))
            painter.setPen(G.QPen(G.QColor("#1c1435"), 4))
            painter.drawPolygon(polygon)
        elif style == "sticker":
            painter.rotate(-3)
            y -= 4
            painter.setBrush(G.QColor("#e95278"))
            painter.setPen(G.QPen(G.QColor("#fff2ca"), 4))
            painter.drawRoundedRect(C.QRectF(-x, -y, x * 2, y * 2), 7, 7)
        else:
            arrow = 20
            shape = [(-x, -y), (x-arrow, -y), (x, 0), (x-arrow, y), (-x, y)]
            if self.position == "left":
                shape = [(-px, py) for px, py in shape]
            painter.setBrush(G.QColor("#0e3958"))
            painter.setPen(G.QPen(G.QColor("#90ebff"), 4))
            painter.drawPolygon(G.QPolygonF([C.QPointF(px, py) for px, py in shape]))
        glyphs = G.QPainterPath()
        glyphs.addText(0, 0, self.font, self.text)
        painter.translate(-glyphs.boundingRect().center())
        color = G.QColor(self.text_color)
        edge = G.QColor("#181320" if color.lightness() > 120 else "#fffaea")
        painter.setPen(G.QPen(edge, 2.5, C.Qt.SolidLine, C.Qt.RoundCap, C.Qt.RoundJoin))
        painter.setBrush(color)
        painter.drawPath(glyphs)


class PanicHotkey(C.QAbstractNativeEventFilter):
    def __init__(self, window):
        super().__init__()
        self.window = window

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) not in (b"windows_dispatcher_MSG", b"windows_generic_MSG"):
            return False, 0
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam == 47:
            self.window.disable_pranks()
        elif msg.message == 0x0312 and msg.wParam == 48:
            self.window.repeat_last()
        elif msg.message == 0x0312 and msg.wParam == 49:
            self.window.preview_prank()
        return False, 0


class Listener(C.QThread):
    level = C.pyqtSignal(int)
    timed_sentence = C.pyqtSignal(str, float, float, bytes)
    status = C.pyqtSignal(str)

    def __init__(self, pid, model_path, parent=None):
        super().__init__(parent)
        self.pid = pid
        self.model_path = model_path
        self.stop = threading.Event()
        self.record_replay = threading.Event()

    def audio_stream(self):
        if self.pid is None:
            from microphone import packets

            yield from packets(self.stop, lambda: self.status.emit("正在读取麦克风"))
            return
        from capture import packets

        rate_state = None
        with closing(packets(self.pid, self.stop, lambda: self.status.emit("正在监听"))) as stream:
            for stereo in stream:
                mono = audioop.tomono(stereo, 2, 0.5, 0.5)
                mono, rate_state = audioop.ratecv(mono, 2, 1, 44100, 16000, rate_state)
                yield mono

    def run(self):
        try:
            recognizer = SenseVoice(self.model_path)
            samples = 0
            if self.stop.is_set():
                return
            with closing(self.audio_stream()) as stream:
                for mono in stream:
                    if self.stop.is_set():
                        break
                    samples += len(mono) // 2
                    now = time.monotonic()
                    self.level.emit(min(100, audioop.rms(mono, 2) // 100))
                    origin = now - samples / 16000
                    for text, start, end, pcm in recognizer.feed(mono):
                        self.timed_sentence.emit(text, origin + start, origin + end,
                                                 pcm if self.record_replay.is_set() else b"")
        except Exception as error:
            self.status.emit(f"监听失败 · {error}")


class Overlay(Q.QLabel):
    def __init__(self):
        super().__init__(None, C.Qt.Tool | C.Qt.FramelessWindowHint |
                         C.Qt.WindowStaysOnTopHint | C.Qt.WindowTransparentForInput |
                         C.Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(C.Qt.WA_ShowWithoutActivating)
        self.setAttribute(C.Qt.WA_TranslucentBackground)
        self.setTextFormat(C.Qt.PlainText)
        self.animation = C.QPropertyAnimation(self, b"pos", self)
        self.expiry = C.QTimer(self)
        self.expiry.setSingleShot(True)

    def fly(self, text, size, color, seconds, offset, screen, position, style, lane):
        self.animation.stop()
        trim = {"gold": "border:2px solid #d8aa52;", "urgent": "border:2px solid #ed7695;"}.get(style, "")
        self.setStyleSheet(f"color:{color};background:rgba(13,18,27,225);padding:4px 18px;"
                           f"border-radius:11px;font-size:{size}px;font-weight:700;{trim}")
        bounds = screen.availableGeometry()
        font = G.QFont(self.font())
        font.setPixelSize(size)
        font.setBold(True)
        if style in ("comic", "sticker", "signal"):
            self.setStyleSheet("background:transparent")
            self.art = Artwork(text, style, size, position, bounds.width() - 35, color, self)
            self.resize(self.art.size())
        else:
            self.setText(G.QFontMetrics(font).elidedText(text, C.Qt.ElideRight,
                                                        max(120, bounds.width() - 60)))
            self.adjustSize()
        padding = min(offset, max(0, bounds.height() - self.height()))
        y = bounds.top() + min(padding + lane * (self.height() + 4), bounds.height() - self.height())
        middle_x = bounds.center().x() - self.width() // 2
        start = C.QPoint(bounds.right() + 1, y)
        end = C.QPoint(bounds.left() - self.width(), y)
        if position in ("top", "bottom"):
            bottom_y = max(bounds.top(), bounds.bottom() - 22 - (lane + 1) * (self.height() + 4))
            end = C.QPoint(middle_x, bottom_y if position == "bottom" else y)
            start = end + C.QPoint(0, 22 if position == "bottom" else -18)
        elif position in ("right", "left"):
            side_y = min(bounds.center().y() - self.height() // 2 + lane * (self.height() + 4),
                         bounds.bottom() - self.height())
            if position == "right":
                start = C.QPoint(bounds.right() + 1, side_y)
                end = C.QPoint(bounds.right() - self.width() - 15, side_y)
            else:
                start = C.QPoint(bounds.left() - self.width(), side_y)
                end = C.QPoint(bounds.left() + 16, side_y)
        self.animation.setStartValue(start)
        self.animation.setEndValue(end)
        self.animation.setDuration(seconds * 1000 if position == "scroll" else 240)
        self.animation.setEasingCurve(C.QEasingCurve.Linear if position == "scroll" else C.QEasingCurve.OutCubic)
        self.move(self.animation.startValue())
        self.show()
        self.animation.start()

    def giant(self, glyph, screen, color="#ffffff"):
        bounds = screen.geometry()
        self.setAlignment(C.Qt.AlignCenter)
        self.setText(glyph)
        size = int(min(bounds.width(), bounds.height()) * 0.82)
        self.setStyleSheet(f"color:{color};background:rgba(25,14,32,195);"
                           f"font-size:{size}px;font-weight:900;")
        width = min(bounds.width(), size + 40)
        height = min(bounds.height(), size + 40)
        self.setGeometry(bounds.center().x() - width // 2, bounds.center().y() - height // 2,
                         width, height)
        self.show()


class RegionPicker(Q.QDialog):
    def __init__(self, screen):
        super().__init__(None, C.Qt.FramelessWindowHint | C.Qt.WindowStaysOnTopHint)
        self.setCursor(C.Qt.CrossCursor)
        self.setGeometry(screen.geometry())
        self.image = screen.grabWindow(0)
        self.band = Q.QRubberBand(Q.QRubberBand.Rectangle, self)
        self.start = None
        self.region = None

    def paintEvent(self, _):
        painter = G.QPainter(self)
        painter.drawPixmap(self.rect(), self.image)
        painter.fillRect(self.rect(), G.QColor(0, 0, 0, 50))

    def mousePressEvent(self, event):
        if event.button() == C.Qt.LeftButton:
            self.start = event.pos()
            self.band.setGeometry(C.QRect(self.start, C.QSize()))
            self.band.show()

    def mouseMoveEvent(self, event):
        if self.start is not None:
            self.band.setGeometry(C.QRect(self.start, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if self.start is not None and event.button() == C.Qt.LeftButton:
            rect = C.QRect(self.start, event.pos()).normalized().intersected(self.rect())
            if rect.width() >= 8 and rect.height() >= 8:
                self.region = (rect.x(), rect.y(), rect.width(), rect.height())
                self.accept()
            else:
                self.start = None
                self.band.hide()


class Window(Q.QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("appWindow")
        self.setWindowTitle(BRAND + " | 开黑语音弹幕")
        self.resize(900, 590)
        self.setMinimumSize(720, 520)
        self.store = Words(DATA / "words.json")
        self.settings = C.QSettings("ShengMu", "ShengMu")
        self.guide = None
        self.speaker_profiles = json.loads(self.settings.value("speaker_profiles", "{}"))
        self.activity = Activity()
        self.calibration = None
        self.server = None
        self.listener = None
        self.microphone_listener = None
        self.voice_replay = VoiceReplay(self)
        self.overlays = []
        self.prank_overlay = None
        self.prank_timer = C.QTimer(self)
        self.prank_timer.setSingleShot(True)
        self.prank_timer.timeout.connect(self.clear_prank)
        self.last_prank = float("-inf")
        self.last_hit = {}
        self.burst_hits = {}
        self.last_line = None
        self.revision = -1
        self.quitting = False

        layout = Q.QVBoxLayout(self)
        layout.setContentsMargins(34, 24, 34, 26)
        layout.setSpacing(22)
        title = Q.QLabel("麦来")
        title.setObjectName("brandTitle")
        header = Q.QHBoxLayout()
        mark = Q.QLabel()
        mark.setPixmap(brand_icon().pixmap(36, 36))
        header.addWidget(mark)
        header.addWidget(title)
        english = Q.QLabel("YapDash")
        english.setObjectName("brandEnglish")
        header.addSpacing(4)
        header.addWidget(english, 0, C.Qt.AlignVCenter)
        header.addStretch()
        self.mode = Q.QComboBox()
        self.mode.setAccessibleName("运行模式")
        self.mode.addItem("纯净模式", "clean")
        self.mode.addItem("娱乐模式", "fun")
        saved_mode = self.mode.findData(self.settings.value("display_mode", "clean"))
        self.mode.setCurrentIndex(saved_mode if saved_mode >= 0 else self.mode.findData("clean"))
        self.mode.currentIndexChanged.connect(self.change_mode)
        self.navigation = Q.QPushButton("设置")
        self.navigation.setProperty("variant", "secondary")
        self.navigation.clicked.connect(self.toggle_settings)
        self.debug_button = Q.QPushButton("调试模式")
        self.debug_button.setObjectName("debugToggle")
        self.debug_button.setProperty("variant", "secondary")
        self.debug_button.setCheckable(True)
        self.debug_button.toggled.connect(self.toggle_debug)
        header.addWidget(self.debug_button)
        header.addWidget(self.navigation)
        self.hide_button = Q.QPushButton("隐藏到托盘")
        self.hide_button.setProperty("variant", "secondary")
        self.hide_button.clicked.connect(self.hide)
        header.addWidget(self.hide_button)
        layout.addLayout(header)
        content = Q.QHBoxLayout()
        content.setSpacing(18)
        layout.addLayout(content, 1)
        self.views = Q.QStackedWidget()
        content.addWidget(self.views, 1)
        self.build_debug(content)
        self.build_home()
        self.build_settings()
        self.build_listen()
        self.build_words()
        self.build_presets()
        self.build_share()
        self.build_overlay()
        self.build_speakers()
        self.refresh_words()

        tray_icon = brand_icon()
        self.setWindowIcon(tray_icon)
        self.tray = Q.QSystemTrayIcon(tray_icon, self)
        menu = Q.QMenu(self)
        menu.addAction("打开麦来", self.reopen)
        menu.addAction("设置", self.open_settings)
        menu.addAction("重看上一句", self.repeat_last)
        self.tray_prank_preview = menu.addAction("试播整蛊大字", self.preview_prank)
        self.tray_prank_preview.setEnabled(self.mode.currentData() == "fun")
        menu.addAction("停止监听", self.stop_listen)
        mode_menu = menu.addMenu("运行模式")
        mode_group = Q.QActionGroup(mode_menu)
        self.tray_modes = {}
        for index in range(self.mode.count()):
            mode = self.mode.itemData(index)
            action = mode_menu.addAction(self.mode.itemText(index))
            action.setCheckable(True)
            mode_group.addAction(action)
            action.setChecked(mode == self.mode.currentData())
            action.triggered.connect(lambda checked, item=index: self.mode.setCurrentIndex(item))
            self.tray_modes[mode] = action
        menu.addAction("关闭整蛊并清屏", self.disable_pranks)
        menu.addAction("退出", self.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.reopen() if reason == Q.QSystemTrayIcon.Trigger else None)
        self.tray.setToolTip(f"{BRAND} · 未监听")
        self.has_tray = Q.QSystemTrayIcon.isSystemTrayAvailable()
        if self.has_tray:
            self.tray.show()
        self.hide_button.setVisible(self.has_tray)
        self.panic_filter = PanicHotkey(self)
        Q.QApplication.instance().installNativeEventFilter(self.panic_filter)
        self.hotkey_ready = bool(ctypes.windll.user32.RegisterHotKey(None, 47, 0x4006, 0x79))
        self.repeat_hotkey_ready = bool(ctypes.windll.user32.RegisterHotKey(None, 48, 0x4006, 0x78))
        self.preview_hotkey_ready = bool(ctypes.windll.user32.RegisterHotKey(None, 49, 0x4006, 0x77))
        self.preview_hotkey_hint.setText(
            "游戏内试播大字 · Ctrl+Shift+F8" if self.preview_hotkey_ready
            else "未能注册 Ctrl+Shift+F8，可从设置或托盘菜单试播。")
        self.repeat_key.setVisible(self.repeat_hotkey_ready)
        self.prank_help.setText("游戏中按 Ctrl+Shift+F10 可关掉整蛊并清屏。" if self.hotkey_ready
                                else "快捷键被占用，可在托盘菜单中关闭整蛊并清屏。")
        self.refresh_processes()
        self.refresh_timer = C.QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_words)
        self.refresh_timer.start(350)
        self.speaker_timer = C.QTimer(self)
        self.speaker_timer.timeout.connect(self.poll_speakers)
        self.speaker_timer.start(100)

    def page(self, label):
        page = Q.QWidget()
        page_layout = Q.QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(15)
        heading = Q.QLabel(label)
        heading.setObjectName("pageTitle")
        page_layout.addWidget(heading)
        scroll = Q.QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.viewport().setObjectName("settingsViewport")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(Q.QFrame.NoFrame)
        page_layout.addWidget(scroll, 1)
        body = Q.QWidget()
        body.setObjectName("settingsBody")
        layout = Q.QVBoxLayout(body)
        layout.setContentsMargins(0, 4, 8, 6)
        layout.setSpacing(10)
        scroll.setWidget(body)
        self.settings_pages.addWidget(page)
        self.settings_list.addItem(label)
        return layout

    def build_debug(self, content):
        self.debug_panel = Q.QFrame()
        self.debug_panel.setObjectName("recentCard")
        self.debug_panel.setFixedWidth(310)
        layout = Q.QVBoxLayout(self.debug_panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        title = Q.QLabel("监听记录")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        self.debug_log = Q.QPlainTextEdit()
        self.debug_log.setReadOnly(True)
        self.debug_log.setMaximumBlockCount(240)
        self.debug_log.setPlaceholderText("说完一句话后，这里会显示转写和关键词命中结果。")
        layout.addWidget(self.debug_log, 1)
        self.microphone_status = Q.QLabel("麦克风已关闭")
        self.microphone_status.setObjectName("secondaryText")
        self.microphone_status.setWordWrap(True)
        layout.addWidget(self.microphone_status)
        self.microphone_volume = Q.QProgressBar()
        self.microphone_volume.setAccessibleName("麦克风输入音量")
        self.microphone_volume.setTextVisible(False)
        self.microphone_volume.setFixedHeight(6)
        self.microphone_volume.setValue(0)
        layout.addWidget(self.microphone_volume)
        self.microphone_button, _ = self.button_row(
            layout, ("开启麦克风", self.toggle_microphone), ("清空", self.debug_log.clear))
        content.addWidget(self.debug_panel)
        self.debug_panel.hide()

    def toggle_debug(self, enabled):
        previous_width = self.width()
        self.debug_panel.setVisible(enabled)
        if not self.isMaximized() and self.screen():
            span = self.debug_panel.width() + 18
            if enabled:
                width = min(previous_width + span, self.screen().availableGeometry().width())
                self.debug_added_width = max(0, width - previous_width)
                self.resize(width, self.height())
            else:
                self.resize(previous_width - getattr(self, "debug_added_width", 0), self.height())
        if not enabled:
            self.stop_microphone()

    def toggle_microphone(self):
        if self.microphone_listener:
            self.stop_microphone()
            return
        if not self.debug_button.isChecked():
            return
        model = self.listening_model()
        if model is None:
            self.microphone_status.setText(self.missing_model_message())
            return
        self.microphone_listener = Listener(None, model, self)
        self.microphone_listener.level.connect(self.microphone_volume.setValue)
        self.microphone_listener.status.connect(self.microphone_status.setText)
        self.microphone_listener.timed_sentence.connect(self.on_microphone_sentence)
        self.microphone_listener.finished.connect(self.microphone_finished)
        self.microphone_status.setText("正在加载离线模型…")
        self.microphone_button.setText("关闭麦克风")
        self.microphone_listener.start()

    def stop_microphone(self):
        if self.microphone_listener:
            self.microphone_listener.stop.set()
            self.microphone_status.setText("正在关闭麦克风…")
            self.microphone_button.setEnabled(False)

    def microphone_finished(self):
        self.microphone_listener.deleteLater()
        self.microphone_listener = None
        self.microphone_volume.setValue(0)
        if not self.microphone_status.text().startswith("监听失败"):
            self.microphone_status.setText("麦克风已关闭")
        self.microphone_button.setText("开启麦克风")
        self.microphone_button.setEnabled(True)
        if self.quitting and not self.listener:
            Q.QApplication.quit()

    def on_microphone_sentence(self, text, start, end, pcm):
        if (self.debug_button.isChecked() and self.microphone_listener
                and not self.microphone_listener.stop.is_set()):
            self.on_sentence(text, start, end, pcm, microphone=True)

    def build_settings(self):
        self.settings_view = Q.QWidget()
        self.views.addWidget(self.settings_view)
        row = Q.QHBoxLayout(self.settings_view)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(28)
        rail = Q.QFrame()
        rail.setObjectName("settingsRail")
        rail.setFixedWidth(160)
        navigation = Q.QVBoxLayout(rail)
        navigation.setContentsMargins(10, 14, 10, 10)
        title = Q.QLabel("设置")
        title.setObjectName("sectionText")
        title.setContentsMargins(10, 0, 0, 4)
        navigation.addWidget(title)
        self.settings_list = Q.QListWidget()
        self.settings_list.setObjectName("settingsNavigation")
        self.settings_list.setAccessibleName("设置分类")
        self.settings_list.setHorizontalScrollBarPolicy(C.Qt.ScrollBarAlwaysOff)
        navigation.addWidget(self.settings_list)
        tutorial = Q.QPushButton("新手教程")
        tutorial.setProperty("variant", "quiet")
        tutorial.clicked.connect(self.open_guide)
        navigation.addWidget(tutorial)
        row.addWidget(rail)
        self.settings_pages = Q.QStackedWidget()
        row.addWidget(self.settings_pages, 1)
        self.settings_list.currentRowChanged.connect(self.settings_pages.setCurrentIndex)

    def open_guide(self):
        if self.guide:
            self.guide.raise_()
            self.guide.activateWindow()
            return
        guide = QuickStart(self)
        self.guide = guide
        guide.finished.connect(self.close_guide)
        guide.open()

    def close_guide(self, _):
        self.settings.setValue("guide_seen", True)
        self.guide.deleteLater()
        self.guide = None

    def show_first_run_guide(self):
        if not self.settings.value("guide_seen", False, type=bool):
            self.open_guide()

    def toggle_settings(self):
        if self.views.currentWidget() is self.settings_view:
            self.views.setCurrentIndex(0)
            self.navigation.setText("设置")
        else:
            self.open_settings()

    def open_settings(self):
        self.views.setCurrentWidget(self.settings_view)
        if self.settings_list.currentRow() < 0:
            self.settings_list.setCurrentRow(0)
        self.navigation.setText("返回首页")
        if not self.isVisible():
            self.reopen()

    def build_home(self):
        home = Q.QWidget()
        content = Q.QVBoxLayout(home)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(17)
        self.views.addWidget(home)

        connection = Q.QFrame()
        connection.setObjectName("connectionCard")
        panel = Q.QVBoxLayout(connection)
        panel.setContentsMargins(25, 22, 25, 22)
        panel.setSpacing(17)
        state_row = Q.QHBoxLayout()
        source_caption = Q.QLabel("开黑监听")
        source_caption.setObjectName("sectionText")
        state_row.addWidget(source_caption, 1)
        state_row.addWidget(self.mode)
        panel.addLayout(state_row)
        activity_row = Q.QHBoxLayout()
        activity_row.setSpacing(30)
        source_details = Q.QVBoxLayout()
        source_details.setSpacing(7)
        connection_status = Q.QHBoxLayout()
        self.status_dot = Q.QFrame()
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setFixedSize(8, 8)
        connection_status.addWidget(self.status_dot, 0, C.Qt.AlignVCenter)
        self.home_status = Q.QLabel("未监听")
        self.home_status.setObjectName("homeStatus")
        self.home_status.setWordWrap(True)
        connection_status.addWidget(self.home_status, 1)
        source_details.addLayout(connection_status)
        self.home_source = Q.QLabel("在设置中选择声音来源")
        self.home_source.setObjectName("secondaryText")
        self.home_source.setWordWrap(True)
        source_details.addWidget(self.home_source)
        activity_row.addLayout(source_details, 5)
        self.home_volume = AudioMeter()
        activity_row.addWidget(self.home_volume, 4)
        panel.addLayout(activity_row)
        bar = Q.QFrame()
        bar.setObjectName("panelLine")
        bar.setFixedHeight(1)
        panel.addWidget(bar)
        self.listen_button, source_button = self.button_row(
            panel, ("开始监听", self.toggle_listen), ("选择声音来源", self.open_audio_settings))
        self.listen_button.setProperty("variant", "primary")
        source_button.setProperty("variant", "quiet")
        content.addWidget(connection)

        recent = Q.QFrame()
        recent.setObjectName("recentCard")
        recent_layout = Q.QVBoxLayout(recent)
        recent_layout.setContentsMargins(25, 18, 25, 20)
        recent_layout.setSpacing(11)
        caption = Q.QLabel("上一句弹幕")
        caption.setObjectName("sectionText")
        recent_header = Q.QHBoxLayout()
        recent_header.addWidget(caption, 1)
        self.repeat_key = Q.QLabel("Ctrl+Shift+F9")
        self.repeat_key.setObjectName("keyboardHint")
        recent_header.addWidget(self.repeat_key)
        self.repeat_button = Q.QPushButton("重看")
        self.repeat_button.clicked.connect(self.repeat_last)
        self.repeat_button.setEnabled(False)
        recent_header.addWidget(self.repeat_button)
        recent_layout.addLayout(recent_header)
        self.home_line = Q.QLabel("等待关键词命中")
        self.home_line.setTextFormat(C.Qt.PlainText)
        self.home_line.setWordWrap(True)
        self.home_line.setObjectName("recentText")
        self.home_line.setProperty("empty", True)
        recent_layout.addWidget(self.home_line)
        recent.setMinimumHeight(125)
        content.addWidget(recent)
        content.addStretch(1)

    def toggle_listen(self):
        if self.listener:
            self.stop_listen()
            return
        self.refresh_processes()
        if self.process.currentData() is None:
            self.open_audio_settings()
            return
        self.start_listen()

    def open_audio_settings(self):
        self.open_settings()
        self.settings_list.setCurrentRow(0)
        self.process.setFocus()

    def update_source(self):
        process = self.process.currentData()
        name = self.source if self.listener else (process[1] if process else "")
        self.home_source.setText(f"声音来源 · {name}" if name else "在设置中选择声音来源")
        if process:
            self.settings.setValue("selected_source", process[1])

    def button_row(self, layout, *actions):
        row = Q.QHBoxLayout()
        buttons = []
        for name, callback in actions:
            button = Q.QPushButton(name)
            button.clicked.connect(callback)
            row.addWidget(button)
            buttons.append(button)
        row.addStretch(1)
        layout.addLayout(row)
        return buttons

    def build_listen(self):
        layout = self.page("音频与诊断")
        self.process = Q.QComboBox()
        self.process.currentIndexChanged.connect(self.update_source)
        layout.addWidget(Q.QLabel("声音来源 · 请选择应用进程"))
        layout.addWidget(self.process)
        self.button_row(layout, ("刷新应用", self.refresh_processes))
        self.status = Q.QLabel("未监听")
        layout.addWidget(self.status)
        self.volume = Q.QProgressBar()
        self.volume.setTextVisible(False)
        layout.addWidget(self.volume)
        self.transcript = Q.QPlainTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText("最近一句原始转写")
        layout.addWidget(self.transcript, 1)
        self.match_label = Q.QLabel("命中关键词 · 无")
        self.match_label.setTextFormat(C.Qt.PlainText)
        layout.addWidget(self.match_label)
        saved = self.settings.value("sensevoice_model", "", type=str)
        self.model = Q.QLineEdit(saved or str(DEFAULT_MODEL))
        self.listening_model()
        layout.addWidget(Q.QLabel("本地 SenseVoice 中英识别模型目录"))
        layout.addWidget(self.model)
        self.button_row(layout, ("选择目录", self.choose_model))

    def choose_model(self):
        path = Q.QFileDialog.getExistingDirectory(self, "选择 SenseVoice 模型目录")
        if path:
            self.model.setText(path)

    def refresh_processes(self):
        previous = self.process.currentData()
        preferred = self.settings.value("selected_source", "")
        self.process.blockSignals(True)
        self.process.clear()
        try:
            entries = running_processes()
            names_by_pid = {pid: name.casefold() for name, pid, _ in entries}
            processes = [(name, pid) for name, pid, parent in entries
                         if name and pid and pid != os.getpid()
                         and names_by_pid.get(parent) != name.casefold()
                         and name.casefold() not in ("oopz-overlay2.exe", "oopz-runner.exe")]
            priorities = lambda entry: (not any(term in entry[0].casefold()
                                                for term in ("kook", "kaihei", "oopz")), entry[0].casefold())
            self.process.addItem("选择声音来源", None)
            for name, pid in sorted(processes, key=priorities):
                self.process.addItem(f"{name}   ·   {pid}", (pid, Path(name).stem))
            candidates = [index for index in range(1, self.process.count())
                          if self.process.itemData(index)[1] == preferred]
            for index in range(self.process.count()):
                if previous and self.process.itemData(index) == previous:
                    self.process.setCurrentIndex(index)
                    break
            else:
                if candidates:
                    self.process.setCurrentIndex(candidates[0])
        except OSError as error:
            self.process.addItem("暂时无法读取进程")
            self.process.setItemData(0, str(error), C.Qt.ToolTipRole)
        finally:
            self.process.blockSignals(False)
            self.update_source()

    def listening_model(self):
        configured = self.model.text().strip()
        if configured:
            model = ROOT / configured
            if all((model / file).is_file() for file in MODEL_FILES):
                return model
        if all((DEFAULT_MODEL / file).is_file() for file in MODEL_FILES):
            self.model.setText(str(DEFAULT_MODEL))
            return DEFAULT_MODEL
        return None

    def missing_model_message(self):
        if (ROOT / "runtime" / "pythonw.exe").is_file():
            return "找不到随包模型，请完整解压免安装包，并确认 models 文件夹与麦来.exe 同级。"
        return "SenseVoice 模型未安装完整，请运行「安装依赖和模型.ps1」。"

    def start_listen(self):
        if self.listener:
            return
        process = self.process.currentData()
        if not process:
            self.set_status("请先选择声音来源。")
            return
        model = self.listening_model()
        if model is None:
            self.set_status(self.missing_model_message())
            return
        self.settings.setValue("sensevoice_model", "" if model == DEFAULT_MODEL else str(model))
        pid, self.source = process
        self.listener = Listener(pid, model, self)
        self.listener.level.connect(self.volume.setValue)
        self.listener.level.connect(self.home_volume.setValue)
        self.activity.samples.clear()
        self.listener.timed_sentence.connect(self.on_sentence)
        self.sync_replay()
        self.listener.status.connect(self.set_status)
        self.listener.finished.connect(self.on_finished)
        self.set_status("正在加载离线模型…")
        self.listener.start()

    def stop_listen(self):
        if self.listener:
            self.listener.stop.set()
            self.listener.record_replay.clear()
            self.voice_replay.stop()
            self.set_status("正在停止…")

    def on_finished(self):
        self.listener.deleteLater()
        self.listener = None
        self.volume.setValue(0)
        self.home_volume.reset()
        self.update_source()
        if not self.status.text().startswith("监听失败"):
            status = "未监听"
        else:
            status = self.status.text()
        self.set_status(status)
        if self.quitting and not self.microphone_listener:
            Q.QApplication.quit()

    def set_status(self, text):
        self.status.setText(text)
        self.home_status.setText(text)
        self.status_dot.setProperty("active", text == "正在监听")
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)
        self.listen_button.setText("停止监听" if self.listener else "开始监听")
        self.listen_button.setEnabled(text != "正在停止…")
        if hasattr(self, "tray"):
            self.tray.setToolTip(f"{BRAND} · {text}")

    def sound_enabled_for(self, word, overrides):
        return overrides.get(word, word in delta_pack.SOUND_WORDS)

    def on_sentence(self, text, start=0.0, end=0.0, pcm=b"", *, microphone=False):
        text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
        original = text
        speaker = self.activity.identify(start, end) if not microphone and self.kook_nicknames_enabled() else None
        name = "我（麦克风）" if microphone else speaker or getattr(self, "source", "试播")
        self.transcript.setPlainText(f"{name}：{text}")
        state = self.store.snapshot()
        enabled_words = set(state["words"])
        overrides = self.settings.value("sound_word_overrides", {}, type=dict)
        sound_words = {word for word in enabled_words if self.sound_enabled_for(word, overrides)}
        for short_call in ("左边", "右边"):
            if short_call not in enabled_words and short_call + "有人" in sound_words:
                sound_words.add(short_call)
        text, matches = match_words(text, state["words"], sound_words, DELTA_LATIN_NAMES)
        label = f"{name}：{text}"
        directions = {direction(cue.group()) for cue in CUE_PATTERN.finditer(fold(text))}
        for short_call in ("左边", "右边"):
            expanded = short_call + "有人"
            if (expanded in enabled_words and expanded not in matches
                    and short_call not in matches and direction(short_call) in directions):
                matches.append(expanded)
        self.match_label.setText("命中关键词 · " + ("、".join(matches) or "无"))
        now = time.monotonic()
        threshold = now - BURST_WINDOW_SECONDS
        self.burst_hits = {key: [hit for hit in times if hit > threshold]
                           for key, times in self.burst_hits.items() if times[-1] > threshold}
        capped = False
        cooling = False
        result = "未命中"
        fun = self.mode.currentData() == "fun"
        preset = self.settings.value("delta_preset", state.get("default_delta", False), type=bool)
        for word in sorted(matches, key=lambda value: (
                {"prank": 0, "signal": 1, "urgent": 1, "gold": 2}.get(
                    state["effects"].get(value, DEFAULT_EFFECT)[0], 3) if fun else 0, -len(value))):
            style, cooldown, glyph, position = effect_fields(state, word)
            if not fun:
                if style == "prank":
                    position = "scroll"
                style = "normal"
            signature = (style, cooldown, glyph, position)
            canonical = delta_pack.ALIASES.get(word, word) if preset else word
            cooldown_key = canonical.casefold()
            previous = self.last_hit.get(cooldown_key)
            if previous and previous[0] == signature and now - previous[1] < cooldown:
                cooling = True
                continue
            if position == "auto":
                position = direction(word) or direction(text) or "scroll"
            side = direction(word) or (position if position in ("left", "right") else None)
            burst_key = ("direction", side) if side else ("keyword", cooldown_key)
            hits = self.burst_hits.get(burst_key, [])
            if len(hits) >= MAX_BURST_CAPTIONS:
                capped = True
                continue
            if style == "prank":
                displayed = self.emit_overlay(label, "normal", "scroll")
                if state["friend_pranks"]:
                    displayed = self.emit_prank(glyph) or displayed
            else:
                displayed = self.emit_overlay(label, style, position)
            if displayed:
                self.last_hit[cooldown_key] = (signature, now)
                self.burst_hits[burst_key] = hits + [now]
                self.last_line = (label, position, pcm if self.replay_enabled() else b"")
                self.home_line.setText(label)
                self.home_line.setProperty("empty", False)
                self.home_line.style().unpolish(self.home_line)
                self.home_line.style().polish(self.home_line)
                self.repeat_button.setEnabled(True)
                played = self.replay_enabled() and self.voice_replay.play(pcm)
                if fun and self.sound_enabled.isChecked() and not played:
                    self.play_sound()
                result = "已显示弹幕"
                break
        if capped and result != "已显示弹幕":
            self.match_label.setText(self.match_label.text() + " · 防刷屏")
            result = "命中，防刷屏"
        elif matches and result != "已显示弹幕":
            result = "命中，冷却中" if cooling else "命中，未显示"
        if self.debug_button.isChecked():
            when = datetime.now().strftime("%H:%M:%S")
            correction = f"\n纠正后 · {text}" if text != original else ""
            words = "、".join(matches) or "无"
            self.debug_log.appendPlainText(
                f"{when} · {name}\n{original}{correction}\n关键词 · {words}    {result}\n")

    def repeat_last(self):
        if self.last_line is None:
            return
        label, position, pcm = self.last_line
        if self.emit_overlay(label, "normal", "scroll" if position == "auto" else position):
            if self.replay_enabled():
                self.voice_replay.play(pcm)

    def build_words(self):
        layout = self.page("关键词")
        self.search = Q.QLineEdit()
        self.search.setPlaceholderText("搜索关键词")
        self.search.textChanged.connect(lambda: self.refresh_words(force=True))
        layout.addWidget(self.search)
        self.word_list = Q.QListWidget()
        self.word_list.setMinimumHeight(165)
        self.word_list.itemDoubleClicked.connect(lambda _: self.rename_word())
        layout.addWidget(self.word_list)
        self.button_row(layout, ("添加或批量粘贴", self.add_words), ("修改", self.rename_word),
                        ("删除", self.delete_word), ("匹配与弹幕设置", self.configure_effect))
        self.button_row(layout, ("导入 TXT", self.import_words), ("导出 TXT", self.export_words))

    def build_presets(self):
        layout = self.page("词包与试用")
        title = Q.QLabel(f"三角洲行动 · {len(delta_pack.WORDS)} 条关键词")
        title.setObjectName("sectionText")
        layout.addWidget(title)
        self.button_row(layout, ("添加左右报点规则", self.add_directions))
        self.button_row(layout, ("加载三角洲词包", self.load_delta_pack),
                        ("试播「东楼有牢赛」", self.preview_delta))
        self.preset_status = Q.QLabel()
        layout.addWidget(self.preset_status)
        layout.addStretch(1)

    def load_delta_pack(self):
        def load():
            added = self.store.add_preset(delta_pack.WORDS, delta_pack.EFFECTS)
            self.settings.setValue("delta_preset", True)
            self.preset_status.setText(f"三角洲词包已加载 · 新增 {added} 个词")
        self.edit_safely(load)

    def preview_delta(self):
        if "牢赛" not in self.store.snapshot()["words"]:
            self.preset_status.setText("先加载三角洲词包，再试播整句。")
            return
        self.on_sentence("东楼有牢赛")

    def add_directions(self):
        def add():
            for word in ("左边", "右边"):
                with self.store.lock:
                    self.store.edit("add", word, "本机")
                    if word not in self.store.snapshot()["effects"]:
                        self.store.effect(word, "signal", 2, "区", position="auto")
        self.edit_safely(add)

    def refresh_words(self, force=False):
        snapshot = self.store.snapshot()
        if not force and snapshot["rev"] == self.revision:
            if self.link.text() and not self.store.authorized(snapshot["token"]):
                self.update_link()
            return
        self.revision = snapshot["rev"]
        selected = self.word_list.currentItem()
        selected_word = selected.text() if selected else None
        self.word_list.clear()
        self.word_list.addItems([word for word in snapshot["words"]
                                 if self.search.text().casefold() in word.casefold()])
        for index in range(self.word_list.count()):
            item = self.word_list.item(index)
            style, cooldown, glyph, position = effect_fields(snapshot, item.text())
            if style != "normal" or cooldown or position != "scroll":
                item.setToolTip(f"{EFFECTS[style]} · {POSITIONS[position]} · 冷却 {cooldown} 秒"
                                + (f" · {glyph}" if style == "prank" else ""))
        if selected_word:
            found = self.word_list.findItems(selected_word, C.Qt.MatchExactly)
            if found:
                self.word_list.setCurrentItem(found[0])
        self.history.clear()
        for date, actor, action, word in reversed(snapshot["history"]):
            label = {"add": "添加", "delete": "删除", "effect": "设置特效"}[action]
            item = Q.QListWidgetItem(f"{date.replace('T', ' ')}   {actor}   {label}「{word}」")
            item.setData(C.Qt.UserRole, (action, word))
            self.history.addItem(item)
        selected = {item.data(C.Qt.UserRole) for item in self.pending_list.selectedItems()}
        self.pending_list.clear()
        self.pending_title.setText(f"待审核建议 · {len(snapshot['pending'])}")
        for proposal in snapshot["pending"]:
            action = proposal["action"]
            detail = {"add": "新增", "delete": "删除", "effect": "修改特效"}[action]
            if action == "effect":
                style, cooldown, glyph, position = proposal["effect"]
                detail += f" · {EFFECTS[style]} · {POSITIONS[position]} · {cooldown} 秒冷却"
                if style == "prank":
                    detail += f" · 大字「{glyph}」"
            item = Q.QListWidgetItem(f"「{proposal['word']}」  {detail}")
            item.setData(C.Qt.UserRole, proposal["id"])
            self.pending_list.addItem(item)
            item.setSelected(proposal["id"] in selected)
        self.update_link()

    def edit_safely(self, callback):
        try:
            callback()
        except (ValueError, OSError) as error:
            Q.QMessageBox.warning(self, "词库", str(error))
        self.refresh_words()

    def configure_effect(self):
        item = self.word_list.currentItem()
        if not item:
            return
        word = item.text()
        style, cooldown, glyph, position = effect_fields(self.store.snapshot(), word)
        dialog = Q.QDialog(self)
        dialog.setWindowTitle(f"「{word}」的弹幕")
        form = Q.QFormLayout(dialog)
        choices = Q.QComboBox()
        for key, label in EFFECTS.items():
            choices.addItem(label, key)
        choices.setCurrentIndex(choices.findData(style))
        placement = self.position_picker(position)
        placement.setEnabled(style != "prank")
        choices.currentIndexChanged.connect(lambda: placement.setEnabled(choices.currentData() != "prank"))
        delay = Q.QSpinBox()
        delay.setRange(0, 120)
        delay.setValue(cooldown)
        character = Q.QLineEdit(glyph)
        character.setMaxLength(1)
        overrides = self.settings.value("sound_word_overrides", {}, type=dict)
        sound_match = Q.QCheckBox("用同音和近音转写触发")
        sound_match.setChecked(self.sound_enabled_for(word, overrides))
        form.addRow("特效", choices)
        form.addRow("出场位置", placement)
        form.addRow("冷却秒数", delay)
        form.addRow("整蛊大字", character)
        form.addRow("读音匹配", sound_match)
        buttons = Q.QDialogButtonBox(Q.QDialogButtonBox.Save | Q.QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec_():
            def save():
                self.store.effect(word, choices.currentData(), delay.value(), character.text() or "区",
                                  position=placement.currentData())
                overrides[word] = sound_match.isChecked()
                self.settings.setValue("sound_word_overrides", overrides)
            self.edit_safely(save)

    def add_words(self):
        text, ok = Q.QInputDialog.getMultiLineText(self, "添加关键词", "一行一个关键词")
        if ok:
            self.edit_safely(lambda: self.store.set_words([s for s in text.splitlines() if s.strip()], True))

    def rename_word(self):
        item = self.word_list.currentItem()
        if item:
            original = item.text()
            text, ok = Q.QInputDialog.getText(self, "修改关键词", "关键词", text=original)
            if ok:
                self.edit_safely(lambda: self.store.rename(original, text))

    def delete_word(self):
        item = self.word_list.currentItem()
        if item:
            self.edit_safely(lambda: self.store.edit("delete", item.text(), "本机"))

    def import_words(self):
        path, _ = Q.QFileDialog.getOpenFileName(self, "导入词库", "", "文本文件 (*.txt)")
        if not path:
            return
        try:
            file = Path(path)
            if file.stat().st_size > 1024 * 1024:
                raise ValueError("导入文件不得超过 1 MB")
            incoming = [clean(line) for line in file.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        except (OSError, ValueError) as error:
            Q.QMessageBox.warning(self, "导入失败", str(error))
            return
        box = Q.QMessageBox(self)
        box.setWindowTitle("导入预览")
        box.setText(f"读取到 {len(incoming)} 行关键词")
        box.setDetailedText("\n".join(incoming))
        merge = box.addButton("合并去重", Q.QMessageBox.AcceptRole)
        replace = box.addButton("替换词库", Q.QMessageBox.DestructiveRole)
        box.addButton(Q.QMessageBox.Cancel)
        box.exec_()
        clicked = box.clickedButton()
        if clicked in (merge, replace):
            self.edit_safely(lambda: self.store.set_words(incoming, clicked == merge))

    def export_words(self):
        path, _ = Q.QFileDialog.getSaveFileName(self, "导出词库", "关键词.txt", "文本文件 (*.txt)")
        if path:
            self.edit_safely(lambda: Path(path).write_text(
                "\n".join(self.store.snapshot()["words"]) + "\n", encoding="utf-8"))

    def build_share(self):
        layout = self.page("共享")
        self.tunnel_url = ""
        self.tunnel_output = ""
        self.tunnel = C.QProcess(self)
        self.tunnel.setProcessChannelMode(C.QProcess.MergedChannels)
        self.tunnel.readyReadStandardOutput.connect(self.read_tunnel)
        self.tunnel.finished.connect(self.tunnel_finished)
        self.tunnel.errorOccurred.connect(lambda _: self.tunnel_finished())
        self.tunnel_timer = C.QTimer(self)
        self.tunnel_timer.setSingleShot(True)
        self.tunnel_timer.timeout.connect(self.tunnel_timeout)
        self.external = Q.QLineEdit(str(self.settings.value("public_url", "")))
        self.external.setPlaceholderText("https://你的转发地址")
        self.external.textChanged.connect(self.update_link)
        self.external.editingFinished.connect(lambda: self.settings.setValue("public_url", self.external.text().strip()))
        layout.addWidget(Q.QLabel("公网 HTTPS 转发地址 · 留空仅在本机预览"))
        layout.addWidget(self.external)
        self.link = Q.QLineEdit()
        self.link.setReadOnly(True)
        layout.addWidget(self.link)
        self.share_status = Q.QLabel()
        self.share_status.setWordWrap(True)
        layout.addWidget(self.share_status)
        self.share_mode = Q.QComboBox()
        self.share_mode.addItem("提交建议 · 审核后生效", "suggest")
        self.share_mode.addItem("限时共编 · 即时生效", "direct")
        self.share_mode.currentIndexChanged.connect(self.update_share_controls)
        self.share_minutes = Q.QSpinBox()
        self.share_minutes.setRange(5, 240)
        self.share_minutes.setValue(60)
        self.share_minutes.setSuffix(" 分钟")
        self.share_words = Q.QCheckBox("允许新增和删除词条")
        self.share_words.setChecked(True)
        self.share_effects = Q.QCheckBox("允许配置词条特效")
        self.share_effects.setChecked(True)
        link_options = Q.QFormLayout()
        link_options.addRow("新链接权限", self.share_mode)
        link_options.addRow("共编时长", self.share_minutes)
        layout.addLayout(link_options)
        permissions = Q.QHBoxLayout()
        permissions.addWidget(self.share_words)
        permissions.addWidget(self.share_effects)
        layout.addLayout(permissions)
        self.update_share_controls()
        self.button_row(layout, ("生成新链接", self.create_link), ("复制", self.copy_link),
                        ("本机预览", self.preview_link), ("撤销链接", self.revoke_link))
        self.button_row(layout, ("生成临时公网链接", self.start_tunnel))
        self.prank_toggle = Q.QCheckBox("在本机启用单挑大字")
        self.prank_toggle.setChecked(self.store.snapshot()["friend_pranks"])
        self.prank_toggle.toggled.connect(self.toggle_pranks)
        layout.addWidget(self.prank_toggle)
        self.prank_help = Q.QLabel()
        layout.addWidget(self.prank_help)
        self.pending_title = Q.QLabel("待审核建议")
        layout.addWidget(self.pending_title)
        self.pending_list = Q.QListWidget()
        self.pending_list.setSelectionMode(Q.QAbstractItemView.ExtendedSelection)
        self.pending_list.setMinimumHeight(100)
        layout.addWidget(self.pending_list, 1)
        self.button_row(layout, ("通过所选", lambda: self.review_suggestions(True)),
                        ("拒绝所选", lambda: self.review_suggestions(False)))
        layout.addWidget(Q.QLabel("编辑记录"))
        self.history = Q.QListWidget()
        layout.addWidget(self.history, 1)
        self.button_row(layout, ("恢复选中的删除项", self.restore_word))

    def update_share_controls(self):
        direct = self.share_mode.currentData() == "direct"
        self.share_minutes.setEnabled(direct)
        self.share_effects.setChecked(not direct)

    def review_suggestions(self, approved):
        selected = [item.data(C.Qt.UserRole) for item in self.pending_list.selectedItems()]
        errors = []
        for change_id in selected:
            try:
                self.store.review(change_id, approved)
            except (ValueError, OSError) as error:
                errors.append(str(error))
        self.refresh_words()
        if errors:
            Q.QMessageBox.warning(self, "部分建议未处理", "\n".join(dict.fromkeys(errors)))

    def local_base(self):
        return f"http://127.0.0.1:{self.server.server_port}" if self.server else ""

    def update_link(self):
        snapshot = self.store.snapshot()
        token = snapshot["token"]
        active = self.store.authorized(token)
        external = self.external.text().strip().rstrip("/")
        try:
            url = urlsplit(external)
            valid = bool(url.scheme == "https" and url.hostname and not url.username
                         and not url.password and not url.query and not url.fragment and not url.path)
        except ValueError:
            valid = False
        base = self.tunnel_url or ((external if valid else "") if external else self.local_base())
        self.link.setText(f"{base}/edit/{token}/" if base and active and self.server else "")
        kind = "建议链接 · 审核后生效"
        if snapshot["share_mode"] == "direct" and active:
            deadline = datetime.fromtimestamp(snapshot["share_expires"]).strftime("%m-%d %H:%M")
            kind = f"限时共编 · {deadline} 到期"
        if self.tunnel_url:
            self.share_status.setText(kind + " · 公网可访问" if active else "链接已过期，请生成新链接。")
        elif self.tunnel.state() != C.QProcess.NotRunning:
            self.share_status.setText("正在建立临时公网通道…")
        elif external and not valid:
            self.share_status.setText("请输入不带路径的 HTTPS 转发地址。")
        elif self.server:
            self.share_status.setText((kind + "。 " if active else "链接已过期或未启用。 ")
                                      + f"转发目标 {self.local_base()}。"
                                      + ("公网地址已填写，连通性由转发服务决定。" if external
                                         else "当前链接仅本机可打开。"))
        else:
            self.share_status.setText("生成链接后启动本机词库服务。退出麦来后页面不可用。")

    def create_link(self, reuse=False):
        def start():
            token = self.store.snapshot()["token"]
            if not (reuse and self.store.authorized(token)) and not (
                    self.share_words.isChecked() or self.share_effects.isChecked()):
                raise ValueError("请至少选择一项链接权限")
            if not self.server:
                self.server = serve(self.store)
            if not reuse or not self.store.authorized(token):
                self.store.rotate(True, self.share_mode.currentData(), self.share_minutes.value(),
                                  self.share_words.isChecked(), self.share_effects.isChecked())
            self.update_link()
        self.edit_safely(start)

    def copy_link(self):
        if self.link.text():
            Q.QApplication.clipboard().setText(self.link.text())

    def preview_link(self):
        token = self.store.snapshot()["token"]
        if self.store.authorized(token) and self.server:
            G.QDesktopServices.openUrl(C.QUrl(f"{self.local_base()}/edit/{token}/"))

    def revoke_link(self):
        def revoke():
            self.store.rotate(False)
            self.tunnel_url = ""
            self.tunnel_timer.stop()
            if self.tunnel.state() != C.QProcess.NotRunning:
                self.tunnel.kill()
            self.update_link()
        self.edit_safely(revoke)

    def toggle_pranks(self, enabled):
        self.edit_safely(lambda: self.store.allow_pranks(enabled))
        if not enabled:
            self.clear_prank()

    def disable_pranks(self):
        self.prank_toggle.setChecked(False)
        self.clear_effects()
        self.voice_replay.stop()

    def clear_effects(self):
        self.clear_prank()
        winsound.PlaySound(None, 0)
        for overlay in self.overlays.copy():
            overlay.animation.stop()
            self.remove_overlay(overlay)

    def change_mode(self):
        mode = self.mode.currentData()
        self.settings.setValue("display_mode", mode)
        self.tray_modes[mode].setChecked(True)
        self.tray_prank_preview.setEnabled(mode == "fun")
        if mode == "clean":
            self.clear_effects()
        self.update_mode_status()
        self.sync_replay()

    def update_mode_status(self):
        fun = self.mode.currentData() == "fun"
        self.mode_hint.setText("娱乐模式：按词条设置播放样式和提示音。"
                               if fun else "纯净模式：只显示普通文字，保留出场方向。")
        self.sound_enabled.setEnabled(fun)
        self.preview_style.setEnabled(fun)
        self.preview_position.setEnabled(not fun or self.preview_style.currentData() != "prank")
        self.preview_prank_button.setEnabled(fun)
        self.preview_sound_button.setEnabled(fun)

    def start_tunnel(self):
        if self.tunnel.state() != C.QProcess.NotRunning:
            return
        bundled = ROOT / "cloudflared.exe"
        executable = str(bundled) if bundled.is_file() else shutil.which("cloudflared")
        if not executable:
            self.share_status.setText("请安装 cloudflared，或将 cloudflared.exe 放到启动脚本所在目录。")
            return
        self.create_link(reuse=True)
        if not self.server or not self.store.authorized(self.store.snapshot()["token"]):
            return
        self.tunnel_output = ""
        self.tunnel.start(executable, ["tunnel", "--no-autoupdate", "--protocol", "http2",
                                       "--url", self.local_base()])
        self.tunnel_timer.start(35000)
        self.update_link()

    def read_tunnel(self):
        output = bytes(self.tunnel.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.tunnel_output = (self.tunnel_output + output)[-8192:]
        match = re.search(r"\|\s+(https://[a-z0-9-]+\.trycloudflare\.com)\s+\|", self.tunnel_output)
        if match:
            self.tunnel_url = match.group(1)
            self.tunnel_timer.stop()
            self.update_link()

    def tunnel_timeout(self):
        if self.tunnel.state() != C.QProcess.NotRunning:
            self.tunnel.kill()

    def tunnel_finished(self, *_):
        self.tunnel_timer.stop()
        self.tunnel_url = ""
        self.update_link()
        if self.store.snapshot()["token"]:
            self.share_status.setText("临时公网通道已关闭或连接失败。本机链接仍可使用。")

    def restore_word(self):
        item = self.history.currentItem()
        if item:
            action, word = item.data(C.Qt.UserRole)
            if action == "delete":
                self.edit_safely(lambda: self.store.edit("add", word, "本机恢复"))

    def build_overlay(self):
        layout = self.page("弹幕")
        fields = Q.QFormLayout()
        layout.addLayout(fields)
        self.size = self.spin(fields, "字号", "size", 14, 64, 31)
        self.offset = self.spin(fields, "距屏幕顶端", "offset", 0, 700, 45)
        self.speed = self.spin(fields, "飘过时长（秒）", "duration", 2, 15, 6)
        self.color = G.QColor(str(self.settings.value("color", DEFAULT_DANMAKU_COLOR)))
        if not self.color.isValid():
            self.color = G.QColor(DEFAULT_DANMAKU_COLOR)
        self.color_button = Q.QPushButton(self.color.name())
        self.color_button.clicked.connect(self.pick_color)
        fields.addRow("颜色", self.color_button)
        self.sample = Q.QLineEdit("队友：缺一，速来！")
        self.sample.setMaxLength(300)
        fields.addRow("试播文字", self.sample)
        self.preview_style = Q.QComboBox()
        for key, label in EFFECTS.items():
            self.preview_style.addItem(label, key)
        self.preview_position = self.position_picker("scroll")
        self.preview_style.currentIndexChanged.connect(
            lambda: self.update_mode_status())
        fields.addRow("试播样式", self.preview_style)
        fields.addRow("试播位置", self.preview_position)
        self.sound_enabled = Q.QCheckBox("命中关键词时播放提示音")
        self.sound_enabled.setChecked(self.settings.value("sound_enabled", True, type=bool))
        self.sound_enabled.toggled.connect(lambda enabled: self.settings.setValue("sound_enabled", enabled))
        fields.addRow("提示音", self.sound_enabled)
        self.replay_checkbox = Q.QCheckBox("命中后回放整句原声")
        self.replay_checkbox.setChecked(self.settings.value("replay_enabled", False, type=bool))
        self.replay_checkbox.toggled.connect(self.change_replay)
        fields.addRow("原声回放", self.replay_checkbox)
        _, self.preview_prank_button, self.preview_sound_button = self.button_row(
                        layout, ("试播", self.play_preview),
                        ("试播大字", self.preview_prank),
                        ("试听提示音", self.play_sound))
        self.mode_hint = Q.QLabel()
        self.mode_hint.setWordWrap(True)
        layout.addWidget(self.mode_hint)
        self.preview_hotkey_hint = Q.QLabel()
        self.preview_hotkey_hint.setObjectName("secondaryText")
        self.preview_hotkey_hint.setWordWrap(True)
        layout.addWidget(self.preview_hotkey_hint)
        self.update_mode_status()
        layout.addStretch()

    def play_sound(self):
        try:
            winsound.PlaySound(str(ROOT / "ping.wav"), winsound.SND_FILENAME |
                               winsound.SND_ASYNC | winsound.SND_NODEFAULT | winsound.SND_NOSTOP)
        except RuntimeError:
            pass

    def replay_enabled(self):
        return self.replay_checkbox.isChecked()

    def change_replay(self, enabled):
        self.settings.setValue("replay_enabled", enabled)
        if not enabled and self.last_line:
            self.last_line = (*self.last_line[:2], b"")
        self.sync_replay()

    def sync_replay(self):
        enabled = self.replay_enabled()
        if self.listener:
            if enabled:
                self.listener.record_replay.set()
            else:
                self.listener.record_replay.clear()
        if not enabled:
            self.voice_replay.stop()

    def build_speakers(self):
        layout = self.page("队友昵称")
        self.speaker_enable = Q.QCheckBox("根据 KOOK 覆盖层的发言高亮显示昵称")
        self.speaker_enable.setChecked(self.settings.value("speakers_enabled", False, type=bool))
        self.speaker_enable.toggled.connect(self.enable_speakers)
        layout.addWidget(self.speaker_enable)
        help_text = Q.QLabel("保持 KOOK 桌面覆盖或 OBS 预览可见。为每位队友框选会变亮的边框或图标，"
                             "分别采样安静和发言状态。名单换位置后请重新校准。")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        self.speaker_list = Q.QListWidget()
        layout.addWidget(self.speaker_list, 1)
        self.button_row(layout, ("添加或重选区域", self.add_speaker),
                        ("删除队友", self.remove_speaker))
        self.button_row(layout, ("采样安静", lambda: self.begin_calibration("quiet")),
                        ("采样发言", lambda: self.begin_calibration("speaking")))
        self.speaker_status = Q.QLabel("请选择队友并完成两个状态的采样。")
        self.speaker_status.setWordWrap(True)
        layout.addWidget(self.speaker_status)
        self.refresh_speakers()

    def enable_speakers(self, enabled):
        self.settings.setValue("speakers_enabled", enabled)
        self.activity.samples.clear()

    def kook_nicknames_enabled(self):
        source = getattr(self, "source", "").casefold()
        return self.speaker_enable.isChecked() and ("kook" in source or "kaihei" in source)

    def profile_data(self):
        return {name: {**profile, **{kind: base64.b64encode(profile[kind]).decode("ascii")
                    for kind in ("quiet", "speaking") if isinstance(profile.get(kind), bytes)}}
                for name, profile in self.speaker_profiles.items()}

    def save_speakers(self):
        self.settings.setValue("speaker_profiles", json.dumps(self.profile_data(), ensure_ascii=False))

    def refresh_speakers(self, selected=None):
        prior = self.speaker_list.currentItem()
        selected = selected or (prior.data(C.Qt.UserRole) if prior else None)
        self.speaker_list.clear()
        for name, profile in self.speaker_profiles.items():
            missing = [label for kind, label in (("quiet", "安静"), ("speaking", "发言")) if not profile.get(kind)]
            item = Q.QListWidgetItem(f"{name} · {'待采样 ' + ' / '.join(missing) if missing else '已校准'}")
            item.setData(C.Qt.UserRole, name)
            self.speaker_list.addItem(item)
            if selected == name:
                self.speaker_list.setCurrentItem(item)

    def add_speaker(self):
        current = self.speaker_list.currentItem()
        initial = current.data(C.Qt.UserRole) if current else ""
        name, ok = Q.QInputDialog.getText(self, "队友昵称", "输入浮窗中的昵称", text=initial)
        name = name.strip()[:40]
        if not ok or not name:
            return
        screen = self.screen()
        self.hide()
        Q.QApplication.processEvents()
        picker = RegionPicker(screen)
        accepted = picker.exec_()
        self.reopen()
        if accepted and picker.region:
            self.speaker_profiles[name] = {"screen": screen.name(), "region": picker.region}
            self.activity.samples.clear()
            self.save_speakers()
            self.refresh_speakers(name)
            self.speaker_status.setText("已选区域。先让队友安静并采样，再让他持续讲话并采样。")

    def remove_speaker(self):
        item = self.speaker_list.currentItem()
        if item:
            self.speaker_profiles.pop(item.data(C.Qt.UserRole), None)
            self.activity.samples.clear()
            self.save_speakers()
            self.refresh_speakers()

    def begin_calibration(self, kind):
        item = self.speaker_list.currentItem()
        if item and not self.calibration:
            name = item.data(C.Qt.UserRole)
            action = "保持安静" if kind == "quiet" else "持续讲话"
            self.speaker_status.setText(f"4 秒后采样。让 {name} {action}。")
            self.calibration = (name, kind, time.monotonic() + 4)
            if self.has_tray:
                self.hide()

    def read_profile(self, profile):
        screen = next((screen for screen in Q.QApplication.screens()
                       if screen.name() == profile["screen"]), None)
        if not screen:
            return None
        return fingerprint(screen.grabWindow(0, *profile["region"]).toImage())

    @staticmethod
    def reference(profile, kind):
        value = profile.get(kind)
        return base64.b64decode(value) if isinstance(value, str) else value

    def poll_speakers(self):
        now = time.monotonic()
        if self.calibration:
            name, kind, deadline = self.calibration
            if now < deadline:
                return
            self.calibration = None
            profile = self.speaker_profiles.get(name)
            sample = self.read_profile(profile) if profile else None
            if sample:
                opposite = self.reference(profile, "quiet" if kind == "speaking" else "speaking")
                if opposite and distance(opposite, sample) < 2:
                    result = "两个状态看起来相同。请缩小范围，框住会变化的边框或图标后重试。"
                else:
                    profile[kind] = sample
                    self.activity.samples.clear()
                    self.save_speakers()
                    self.refresh_speakers(name)
                    result = f"{name} 的{'安静' if kind == 'quiet' else '发言'}状态已采样。"
            else:
                result = "采样失败。请检查屏幕和覆盖层，重新框选。"
            self.speaker_status.setText(result)
            self.reopen()
            return
        if not self.listener or not self.kook_nicknames_enabled():
            return
        names = []
        for name, profile in self.speaker_profiles.items():
            quiet, speaking = self.reference(profile, "quiet"), self.reference(profile, "speaking")
            if quiet and speaking:
                current = self.read_profile(profile)
                if current and is_active(current, quiet, speaking):
                    names.append(name)
        self.activity.record(now, names)
        self.speaker_status.setText("当前高亮 · " + ("、".join(names) if names else "无"))

    def position_picker(self, current):
        picker = Q.QComboBox()
        for key, name in POSITIONS.items():
            picker.addItem(name, key)
        picker.setCurrentIndex(picker.findData(current))
        return picker

    def play_preview(self):
        style, position = self.preview_style.currentData(), self.preview_position.currentData()
        if self.mode.currentData() == "clean":
            style = "normal"
        if style == "prank":
            self.preview_prank()
            return
        text = self.sample.text()
        if position == "auto":
            position = direction(text) or "scroll"
        self.emit_overlay(text, style, position)

    def preview_prank(self):
        self.emit_prank("区", preview=True, screen=Q.QApplication.screenAt(G.QCursor.pos()))

    def spin(self, form, label, key, low, high, default):
        widget = Q.QSpinBox()
        widget.setRange(low, high)
        widget.setValue(self.settings.value(key, default, type=int))
        widget.valueChanged.connect(lambda value: self.settings.setValue(key, value))
        form.addRow(label, widget)
        return widget

    def pick_color(self):
        selected = Q.QColorDialog.getColor(self.color, self, "弹幕颜色")
        if selected.isValid():
            self.color = selected
            self.settings.setValue("color", selected.name())
            self.color_button.setText(selected.name())

    def emit_prank(self, glyph, preview=False, screen=None):
        if self.mode.currentData() != "fun":
            return False
        now = time.monotonic()
        if self.prank_overlay or (not preview and now - self.last_prank < 20):
            return False
        if not preview:
            self.last_prank = now
        self.prank_overlay = Overlay()
        self.prank_overlay.giant(glyph, screen or self.target_screen(), self.color.name())
        self.prank_timer.start(1500)
        return True

    def clear_prank(self):
        self.prank_timer.stop()
        if self.prank_overlay:
            self.prank_overlay.hide()
            self.prank_overlay.deleteLater()
            self.prank_overlay = None

    def target_screen(self):
        return self.screen() if self.isVisible() else (
            Q.QApplication.screenAt(G.QCursor.pos()) or Q.QApplication.primaryScreen())

    def emit_overlay(self, text, style="normal", position="scroll"):
        if not text.strip() or len(self.overlays) >= 4:
            return False
        screen = self.target_screen()
        group = "top" if position == "scroll" else position
        occupied = {overlay.lane for overlay in self.overlays if overlay.group == group}
        lane = next(i for i in range(4) if i not in occupied)
        overlay = Overlay()
        overlay.lane = lane
        overlay.group = group
        self.overlays.append(overlay)
        overlay.expiry.timeout.connect(lambda: self.remove_overlay(overlay))
        size = self.size.value()
        color = self.color.name()
        overlay.fly(text, size + (10 if style == "urgent" else 0), color, self.speed.value(),
                    self.offset.value(), screen, position, style, lane)
        overlay.expiry.start(self.speed.value() * 1000)
        return True

    def remove_overlay(self, overlay):
        self.overlays.remove(overlay)
        overlay.expiry.stop()
        overlay.hide()
        overlay.deleteLater()

    def reopen(self):
        self.showNormal()
        self.activateWindow()

    def changeEvent(self, event):
        super().changeEvent(event)
        if (event.type() == C.QEvent.WindowStateChange and self.isMinimized()
                and getattr(self, "has_tray", False)):
            C.QTimer.singleShot(0, self.hide_if_minimized)

    def hide_if_minimized(self):
        if self.isMinimized():
            self.hide()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if not self.has_tray:
            self.quit()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.stop_microphone()

    def quit(self):
        self.quitting = True
        self.voice_replay.stop()
        if self.hotkey_ready:
            ctypes.windll.user32.UnregisterHotKey(None, 47)
        if self.repeat_hotkey_ready:
            ctypes.windll.user32.UnregisterHotKey(None, 48)
        if self.preview_hotkey_ready:
            ctypes.windll.user32.UnregisterHotKey(None, 49)
        if self.tunnel.state() != C.QProcess.NotRunning:
            self.tunnel.kill()
            self.tunnel.waitForFinished(1000)
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.stop_microphone()
        if self.listener:
            self.stop_listen()
        elif not self.microphone_listener:
            Q.QApplication.quit()


def apply_theme(app):
    app.setFont(G.QFont("Microsoft YaHei UI", 10))
    palette = app.palette()
    for role, hex_color in (
        (G.QPalette.Window, "#111116"), (G.QPalette.Base, "#1c1b25"),
        (G.QPalette.AlternateBase, "#242130"), (G.QPalette.Text, "#efedf5"),
        (G.QPalette.WindowText, "#efedf5"), (G.QPalette.ButtonText, "#efedf5"),
        (G.QPalette.Highlight, "#4b3866"), (G.QPalette.HighlightedText, "#ffffff"),
    ):
        palette.setColor(role, G.QColor(hex_color))
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLE)


def main():
    app = Q.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    window = Window()
    window.show()
    C.QTimer.singleShot(0, window.show_first_run_guide)
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
