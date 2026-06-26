# TODO — plany i rzeczy do zrobienia

> Dom dla planów na przyszłość tego projektu. Czytany przez `/orchestrator` (lekki rzut oka na starcie) i `/autopilot` (brama strategiczna sprawdza „🎯 Aktywny fokus"). Plan **strategiczny** (oferta, pricing, kierunek rozwoju) żyje osobno w `.claude/memory/plan-rozwoju.md` i prowadzi go `/doradca` — tutaj trzymamy rzeczy **operacyjne**: co konkretnie zrobić.

## 🎯 Aktywny fokus
> Nad czym pracujemy teraz. `/autopilot` i `/orchestrator` konfrontują z tym nowe zakresy — zadanie spoza fokusu = sygnał do zatrzymania i decyzji.

- _(jeszcze nic — uzupełni się w trakcie projektu)_

## Backlog
> Pomysły i zadania na później. Bez kolejności — przenosisz do „Aktywnego fokusu", gdy wchodzą do realizacji.

### Onboarding / dystrybucja
- [ ] **Instrukcja krok po kroku: najprostsze uruchomienie z modelem Groq.**
  Groq jest najsprawniejszy (najszybsze STT + darmowy tier) i jest domyślnym torem.
  Cel: nietechniczny znajomy pobiera release z GitHub, wkleja klucz Groq i działa
  w < 5 min. Rozważyć: skąd wziąć klucz Groq (link + screeny), gdzie go wkleić w UI,
  domyślne ustawienia dla trybu „zero kosztów".

## Zrobione
> Krótki ślad po zamkniętych pozycjach (autopilot przenosi tu podsumowania paczek).

- [x] **Skill `/release`** — automatyzacja pakowania i publikacji release'u:
  `pyinstaller voiceflow.spec` → spakowanie `dist/VoiceFlow.exe` → utworzenie
  release'u w organizacyjnym repo GitHub (tag, changelog, upload artefaktu).
  (patrz `.claude/commands/release.md`)
