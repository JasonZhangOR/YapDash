from collections import deque

from PyQt5.QtCore import QByteArray, QBuffer, QIODevice, QObject
from PyQt5.QtMultimedia import QAudio, QAudioDeviceInfo, QAudioFormat, QAudioOutput


class RecentAudio:
    rate = 16000
    bytes_per_sample = 2
    max_samples = rate * 30

    def __init__(self):
        self.chunks = deque()

    def add(self, end, pcm):
        self.chunks.append((end - len(pcm) // self.bytes_per_sample, pcm))
        cutoff = end - self.max_samples
        while self.chunks:
            offset, oldest = self.chunks[0]
            if offset + len(oldest) // self.bytes_per_sample > cutoff:
                break
            self.chunks.popleft()

    def clip(self, start_time, end_time):
        if not self.chunks or end_time <= start_time:
            return b""
        start = max(0, round((start_time - 0.16) * self.rate))
        end = round((end_time + 0.24) * self.rate)
        if round(start_time * self.rate) < self.chunks[0][0]:
            return b""
        parts = []
        for offset, pcm in self.chunks:
            if offset >= end:
                break
            first = max(0, start - offset) * self.bytes_per_sample
            last = min(len(pcm), (end - offset) * self.bytes_per_sample)
            if last > first:
                parts.append(pcm[first:last])
        return b"".join(parts)


class VoiceReplay(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.output = None
        self.buffer = None
        self.pending = deque()

    def play(self, pcm):
        if not pcm:
            return False
        if self.output:
            if len(self.pending) < 3:
                self.pending.append(pcm)
                return True
            return False
        device = QAudioDeviceInfo.defaultOutputDevice()
        audio_format = QAudioFormat()
        audio_format.setCodec("audio/pcm")
        audio_format.setSampleRate(RecentAudio.rate)
        audio_format.setChannelCount(1)
        audio_format.setSampleSize(16)
        audio_format.setSampleType(QAudioFormat.SignedInt)
        audio_format.setByteOrder(QAudioFormat.LittleEndian)
        if device.isNull() or not device.isFormatSupported(audio_format):
            return False
        self.buffer = QBuffer(self)
        self.buffer.setData(QByteArray(pcm))
        self.buffer.open(QIODevice.ReadOnly)
        output = QAudioOutput(device, audio_format, self)
        self.output = output
        output.setVolume(0.85)
        output.stateChanged.connect(lambda state: self.finished(output, state))
        output.start(self.buffer)
        return output.error() == QAudio.NoError

    def finished(self, output, state):
        if output is self.output and state in (QAudio.IdleState, QAudio.StoppedState):
            self.release()
            if self.pending:
                self.play(self.pending.popleft())

    def stop(self):
        self.pending.clear()
        self.release()

    def release(self):
        output, self.output = self.output, None
        if output:
            output.stop()
            output.deleteLater()
        if self.buffer:
            self.buffer.close()
            self.buffer.deleteLater()
            self.buffer = None
