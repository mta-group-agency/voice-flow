# VoiceFlow — plan rozwoju

Aktualizowany na bieżąco. Czytany przez `/doradca` (KROK 0) na starcie sesji.
Statusy: TODO / W TOKU / DONE.

Ostatnia aktualizacja: 2026-06-17 (inicjalizacja przez `/initiate`).

## Cele nadrzędne

1. Stabilność — zero crashy.
2. Koszt ≈ 0 zł — darmowe tory domyślne (Groq jako standard).

## Priorytet teraz

- [ ] (brak aktywnego zadania — do ustalenia w następnej sesji)

## Horyzont krótki

- [ ] TODO — patrz [TODO.md](TODO.md): instrukcja onboardingu dla Groq, skill `/release`.

## Znane bolączki / obszary ryzyka

- Lokalny Whisper: generalnie stabilny po ostatnich fixach (pobieranie modelu,
  timeout, stale `.locks`). Nie jest torem domyślnym — to fallback offline.

## Zrobione (historia)

- 2026-06-17 — inicjalizacja projektu (`/initiate`): aktualizacja CLAUDE.md,
  utworzenie `.claude/memory/` (kontekst produktu, plan rozwoju, TODO).
- (wcześniejsze fixy — patrz git log: timeout 30s, thread-safe queue,
  pobieranie modeli, status bar / dropdown modeli)