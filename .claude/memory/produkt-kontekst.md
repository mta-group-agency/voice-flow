# VoiceFlow — kontekst produktu

Zwięzły kontekst dla skilli strategicznych (`/doradca`) i orientacji w projekcie.

## Czym jest

Desktopowy klon Wispr Flow na Windows — narzędzie STT (Speech-to-Text). Hotkey
(domyślnie prawy Alt) uruchamia nagrywanie; mowa → transkrypcja → opcjonalny
AI post-processing → tekst wklejany w aktywne pole (schowek + Ctrl+V).

## Dla kogo i po co

- **Przede wszystkim dla autora** — narzędzie osobiste, robione pod własne potrzeby
  i własny workflow na Windowsie.
- **Przy okazji** dzielone z kolegami i koleżankami przez release'y w organizacyjnym
  repo GitHub. Każdy używa **własnych kluczy API**.
- Nie robimy go „na siłę" pod cudze wymagania — priorytet to wygoda autora.

## Cele (definicja sukcesu)

1. **Stabilność** — działa bez crashy.
2. **Koszt ≈ 0 zł** — darmowe tory STT/AI są domyślne i wystarczające.

## Tory STT / AI

- **Groq** — docelowy, standardowy, rekomendowany tor (najszybszy, darmowy tier).
- **Gemini** — alternatywa (combined STT+AI w jednym wywołaniu).
- **Lokalny Whisper** (faster-whisper) — stabilny fallback offline, 0 zł, bez kluczy.
- AI post-processing: Groq / Gemini / Claude.

## Scope

- **W scope:** Windows.
- **Poza scope (świadomie):** macOS, Linux, web, mobile, i18n UI.

## Dystrybucja

- Organizacyjne repo GitHub + release'y (jeden release już opublikowany).
- Brak współdzielonych kluczy — onboarding polega na wklejeniu własnego klucza API.