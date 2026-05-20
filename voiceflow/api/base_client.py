from abc import ABC, abstractmethod

from voiceflow.config.schema import ProcessingConfig


class BaseAIClient(ABC):
    @abstractmethod
    def transcribe(self, wav_bytes: bytes) -> str:
        """Convert audio bytes (WAV) to text. Raises NotImplementedError if STT not supported."""

    @abstractmethod
    def process_text(self, text: str, config: ProcessingConfig) -> str:
        """Post-process transcribed text according to ProcessingConfig."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if the API key is valid and reachable."""

    def _build_system_prompt(self, config: ProcessingConfig) -> str:
        rules = []
        if config.remove_fillers:
            rules.append("- Remove filler words and sounds (yyy, eee, um, uh, hmm, like, you know) without changing meaning.")
        if config.fix_grammar:
            rules.append("- Fix grammar, punctuation, and spelling. Preserve the original language.")
        if config.translation_target:
            rules.append(f"- Translate the text to {config.translation_target}.")
        if config.tone:
            rules.append(f"- Adjust the tone to be {config.tone}.")

        if not rules:
            return ""

        return (
            "You are a text post-processor. Apply ONLY the following transformations:\n"
            + "\n".join(rules)
            + "\n\nReturn only the processed text, no explanations, no quotes."
        )
