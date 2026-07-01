"""
Local speech-to-text using faster-whisper (CTranslate2 backend).
NVIDIA GPU recommended (~150-800ms); falls back to CPU (~2-5s).
Models are downloaded from HuggingFace Hub and cached in %APPDATA%/VoiceFlow/models/.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Optional

from voiceflow.api.base_client import BaseAIClient
from voiceflow.config.schema import ProcessingConfig

MODELS_DIR = Path(os.environ.get("APPDATA", Path.home())) / "VoiceFlow" / "models"

MODEL_INFO = {
    "tiny":     {"size_mb": 39,   "disk_mb": 80,   "speed": "~0.1s (GPU)"},
    "small":    {"size_mb": 244,  "disk_mb": 490,  "speed": "~0.15s (GPU)"},
    "medium":   {"size_mb": 769,  "disk_mb": 1540, "speed": "~0.30s (GPU)"},
    "large-v3": {"size_mb": 1550, "disk_mb": 3100, "speed": "~0.80s (GPU)"},
}

_model_cache: dict[str, object] = {}


def _cuda_available() -> bool:
    try:
        import ctranslate2
        return ctranslate2.cuda.is_available()
    except Exception:
        return False


class LocalWhisperClient(BaseAIClient):
    def __init__(self, model_name: str = "small"):
        self._model_name = model_name

    @classmethod
    def preload_model(
        cls,
        model_name: str,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Download and load the model. Safe to call from any thread.

        on_status is called with:
          "downloading"  — network download phase (folder size grows)
          "loading"      — files present, loading into GPU/CPU memory
        """
        if model_name in _model_cache:
            return

        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        # Stale .locks files from interrupted downloads cause snapshot_download to hang forever.
        locks_dir = MODELS_DIR / ".locks"
        if locks_dir.exists():
            try:
                shutil.rmtree(locks_dir)
            except Exception:
                pass

        model_dir = MODELS_DIR / f"models--Systran--faster-whisper-{model_name}"
        already_cached = model_dir.exists()

        # Phase 1 — download files from HuggingFace Hub (skip if already cached)
        if on_status:
            on_status("downloading")
        if not already_cached:
            try:
                from huggingface_hub import snapshot_download
                snapshot_download(
                    repo_id=f"Systran/faster-whisper-{model_name}",
                    cache_dir=str(MODELS_DIR),
                )
            except Exception:
                pass  # WhisperModel constructor will retry / use what's cached

        # Phase 2 — load into memory (CUDA warmup can take 30-90s first time)
        if on_status:
            on_status("loading")

        from faster_whisper import WhisperModel
        use_cuda = _cuda_available()
        device = "cuda" if use_cuda else "cpu"
        compute_type = "float16" if use_cuda else "int8"
        try:
            model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                download_root=str(MODELS_DIR),
            )
        except Exception:
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

    def run_assistant(self, command: str, context: str | None, system_prompt: str) -> str:
        raise NotImplementedError("Local Whisper does not support the AI assistant. Use Gemini, Groq, or Claude.")

    def test_connection(self) -> bool:
        return self._model_name in _model_cache

    @staticmethod
    def estimate_cost(audio_seconds: float, output_chars: int) -> float:
        return 0.0
