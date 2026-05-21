"""
Local speech-to-text using faster-whisper (CTranslate2 backend).
Requires NVIDIA GPU for fast inference (~150-800ms); falls back to CPU (~2-5s).
Models are downloaded on first use and cached in %APPDATA%/VoiceFlow/models/.
"""

import os
import tempfile
from pathlib import Path

from voiceflow.api.base_client import BaseAIClient
from voiceflow.config.schema import ProcessingConfig

MODELS_DIR = Path(os.environ.get("APPDATA", Path.home())) / "VoiceFlow" / "models"

# Approximate model info for UI display
MODEL_INFO = {
    "tiny":     {"size_mb": 39,   "speed": "~0.1s (GPU)"},
    "small":    {"size_mb": 244,  "speed": "~0.15s (GPU)"},
    "medium":   {"size_mb": 769,  "speed": "~0.30s (GPU)"},
    "large-v3": {"size_mb": 1550, "speed": "~0.80s (GPU)"},
}

# Class-level cache — model stays loaded for the lifetime of the process
_model_cache: dict[str, object] = {}


class LocalWhisperClient(BaseAIClient):
    def __init__(self, model_name: str = "small"):
        self._model_name = model_name

    @classmethod
    def preload_model(cls, model_name: str) -> None:
        """Download and load the model into memory. Safe to call from any thread."""
        if model_name in _model_cache:
            return
        from faster_whisper import WhisperModel
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            model = WhisperModel(
                model_name,
                device="cuda",
                compute_type="float16",
                download_root=str(MODELS_DIR),
            )
        except Exception:
            # Fall back to CPU if CUDA is unavailable
            model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                download_root=str(MODELS_DIR),
            )
        _model_cache[model_name] = model

    @classmethod
    def is_loaded(cls, model_name: str) -> bool:
        return model_name in _model_cache

    def transcribe(self, wav_bytes: bytes) -> str:
        self.preload_model(self._model_name)
        model = _model_cache[self._model_name]

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        try:
            with os.fdopen(tmp_fd, "wb") as f:
                f.write(wav_bytes)
            segments, _ = model.transcribe(tmp_path, task="transcribe")
            return " ".join(seg.text.strip() for seg in segments).strip()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def process_text(self, text: str, config: ProcessingConfig) -> str:
        raise NotImplementedError("Local Whisper does not support text processing.")

    def test_connection(self) -> bool:
        return self._model_name in _model_cache

    @staticmethod
    def estimate_cost(audio_seconds: float, output_chars: int) -> float:
        return 0.0
