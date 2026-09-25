"""Pick a working replacement when a configured model disappears from a provider's live list."""

import re

# Modele nienadające się do roli czatu/asystenta, nawet jeśli provider je zwraca.
# Modele rozumujące (distill/r1/qwq/...) zostają widoczne w Settings — user może je
# wybrać świadomie — ale nie są auto-wybierane, bo wklejają <think> do tekstu.
_CHAT_EXCLUDE = (
    "guard", "whisper", "tts", "embed", "moderation", "orpheus",
    "distill", "-r1", "r1-", "reasoning", "thinking", "qwq",
)

# Kolejność preferencji przy auto-wyborze zamiennika. "" = dowolny pozostały kandydat.
_PREFERENCES = {
    ("gemini", "chat"): ["flash", ""],
    ("gemini", "stt"):  ["flash", ""],
    ("claude", "chat"): ["sonnet", "haiku", ""],
    ("groq", "chat"):   ["versatile", "llama", ""],
    ("groq", "stt"):    ["turbo", "whisper", ""],
}

# Pola configu, które trzeba sprawdzić dla danego providera i rodzaju modelu.
FIELDS = {
    ("gemini", "stt"):  ["stt_model"],
    ("gemini", "chat"): ["gemini_ai_model", "assistant_gemini_model"],
    ("claude", "chat"): ["claude_ai_model", "assistant_claude_model"],
    ("groq", "stt"):    ["groq_stt_model"],
    ("groq", "chat"):   ["groq_ai_model", "assistant_groq_model"],
}


def _rank(model_id: str):
    """Newest version wins; on a tie, the shorter (base) identifier wins over a
    suffixed/trimmed variant (e.g. "-lite").

    Release stamps (claude-sonnet-4-5-20250929) are ranked separately from version
    numbers — treating them as one sequence lets a date outweigh a minor version.
    """
    numbers = [int(n) for n in re.findall(r"\d+", model_id)]
    stamps = [n for n in numbers if 20000000 <= n <= 29999999]
    version = tuple(n for n in numbers if n not in stamps)
    return (version, max(stamps, default=0), -len(model_id))


def pick_replacement(available: list[str], provider: str, kind: str) -> str | None:
    """Best available model for (provider, kind), or None when nothing fits."""
    candidates = available
    if kind == "chat":
        candidates = [
            c for c in candidates
            if not any(bad in c.lower() for bad in _CHAT_EXCLUDE)
        ]
    if not candidates:
        return None

    stable = [c for c in candidates if "preview" not in c and "-exp" not in c]
    pool = stable if stable else candidates

    for pattern in _PREFERENCES.get((provider, kind), [""]):
        matching = [c for c in pool if pattern in c]
        if matching:
            return max(matching, key=_rank)

    return None


def heal_config(config, provider: str, kind: str, available: list[str]) -> list[tuple[str, str, str]]:
    """Return [(field, old, new)] for fields whose model vanished from `available`.
    Does NOT write anything — caller persists."""
    if not available:
        return []

    changes = []
    for field in FIELDS.get((provider, kind), []):
        old = getattr(config, field)
        if not old or old in available:
            continue
        new = pick_replacement(available, provider, kind)
        if new and new != old:
            changes.append((field, old, new))
    return changes
