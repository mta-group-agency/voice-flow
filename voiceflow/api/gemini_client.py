import base64
import json
import time

import requests

from voiceflow.api.base_client import BaseAIClient
from voiceflow.config.schema import ProcessingConfig

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_TIMEOUT = 30
_RETRYABLE = {429, 500, 502, 503, 504}
_session = requests.Session()  # Persistent TCP connections across all Gemini calls


class GeminiClient(BaseAIClient):
    def __init__(self, api_key: str, stt_model: str = "gemini-2.5-flash", ai_model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.stt_model = stt_model
        self.ai_model = ai_model

    def _url(self, model: str, stream: bool = False) -> str:
        endpoint = "streamGenerateContent?alt=sse&" if stream else "generateContent?"
        return f"{_BASE}/{model}:{endpoint}key={self.api_key}"

    def _post(self, model: str, payload: dict) -> dict:
        for attempt in range(3):
            try:
                resp = _session.post(self._url(model), json=payload, timeout=_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                if status in _RETRYABLE and attempt < 2:
                    time.sleep(0.3 * (2 ** attempt))  # 0.3s, 0.6s
                    continue
                reason = e.response.reason if e.response is not None else "unknown"
                raise RuntimeError(f"Gemini API error {status} ({reason})") from None
            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(0.3 * (2 ** attempt))
                    continue
                raise RuntimeError(f"Gemini API connection error: {type(e).__name__}") from None
        raise RuntimeError("Gemini API: service unavailable after retries")

    def _post_stream(self, model: str, payload: dict) -> str:
        """Stream response for lower TTFB; collects and returns the full text."""
        for attempt in range(3):
            try:
                resp = _session.post(
                    self._url(model, stream=True), json=payload,
                    timeout=_TIMEOUT, stream=True,
                )
                resp.raise_for_status()
                parts = []
                for line in resp.iter_lines():
                    if not line or not line.startswith(b"data: "):
                        continue
                    raw = line[6:]
                    if raw == b"[DONE]":
                        break
                    try:
                        chunk = json.loads(raw)
                        text = chunk["candidates"][0]["content"]["parts"][0].get("text", "")
                        parts.append(text)
                    except (KeyError, IndexError, json.JSONDecodeError):
                        pass
                return "".join(parts).strip()
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                if status in _RETRYABLE and attempt < 2:
                    time.sleep(0.3 * (2 ** attempt))
                    continue
                reason = e.response.reason if e.response is not None else "unknown"
                raise RuntimeError(f"Gemini API error {status} ({reason})") from None
            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(0.3 * (2 ** attempt))
                    continue
                raise RuntimeError(f"Gemini API connection error: {type(e).__name__}") from None
        raise RuntimeError("Gemini API: service unavailable after retries")

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
        return self._post_stream(self.stt_model, payload)

    def transcribe_and_process(self, wav_bytes: bytes, config: ProcessingConfig) -> str:
        """Single Gemini call that transcribes audio and applies post-processing together."""
        instructions = self._build_system_prompt(config)
        b64 = base64.b64encode(wav_bytes).decode("utf-8")
        prompt = (
            "Transcribe this audio recording accurately and apply the following transformations:\n"
            + instructions
            + "\n\nReturn only the final processed text, nothing else."
        )
        payload = {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": "audio/wav", "data": b64}},
                    {"text": prompt},
                ]
            }],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 512},
        }
        return self._post_stream(self.stt_model, payload)

    def process_text(self, text: str, config: ProcessingConfig) -> str:
        system_prompt = self._build_system_prompt(config)
        if not system_prompt:
            return text

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 512},
        }
        data = self._post(self.ai_model, payload)
        result = self._extract_text(data)
        return result if result else text

    def run_assistant(self, command: str, context: str | None, system_prompt: str) -> str:
        user_message = self._build_assistant_user_message(command, context)
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_message}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
        }
        data = self._post(self.ai_model, payload)
        return self._extract_text(data)

    def test_connection(self) -> bool:
        try:
            payload = {"contents": [{"parts": [{"text": "Say: ok"}]}]}
            self._post(self.ai_model, payload)
            return True
        except Exception:
            return False

    @staticmethod
    def estimate_cost(audio_seconds: float, output_chars: int) -> float:
        audio_cost = audio_seconds * 25 * (1.00 / 1_000_000)
        text_cost = (output_chars / 4) * (3.50 / 1_000_000)
        return audio_cost + text_cost