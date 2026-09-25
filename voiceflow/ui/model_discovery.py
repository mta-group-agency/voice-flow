"""
Best-effort background fetch of live model lists from each configured provider,
run once at app startup so Settings can offer up-to-date models instead of a
static, possibly stale, fallback list.
"""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from voiceflow.api.claude_client import ClaudeClient
from voiceflow.api.gemini_client import GeminiClient
from voiceflow.api.groq_client import GroqClient
from voiceflow.config import model_healing


class ModelDiscoveryWorker(QThread):
    provider_models_ready = pyqtSignal(str, object)  # (provider_key, payload)

    def __init__(self, gemini_key: str, claude_key: str, groq_key: str, parent=None):
        super().__init__(parent)
        self._gemini_key = gemini_key
        self._claude_key = claude_key
        self._groq_key = groq_key

    def run(self):
        if self._gemini_key:
            models = GeminiClient(self._gemini_key).list_models()
            if models:
                self.provider_models_ready.emit("gemini", models)
        if self._claude_key:
            models = ClaudeClient(self._claude_key).list_models()
            if models:
                self.provider_models_ready.emit("claude", models)
        if self._groq_key:
            all_ids = GroqClient(self._groq_key).list_models()
            if all_ids:
                stt, chat = GroqClient.split_stt_and_chat(all_ids)
                self.provider_models_ready.emit("groq", {"stt": stt, "chat": chat})


# provider -> the attribute each client uses for its chat/assistant model. Claude's
# client predates the others and kept the shorter name.
_MODEL_ATTR = {"gemini": "ai_model", "groq": "ai_model", "claude": "model"}


class ConnectionTestWorker(QThread):
    """Runs a Settings "Test" click off the GUI thread — list_models() + test_connection()
    are both real HTTP round trips that used to block the window for seconds.

    Fetching the live model list first both validates the key and, if the configured
    chat model has since been discontinued, gives model_healing enough to retest with
    a working replacement instead of just reporting the dead model as a failure.
    """

    finished_test = pyqtSignal(str, bool, list)  # provider, ok, live_chat_models

    def __init__(self, provider: str, client, parent=None):
        super().__init__(parent)
        self._provider = provider
        self._client = client

    def run(self):
        attr = _MODEL_ATTR[self._provider]
        all_ids = self._client.list_models()
        chat_models = GroqClient.split_stt_and_chat(all_ids)[1] if self._provider == "groq" else all_ids

        configured_model = getattr(self._client, attr)
        if chat_models and configured_model not in chat_models:
            replacement = model_healing.pick_replacement(chat_models, self._provider, "chat")
            if replacement:
                setattr(self._client, attr, replacement)

        ok = self._client.test_connection()
        self.finished_test.emit(self._provider, ok, chat_models)
