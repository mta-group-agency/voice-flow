import anthropic

from voiceflow.api.base_client import BaseAIClient
from voiceflow.config.schema import ProcessingConfig


class ClaudeClient(BaseAIClient):
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        self.api_key = api_key
        self.model = model

    def _client(self) -> anthropic.Anthropic:
        return anthropic.Anthropic(api_key=self.api_key)

    def transcribe(self, wav_bytes: bytes) -> str:
        raise NotImplementedError("Claude does not support audio transcription. Use Gemini for STT.")

    def process_text(self, text: str, config: ProcessingConfig) -> str:
        system_prompt = self._build_system_prompt(config)
        if not system_prompt:
            return text

        try:
            client = self._client()
            message = client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": text}],
            )
            result = message.content[0].text.strip() if message.content else text
            return result if result else text
        except Exception as e:
            raise RuntimeError(f"Claude API error: {type(e).__name__}: {e.args[0] if e.args else ''}") from None

    def test_connection(self) -> bool:
        try:
            client = self._client()
            client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say: ok"}],
            )
            return True
        except Exception:
            return False

    @staticmethod
    def estimate_cost(input_tokens: int, output_tokens: int) -> float:
        # claude-3-5-haiku approximate pricing
        return (input_tokens / 1000) * 0.00025 + (output_tokens / 1000) * 0.00125
