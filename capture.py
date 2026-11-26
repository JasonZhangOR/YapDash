"""WASAPI application loopback. Audio stays in memory."""
import ctypes as c
from ctypes import wintypes as w
import threading
import uuid
import time

P = c.c_void_p
U = c.c_uint32
H = c.c_long
W = c.WINFUNCTYPE
GUID = c.c_ubyte * 16
ole = c.OleDLL("ole32")
mm = c.WinDLL("mmdevapi")


def guid(value):
    return GUID.from_buffer_copy(uuid.UUID(value).bytes_le)


def check(hr):
    if hr < 0:
        raise OSError(f"WASAPI 0x{hr & 0xffffffff:08X}")


def call(obj, slot, result, types, *args):
    table = c.cast(obj, c.POINTER(c.POINTER(P)))[0]
    return W(result, P, *types)(table[slot])(obj, *args)


class Blob(c.Structure):
    _fields_ = [("size", U), ("data", P)]


class Variant(c.Structure):
    _fields_ = [("type", c.c_uint16), ("reserved", c.c_uint16 * 3), ("blob", Blob)]


class Wave(c.Structure):
    _pack_ = 1
    _fields_ = [("tag", c.c_uint16), ("channels", c.c_uint16), ("rate", U),
                ("bytes_per_second", U), ("alignment", c.c_uint16),
                ("bits", c.c_uint16), ("extra", c.c_uint16)]


def open_client(pid):
    audio_iid = guid("1cb9ad4c-dbfa-4c32-b178-c2f568a703b2")
    accepted = {uuid.UUID(x).bytes_le for x in (
        "00000000-0000-0000-c000-000000000046",
        "94ea2b94-e9cc-49e0-c0ff-ee64ca8f5b90",
        "41d949ab-9862-444a-80f6-c261334da5eb")}
    finished = threading.Event()
    result = P()
    errors = []
    refs = 1

    @W(U, P)
    def add_ref(_):
        nonlocal refs
        refs += 1
        return refs

    @W(U, P)
    def release(_):
        nonlocal refs
        refs -= 1
        return refs

    @W(H, P, P, c.POINTER(P))
    def query(this, iid, out):
        out[0] = None
        if c.string_at(iid, 16) not in accepted:
            return -2147467262
        out[0] = this
        add_ref(this)
        return 0

    @W(H, P, P)
    def complete(_, operation):
        try:
            status = H()
            check(call(operation, 3, H, [c.POINTER(H), c.POINTER(P)],
                       c.byref(status), c.byref(result)))
            check(status.value)
        except Exception as error:
            errors.append(error)
        finally:
            finished.set()
        return 0

    table = (P * 4)(*[c.cast(fn, P).value for fn in (query, add_ref, release, complete)])
    callback = c.cast(c.pointer(c.cast(table, P)), P)
    parameters = (U * 3)(1, pid, 0)
    variant = Variant(65, (c.c_uint16 * 3)(), Blob(c.sizeof(parameters), c.cast(parameters, P)))
    operation = P()
    activate = mm.ActivateAudioInterfaceAsync
    activate.argtypes = [w.LPCWSTR, c.POINTER(GUID), c.POINTER(Variant), P, c.POINTER(P)]
    activate.restype = H
    check(activate("VAD\\Process_Loopback", c.byref(audio_iid), c.byref(variant),
                   callback, c.byref(operation)))
    try:
        finished.wait()
        if errors:
            if result:
                call(result, 2, U, [])
            raise errors[0]
        return result
    finally:
        call(operation, 2, U, [])


def packets(pid, stop, ready=lambda: None):
    ole.CoInitializeEx(None, 0)
    audio = capture = None
    started = False
    try:
        audio = open_client(pid)
        wave = Wave(1, 2, 44100, 176400, 4, 16, 0)
        check(call(audio, 3, H, [U, U, c.c_int64, c.c_int64, P, P],
                   0, 0x80020000, 0, 0, c.byref(wave), None))
        capture = P()
        capture_iid = guid("c8adbd64-e71e-48a0-a4de-185c395cd317")
        check(call(audio, 14, H, [c.POINTER(GUID), c.POINTER(P)],
                   c.byref(capture_iid), c.byref(capture)))
        check(call(audio, 10, H, []))
        started = True
        ready()
        deadline = time.monotonic()
        while not stop.is_set():
            frames = U()
            check(call(capture, 5, H, [c.POINTER(U)], c.byref(frames)))
            if not frames.value:
                if time.monotonic() - deadline >= 0.12:
                    deadline = time.monotonic()
                    yield bytes(4410 * 4)
                stop.wait(0.015)
                continue
            deadline = time.monotonic()
            data, count, flags = P(), U(), U()
            check(call(capture, 3, H, [c.POINTER(P), c.POINTER(U), c.POINTER(U), P, P],
                       c.byref(data), c.byref(count), c.byref(flags), None, None))
            try:
                payload = bytes(count.value * 4) if flags.value & 2 else c.string_at(data, count.value * 4)
            finally:
                check(call(capture, 4, H, [U], count.value))
            yield payload
    finally:
        if started:
            call(audio, 11, H, [])
        for obj in (capture, audio):
            if obj:
                call(obj, 2, U, [])
        ole.CoUninitialize()
