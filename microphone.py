"""Read the Windows default microphone as 16 kHz mono PCM."""

import audioop

from PyQt5 import QtCore as C
from PyQt5.QtMultimedia import QAudio, QAudioDeviceInfo, QAudioFormat, QAudioInput


def input_format(device):
    preferred_rate = device.preferredFormat().sampleRate()
    fmt = QAudioFormat()
    fmt.setCodec("audio/pcm")
    fmt.setSampleSize(16)
    fmt.setSampleType(QAudioFormat.SignedInt)
    fmt.setByteOrder(QAudioFormat.LittleEndian)
    for rate in dict.fromkeys((16000, preferred_rate, 48000, 44100)):
        for channels in (1, 2):
            fmt.setSampleRate(rate)
            fmt.setChannelCount(channels)
            if device.isFormatSupported(fmt):
                return fmt
    raise OSError("默认麦克风不支持 16 位单声道或双声道输入")


def packets(stop, ready):
    device = QAudioDeviceInfo.defaultInputDevice()
    if device.isNull():
        raise OSError("未找到默认麦克风")
    fmt = input_format(device)
    events = C.QEventLoop()
    audio = QAudioInput(device, fmt)
    audio.setBufferSize(fmt.bytesForDuration(200_000))
    stream = audio.start()
    rate_state = None
    remainder = b""
    try:
        if not stream or audio.error() != QAudio.NoError:
            raise OSError("无法打开麦克风，请检查 Windows 麦克风权限")
        ready()
        while not stop.is_set():
            events.processEvents()
            if audio.error() != QAudio.NoError or audio.state() == QAudio.StoppedState:
                raise OSError("麦克风输入中断，请检查设备连接和权限")
            data = remainder + bytes(stream.readAll())
            frame_size = fmt.bytesPerFrame()
            complete = len(data) // frame_size * frame_size
            remainder = data[complete:]
            if complete:
                mono = data[:complete]
                if fmt.channelCount() == 2:
                    mono = audioop.tomono(mono, 2, 0.5, 0.5)
                mono, rate_state = audioop.ratecv(mono, 2, 1, fmt.sampleRate(), 16000, rate_state)
                yield mono
            stop.wait(0.025)
    finally:
        audio.stop()
