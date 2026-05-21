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

    _INTENSITY_PREAMBLE = {
        1: (
            "Make MINIMAL changes. Only fix clear typos and remove the most obvious filler sounds. "
            "Preserve the speaker's natural voice, rhythm, and phrasing as much as possible."
        ),
        2: (
            "Make light corrections. Fix typos, remove filler words, and fix only necessary grammar errors. "
            "Keep the original style and sentence structure intact."
        ),
        3: (
            "Apply balanced corrections."
        ),
        4: (
            "Clean up the text thoroughly. Fix all grammar, remove fillers, and improve sentence flow "
            "where it helps readability, while preserving the original meaning."
        ),
        5: (
            "Polish the text aggressively for maximum clarity and professionalism. Fix all grammar and "
            "spelling, remove all fillers, restructure sentences for better flow, and elevate the vocabulary "
            "where appropriate — while preserving the core meaning."
        ),
    }

    def _build_system_prompt(self, config: ProcessingConfig) -> str:
        if config.custom_prompt:
            return config.custom_prompt

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

        intensity = max(1, min(5, config.intensity))
        preamble = self._INTENSITY_PREAMBLE.get(intensity, self._INTENSITY_PREAMBLE[3])
        return (
            f"You are a text post-processor. {preamble}\n\n"
            "Apply ONLY the following transformations:\n"
            + "\n".join(rules)
            + "\n\nReturn only the processed text, no explanations, no quotes."
        )
