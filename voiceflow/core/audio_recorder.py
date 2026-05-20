import io
import wave
from typing import Optional

import pyaudio
from PyQt6.QtCore import QThread, pyqtSignal


class AudioRecorder(QThread):
    recording_finished = pyqtSignal(bytes)  # WAV bytes
    level_updated = pyqtSignal(float)       # 0.0–1.0 amplitude for UI

    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1

    def __init__(self, sample_rate: int = 16000, device_index: Optional[int] = None):
        super().__init__()
        self.sample_rate = sample_rate
        self.device_index = device_index
        self._recording = False
        self._pa: Optional[pyaudio.PyAudio] = None

    def start_recording(self):
        self._recording = True
        if not self.isRunning():
            self.start()

    def stop_recording(self):
        self._recording = False

    def run(self):
        self._pa = pyaudio.PyAudio()
        buf = io.BytesIO()

        kwargs = dict(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.CHUNK,
        )
        if self.device_index is not None:
            kwargs["input_device_index"] = self.device_index

        stream = self._pa.open(**kwargs)

        frames = []
        try:
            while self._recording:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
                # compute amplitude for VU meter
                if frames:
                    import struct
                    samples = struct.unpack_from(f"{self.CHUNK}h", data)
                    peak = max(abs(s) for s in samples) / 32768.0
                    self.level_updated.emit(min(peak * 3.0, 1.0))
        finally:
            stream.stop_stream()
            stream.close()
            self._pa.terminate()
            self._pa = None

        if not frames:
            return

        # encode frames as WAV into memory
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(b"".join(frames))

        self.recording_finished.emit(buf.getvalue())

    @property
    def duration_seconds(self) -> float:
        return 0.0  # updated externally via timer
