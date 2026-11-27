from pathlib import Path

MODEL_DIR = "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
MODEL_FILES = ("model.int8.onnx", "tokens.txt", "silero_vad.onnx")


class SenseVoice:
    def __init__(self, path):
        try:
            import numpy
            import sherpa_onnx
        except ImportError as error:
            raise RuntimeError("请先运行「安装依赖和模型.ps1」安装 SenseVoice") from error
        self.numpy = numpy
        path = Path(path)
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(path / MODEL_FILES[0]), tokens=str(path / MODEL_FILES[1]),
            num_threads=2, language="auto", use_itn=True, debug=False)
        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(path / MODEL_FILES[2])
        config.silero_vad.min_speech_duration = 0.10
        config.silero_vad.min_silence_duration = 0.32
        config.silero_vad.max_speech_duration = 10
        config.sample_rate = 16000
        self.vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=30)
        self.pending = bytearray()

    def feed(self, pcm):
        self.pending.extend(pcm)
        window_bytes = 512 * 2
        complete = len(self.pending) // window_bytes * window_bytes
        frames = bytes(self.pending[:complete])
        del self.pending[:complete]
        for index in range(0, len(frames), window_bytes):
            wave = self.numpy.frombuffer(frames[index:index + window_bytes], dtype="<i2")
            self.vad.accept_waveform(wave.astype(self.numpy.float32) / 32768)
        while not self.vad.empty():
            segment = self.vad.front
            start = segment.start
            clip = self.numpy.array(segment.samples, dtype=self.numpy.float32, copy=True)
            self.vad.pop()
            stream = self.recognizer.create_stream()
            stream.accept_waveform(16000, clip)
            self.recognizer.decode_stream(stream)
            text = stream.result.text.strip()
            if text:
                pcm = self.numpy.clip(clip * 32768, -32768, 32767).astype("<i2").tobytes()
                yield text, start / 16000, (start + len(clip)) / 16000, pcm
