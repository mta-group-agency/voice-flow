from abc import ABC, abstractmethod

from voiceflow.config.schema import ProcessingConfig
from voiceflow.core.logger import redact


def extract_error_detail(response, limit: int = 1200) -> str:
    """Human-readable reason from a JSON API error body (Gemini/Groq both use
    an {"error": {"message": ...}} shape), if any, e.g. "API key not valid.", so a
    bad key can be told apart from other 400s. Collapsed to one line, redacted and
    truncated; never raises. The limit is generous because 429 bodies put the useful
    part (which quota, "retry in 41.7s") several hundred characters in."""
    if response is None:
        return ""
    try:
        body = response.json()
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, str):
            message = error
        elif isinstance(error, dict) and isinstance(error.get("message"), str):
            message = error.get("message")
        else:
            message = ""
    except Exception:
        # A malformed/unreadable body must never replace the HTTP status error.
        return ""
    message = " ".join(str(message).split())
    return redact(message)[:limit] if message else ""


class BaseAIClient(ABC):
    @abstractmethod
    def transcribe(self, wav_bytes: bytes) -> str:
        """Convert audio bytes (WAV) to text. Raises NotImplementedError if STT not supported."""

    @abstractmethod
    def process_text(self, text: str, config: ProcessingConfig) -> str:
        """Post-process transcribed text according to ProcessingConfig."""

    @abstractmethod
    def run_assistant(self, command: str, context: str | None, system_prompt: str) -> str:
        """Execute the transcribed command as an AI assistant and return ready-to-paste text."""

    def _build_assistant_user_message(self, command: str, context: str | None) -> str:
        if context and context.strip():
            return (
                "KONTEKST (zaznaczony/skopiowany tekst):\n"
                f"{context.strip()}\n\n"
                "POLECENIE:\n"
                f"{command.strip()}"
            )
        return command.strip()

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if the API key is valid and reachable."""

    def list_models(self) -> list[str]:
        """Best-effort live model list from the provider. Never raises — returns [] on any failure."""
        return []

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
