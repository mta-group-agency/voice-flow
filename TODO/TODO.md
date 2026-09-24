# TODO — plany i rzeczy do zrobienia

> Dom dla planów na przyszłość tego projektu. Czytany przez `/orchestrator` (lekki rzut oka na starcie) i `/autopilot` (brama strategiczna sprawdza „🎯 Aktywny fokus"). Plan **strategiczny** (oferta, pricing, kierunek rozwoju) żyje osobno w `.claude/memory/plan-rozwoju.md` i prowadzi go `/doradca` — tutaj trzymamy rzeczy **operacyjne**: co konkretnie zrobić.

## 🎯 Aktywny fokus
> Nad czym pracujemy teraz. `/autopilot` i `/orchestrator` konfrontują z tym nowe zakresy — zadanie spoza fokusu = sygnał do zatrzymania i decyzji.

- _(jeszcze nic — uzupełni się w trakcie projektu)_

## Backlog
> Pomysły i zadania na później. Bez kolejności — przenosisz do „Aktywnego fokusu", gdy wchodzą do realizacji.

### Settings — drobiazgi z review v1.3.0
- [ ] **Ostrzeżenie o braku klucza w sekcji Speech-to-Text.** Dwie sekcje AI mają już czerwony
  label pod wyborem providera, STT nie ma. Przy samym kluczu Claude STT zostaje na „Gemini"
  bez sygnału, a pierwsze dyktowanie odsyła po klucz, nie mówiąc, że Claude w ogóle nie robi
  transkrypcji. Treść w stylu: „Claude does not do transcription — pick Groq, Gemini or Local."
- [ ] **Etykieta „Gemini (default)" w liście providerów STT.** Przeczy zdaniu o Groqu dwa wiersze
  wyżej i temu, co apka sama robi po wklejeniu klucza Groq.

### Onboarding / dystrybucja
- [ ] **Instrukcja krok po kroku: najprostsze uruchomienie z modelem Groq.**
  Groq jest najsprawniejszy (najszybsze STT + darmowy tier) i jest domyślnym torem.
  Cel: nietechniczny znajomy pobiera release z GitHub, wkleja klucz Groq i działa
  w < 5 min. Rozważyć: skąd wziąć klucz Groq (link + screeny), gdzie go wkleić w UI,
  domyślne ustawienia dla trybu „zero kosztów".

### Logging, diagnostyka, obsługa błędów
- [ ] **Anulowane dyktowanie wklejane do nowego.** Anuluj dyktowanie w trakcie transkrypcji i natychmiast nagraj nowe — spóźniony wynik starego przebiegu przechodzi przez AI i jest wklejany. Przyczyna: flaga _cancel_flag jest wspólna dla wszystkich przebiegów. Rozwiązanie: numer przebiegu sprawdzany w callbackach. Priorytet wysoki.
- [ ] **Błąd AI: surowa transkrypcja przepada.** Błędy post-processingu (429, timeout, brak sieci) powodują, że nic się nie wkleja i dyktowanie znika, choć surowa transkrypcja jest gotowa. Rozwiązanie: wklejać surowy tekst z komunikatem o błędzie, jak przy braku klucza do AI.
- [ ] **Awaria mikrofonu raportowana jako timeout.** Gdy mikrofon ulegnie awarii, po 30 s pojawia się komunikat "Processing timed out" zamiast błędu mikrofonu. Potrzebne: sprawdzenie logu (step=?) i poprawianie diagnozy na wcześniejszym etapie.
- [ ] **Log diagnostyczny: czasy, stany, błędy Turso.** (1) Dodać czasy stt_ms/ai_ms/total_ms do linii "Dictation done"; (2) zmienić "ai=None/None" na "ai=off"; (3) logować błędy Turso zamiast je połykać (silent catch).
- [ ] **README: ostrzeżenie o bezpieczeństwie logu.** Przy wysyłaniu logu dopisać instrukcję: "wyślij tylko voiceflow.log, nie config.json (tam są klucze API)".

## Zrobione
> Krótki ślad po zamkniętych pozycjach (autopilot przenosi tu podsumowania paczek).

- [x] **Skill `/release`** — automatyzacja pakowania i publikacji release'u:
  `pyinstaller packaging/windows/voiceflow.spec --distpath dist/windows --workpath build/windows` →
  spakowanie `dist/windows/VoiceFlow.exe` → utworzenie release'u w organizacyjnym repo GitHub
  (tag, changelog, upload artefaktu). (patrz `.claude/commands/release.md`)
