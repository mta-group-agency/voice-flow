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
