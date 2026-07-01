import time

import requests

from voiceflow.api.base_client import BaseAIClient
from voiceflow.config.schema import ProcessingConfig

_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_TIMEOUT = 30
_RETRYABLE = {429, 500, 502, 503, 504}


class GroqClient(BaseAIClient):
    def __init__(
        self,
        api_key: str,
        stt_model: str = "whisper-large-v3-turbo",
        ai_model: str = "llama-3.3-70b-versatile",
    ):
        self.api_key = api_key
        self.stt_model = stt_model
        self.ai_model = ai_model

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _post_json(self, url: str, payload: dict) -> dict:
        last_status = 0
        for attempt in range(3):
            try:
                resp = requests.post(
                    url,
                    headers={**self._auth(), "Content-Type": "application/json"},
                    json=payload,
                    timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                return resp.json()
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                last_status = status
                if status in _RETRYABLE and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                reason = e.response.reason if e.response is not None else "unknown"
                raise RuntimeError(f"Groq API error {status} ({reason})") from None
            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"Groq connection error: {type(e).__name__}") from None
        raise RuntimeError(f"Groq API error {last_status}: service unavailable")

    def transcribe(self, wav_bytes: bytes) -> str:
        last_status = 0
        for attempt in range(3):
            try:
                resp = requests.post(
                    _STT_URL,
                    headers=self._auth(),
                    files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                    data={"model": self.stt_model},
                    timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                return resp.json().get("text", "").strip()
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                last_status = status
                if status in _RETRYABLE and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                reason = e.response.reason if e.response is not None else "unknown"
                raise RuntimeError(f"Groq STT error {status} ({reason})") from None
            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"Groq connection error: {type(e).__name__}") from None
        raise RuntimeError(f"Groq STT error {last_status}: service unavailable")

    def process_text(self, text: str, config: ProcessingConfig) -> str:
        system_prompt = self._build_system_prompt(config)
        if not system_prompt:
            return text
        data = self._post_json(_CHAT_URL, {
            "model": self.ai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0.1,
            "max_tokens": 2048,
        })
        result = data["choices"][0]["message"]["content"].strip()
        return result if result else text

    def run_assistant(self, command: str, context: str | None, system_prompt: str) -> str:
        user_message = self._build_assistant_user_message(command, context)
        data = self._post_json(_CHAT_URL, {
            "model": self.ai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
        })
        return data["choices"][0]["message"]["content"].strip()

    def test_connection(self) -> bool:
        try:
            self._post_json(_CHAT_URL, {
                "model": self.ai_model,
                "messages": [{"role": "user", "content": "Say: ok"}],
                "max_tokens": 5,
            })
            return True
        except Exception:
            return False

    @staticmethod
    def estimate_cost(audio_seconds: float, output_chars: int) -> float:
        # Whisper Large v3 Turbo: $0.04/hr audio
        # Llama 3.3 70B: $0.59/M input + $0.79/M output tokens
        audio_cost = audio_seconds * 0.04 / 3600
        llm_cost = (output_chars / 4) * 0.79 / 1_000_000
        return audio_cost + llm_cost
