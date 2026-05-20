import base64
import time

import requests

from voiceflow.api.base_client import BaseAIClient
from voiceflow.config.schema import ProcessingConfig

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_TIMEOUT = 30
_RETRYABLE = {429, 500, 502, 503, 504}


class GeminiClient(BaseAIClient):
    def __init__(self, api_key: str, stt_model: str = "gemini-2.5-flash", ai_model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.stt_model = stt_model
        self.ai_model = ai_model

    def _url(self, model: str) -> str:
        return f"{_BASE}/{model}:generateContent?key={self.api_key}"

    def _post(self, model: str, payload: dict) -> dict:
        last_status = None
        for attempt in range(3):
            try:
                resp = requests.post(self._url(model), json=payload, timeout=_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                last_status = status
                if status in _RETRYABLE and attempt < 2:
                    time.sleep(2 ** attempt)  # 1s, 2s
                    continue
                reason = e.response.reason if e.response is not None else "unknown"
                raise RuntimeError(f"Gemini API error {status} ({reason})") from None
            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"Gemini API connection error: {type(e).__name__}") from None
        raise RuntimeError(f"Gemini API error {last_status}: service unavailable, try again")

    def _extract_text(self, data: dict) -> str:
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            return ""

    def transcribe(self, wav_bytes: bytes) -> str:
        b64 = base64.b64encode(wav_bytes).decode("utf-8")
        payload = {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": "audio/wav", "data": b64}},
                    {"text": (
                        "Please transcribe this audio recording accurately. "
                        "Return only the transcription text, nothing else. "
                        "Preserve the original language."
                    )},
                ]
            }]
        }
        data = self._post(self.stt_model, payload)
        return self._extract_text(data)

    def process_text(self, text: str, config: ProcessingConfig) -> str:
        system_prompt = self._build_system_prompt(config)
        if not system_prompt:
            return text

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
        }
        data = self._post(self.ai_model, payload)
        result = self._extract_text(data)
        return result if result else text

    def test_connection(self) -> bool:
        try:
            payload = {"contents": [{"parts": [{"text": "Say: ok"}]}]}
            self._post(self.ai_model, payload)
            return True
        except Exception:
            return False

    @staticmethod
    def estimate_cost(audio_seconds: float, output_chars: int) -> float:
        # Gemini 2.5 Flash approximate pricing
        # Audio: ~25 tokens/s, $1.00/M input tokens
        # Text output: $3.50/M tokens (~4 chars per token)
        audio_cost = audio_seconds * 25 * (1.00 / 1_000_000)
        text_cost = (output_chars / 4) * (3.50 / 1_000_000)
        return audio_cost + text_cost
