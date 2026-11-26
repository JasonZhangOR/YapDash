import json
import os
import secrets
import threading
import time
import unicodedata
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import delta_pack


def clean(value):
    if not isinstance(value, str):
        raise ValueError("请输入文字关键词")
    value = " ".join(value.split())
    if not value or len(value) > 80:
        raise ValueError("每个关键词需要 1 到 80 个字符")
    return value


class Words:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        if path.exists():
            self.data = json.loads(path.read_text(encoding="utf-8"))
        else:
            self.data = {"words": delta_pack.WORDS.copy(), "token": "", "history": [], "rev": 0,
                         "default_delta": True, "effects": {word: [style, delay, "区", position]
                         for word, (style, delay, position) in delta_pack.EFFECTS.items()}}
        self.data.setdefault("effects", {})
        self.data.setdefault("friend_pranks", False)
        self.data.setdefault("share_mode", "suggest")
        self.data.setdefault("share_expires", 0)
        self.data.setdefault("share_words", True)
        self.data.setdefault("share_effects", True)
        self.data.setdefault("pending", [])

    def save(self, **changes):
        data = {**self.data, **changes, "rev": self.data["rev"] + 1}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.path)
        self.data = data

    def snapshot(self):
        with self.lock:
            return self.data.copy()

    def set_words(self, values, merge=False):
        with self.lock:
            words = self.data["words"] + values if merge else values
            unique_by_key = {}
            for word in map(clean, words):
                unique_by_key.setdefault(word.casefold(), word)
            unique = list(unique_by_key.values())
            if len(unique) > 2000:
                raise ValueError("最多保存 2000 个关键词")
            self.save(words=unique, effects={word: effect for word, effect in
                      self.data["effects"].items() if word in unique})

    def rename(self, original, new_word):
        with self.lock:
            new_word = clean(new_word)
            words = self.data["words"]
            if original not in words:
                raise ValueError("关键词已被删除")
            if any(word != original and word.casefold() == new_word.casefold() for word in words):
                raise ValueError("已有同名关键词")
            effects = self.data["effects"].copy()
            if original in effects:
                effects[new_word] = effects.pop(original)
            self.save(words=[new_word if word == original else word for word in words], effects=effects)

    def add_preset(self, words, effects):
        with self.lock:
            existing = self.data["words"]
            canonical = {word.casefold(): word for word in existing}
            for word in words:
                canonical.setdefault(word.casefold(), word)
            if len(canonical) > 2000:
                raise ValueError("词库已满")
            updated = self.data["effects"].copy()
            for word, (style, cooldown, position) in effects.items():
                updated.setdefault(canonical[word.casefold()], [style, cooldown, "区", position])
            self.save(words=list(canonical.values()), effects=updated)
            return len(canonical) - len(existing)

    def edit(self, action, word, actor, pending=None):
        with self.lock:
            extra = {} if pending is None else {"pending": pending}
            word = clean(word)
            words = self.data["words"].copy()
            existing = next((item for item in words if item.casefold() == word.casefold()), None)
            if action == "add":
                if existing:
                    if extra:
                        self.save(**extra)
                    return
                if len(words) >= 2000:
                    raise ValueError("词库已满")
                words.append(word)
            elif action == "delete":
                if existing is None:
                    if extra:
                        self.save(**extra)
                    return
                word = existing
                words.remove(existing)
            else:
                raise ValueError("未知操作")
            history = self.data["history"] + [[datetime.now().isoformat(timespec="minutes"), actor, action, word]]
            effects = self.data["effects"].copy()
            if action == "delete":
                effects.pop(word, None)
            self.save(words=words, effects=effects, history=history[-250:], **extra)

    def rotate(self, enabled, mode="suggest", minutes=60, allow_words=True, allow_effects=True):
        with self.lock:
            expiry = time.time() + 60 * minutes if enabled and mode == "direct" else 0
            self.save(token=secrets.token_urlsafe(32) if enabled else "", share_mode=mode,
                      share_expires=expiry, share_words=allow_words, share_effects=allow_effects)

    @staticmethod
    def effect_value(style, cooldown, glyph, position):
        if style not in ("normal", "gold", "urgent", "prank", "comic", "sticker", "signal"):
            raise ValueError("无效的特效")
        if position not in ("scroll", "top", "bottom", "right", "left", "auto"):
            raise ValueError("无效的出场位置")
        if type(cooldown) is not int or not 0 <= cooldown <= 120:
            raise ValueError("冷却须为 0 到 120 秒")
        if not isinstance(glyph, str) or len(glyph.strip()) != 1 or not glyph.strip().isprintable():
            raise ValueError("整蛊大字需要一个可显示的字符")
        return [style, cooldown, glyph.strip(), position]

    def effect(self, word, style, cooldown, glyph, position="scroll", actor="本机", pending=None):
        with self.lock:
            word = clean(word)
            if word not in self.data["words"]:
                raise ValueError("关键词已被删除")
            value = self.effect_value(style, cooldown, glyph, position)
            effects = {**self.data["effects"], word: value}
            history = self.data["history"] + [[datetime.now().isoformat(timespec="minutes"),
                                               actor, "effect", word]]
            extra = {} if pending is None else {"pending": pending}
            self.save(effects=effects, history=history[-250:], **extra)

    def submit(self, token, payload):
        with self.lock:
            if not self.authorized(token):
                raise PermissionError("链接已撤销或已过期")
            action = payload.get("action")
            if action not in ("add", "delete", "effect"):
                raise ValueError("未知操作")
            if not self.data["share_effects" if action == "effect" else "share_words"]:
                raise PermissionError("链接未授权此操作")
            word = clean(payload.get("word"))
            if any(unicodedata.category(char).startswith("C") for char in word):
                raise ValueError("关键词含不可见控制字符")
            effect = []
            if action == "effect":
                effect = self.effect_value(payload.get("style"), payload.get("cooldown"),
                                           payload.get("glyph"), payload.get("position", "scroll"))
                if word not in self.data["words"]:
                    raise ValueError("关键词已被删除")
            if self.data["share_mode"] == "direct":
                if effect:
                    if effect[0] == "prank" and not self.data["friend_pranks"]:
                        raise PermissionError("主人尚未启用单挑大字")
                    self.effect(word, *effect, actor="限时共编")
                else:
                    self.edit(action, word, "限时共编")
                return
            pending = self.data["pending"]
            change = {"action": action, "word": word, "effect": effect}
            if any(all(item[k] == value for k, value in change.items()) for item in pending):
                return
            if len(pending) >= 100:
                raise ValueError("待审核列表已满")
            self.save(pending=pending + [{"id": secrets.token_hex(8), **change}])

    def review(self, change_id, approved):
        with self.lock:
            entry = next((item for item in self.data["pending"] if item["id"] == change_id), None)
            if not entry:
                return
            remaining = [item for item in self.data["pending"] if item["id"] != change_id]
            if not approved:
                self.save(pending=remaining)
            elif entry["action"] == "effect":
                self.effect(entry["word"], *entry["effect"], actor="审核通过", pending=remaining)
            else:
                self.edit(entry["action"], entry["word"], "审核通过", pending=remaining)

    def allow_pranks(self, enabled):
        with self.lock:
            effects = self.data["effects"]
            if not enabled:
                effects = {word: effect for word, effect in effects.items() if effect[0] != "prank"}
            self.save(friend_pranks=enabled, effects=effects)

    def shared_view(self):
        with self.lock:
            return {key: self.data[key] for key in ("words", "effects", "friend_pranks",
                "share_mode", "share_words", "share_effects", "share_expires")}

    def authorized(self, token):
        current = self.data["token"]
        expires = self.data["share_expires"]
        return bool(current and token.isascii() and secrets.compare_digest(current, token)
                    and (not expires or time.time() < expires))


def serve(words, port=8765):
    base = Path(__file__).parent

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(8)

        def log_message(self, *_):
            pass

        def send(self, status, body, kind="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", kind + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def json(self, status, value):
            self.send(status, json.dumps(value, ensure_ascii=False).encode())

        def route(self):
            parts = self.path.split("?")[0].strip("/").split("/")
            if len(parts) < 2 or parts[0] != "edit":
                return "", ""
            return parts[1], "/".join(parts[2:])

        def do_GET(self):
            token, resource = self.route()
            with words.lock:
                if not words.authorized(token):
                    self.send(404, "编辑链接不存在或已撤销。".encode(), "text/plain")
                    return
                if resource == "api":
                    self.json(200, words.shared_view())
                    return
            assets = {"": ("friend.html", "text/html"), "style.css": ("style.css", "text/css"),
                      "app.js": ("friend.js", "text/javascript")}
            if resource not in assets:
                self.send(404, b"Not found", "text/plain")
                return
            file, kind = assets[resource]
            self.send(200, (base / file).read_bytes(), kind)

        def do_POST(self):
            token, resource = self.route()
            if resource != "api" or self.headers.get("X-Word-Edit") != "1":
                self.json(404, {"error": "找不到编辑接口"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4096:
                    raise ValueError("请求过大或为空")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("无效的请求")
                words.submit(token, payload)
            except PermissionError as error:
                self.json(403, {"error": str(error)})
            except ValueError as error:
                self.json(400, {"error": str(error)})
            else:
                self.json(200, words.shared_view())

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
