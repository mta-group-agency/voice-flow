# CHANGELOG — log zadań i samodoskonalenia

> Jedna linia na zadanie, najnowsze na górze. Czytany przez `/orchestrator` na starcie
> (skan ostatnich ~10-15 wpisów) do wykrywania powtarzalnych zadań → kandydatów na nowe skille.

**Format wpisu:**
```
- RRRR-MM-DD · **Intencja:** <po co przyszedł użytkownik> · **Zrobiono:** <rezultat + wynik> · **Użyto:** <skille / narzędzia / Agent> · **Skill?:** <pomysł na skill lub —>
```

---

- 2026-07-01 · **Intencja:** popup „co nowego" był ubogi (goły link) — ma jasno pokazywać co się zmieniło, z podglądem wideo · **Zrobiono:** dociąganie prawdziwych notatek z GitHub gdy brak lokalnych + statyczny thumbnail Looma; wykryto i naprawiono martwy URL miniatury (zgadywany -with-play.gif → 403; rozwiązanie przez oEmbed → działający thumbnail_url), render QPixmap w workerze; reviewer 9/10; wydany **release v1.1.1** (commit 9692517) · **Użyto:** Agent (general-purpose) ×2 (w tym redirect w locie GIF→statyczny thumbnail przez SendMessage), /tester ×2, /reviewer, /release · **Skill?:** —
- 2026-07-01 · **Intencja:** wydać nową wersję z Asystentem AI i osadzić własne nagranie „co się zmieniło" dla kolegów · **Zrobiono:** release **v1.1.0** (bump 1.0.3→1.1.0, build .exe, commit 144c5e8 + tag, publikacja GitHub z assetem 130,4 MB), notatki w języku korzyści + linia Walkthrough z Loom — popup „co nowego" pokaże je kolegom · **Użyto:** /release · **Skill?:** —
- 2026-06-30 · **Intencja:** żeby koledzy po aktualizacji wiedzieli co nowego i jak używać, bez tłumaczenia przez autora (onboarding przy update) · **Zrobiono:** 3 popupy (pre-update "co zyskasz", post-update "co nowego", welcome przy 1. instalacji) na wspólnym WhatsNewDialog; treść z notatek GitHub release (markdown via QTextBrowser, bez QtWebEngine), wideo jako przycisk-link (Loom/ClickUp), stan last_run_version + pending_update_* (offline-safe), /release rozbudowany o język wartości + linię Walkthrough; reviewer 8/10, .exe przebudowany · **Użyto:** Explore + Agent (general-purpose) ×3, /tester ×2, /reviewer · **Skill?:** —
- 2026-06-30 · **Intencja:** odróżnić tryby overlaya kolorem (bez czytania napisu) + naprawić czytelność białego napisu na beżowym tle · **Zrobiono:** "wypełniony pill" w kolorze trybu (dyktowanie=niebieski #2563EB, asystent=fiolet #7C3AED), biały tekst (kontrast 5,2–5,7:1 WCAG AA), processing przyciemnia kolor o 18%, equalizer/kropka/stop w bieli; dark+light; reviewer 9/10, .exe przebudowany · **Użyto:** Explore + Agent (general-purpose), /tester, /reviewer · **Skill?:** —
- 2026-06-29 · **Intencja:** dodać drugi hotkey działający jako asystent AI (mówisz polecenie → AI wykonuje i wkleja wynik), obok istniejącego czystego STT · **Zrobiono:** zaimplementowano niezależny tor "assistant" (drugi HotkeyManager, run_assistant w klientach Groq/Gemini/Claude, kontekst ze schowka, edytowalny prompt, rozróżnienie na overlayu); hotkey asystenta startowo pusty (użytkownik ustawia sam), UI po angielsku; reviewer 9/10, gotowe — wymaga przebudowy .exe · **Użyto:** Agent (general-purpose) ×3, /tester ×3, /reviewer ×2 · **Skill?:** —
