# VoiceFlow — instrukcje dla Claude Code

## Cel, odbiorca, scope

- **Czym jest**: desktopowy klon Wispr Flow na Windows — narzędzie STT. Hotkey →
  nagrywanie → transkrypcja → opcjonalny AI post-processing → wklejenie tekstu.
- **Dla kogo**: przede wszystkim dla autora (narzędzie osobiste); przy okazji dzielone
  z kolegami przez release'y w organizacyjnym repo GitHub — każdy na własnych kluczach API.
- **Cele nadrzędne**: stabilność (zero crashy) + koszt ≈ 0 zł (darmowe tory domyślne).
- **Scope**: Windows dziś, port na macOS w toku (plan: `TODO/plan-mac.md`).
  **Poza scope (świadomie)**: Linux, web, mobile, i18n UI.
- Szerszy kontekst i plan strategiczny: `.claude/memory/` (`produkt-kontekst.md`, `plan-rozwoju.md`).
  Operacyjne TODO (aktywny fokus + backlog) żyje w `TODO/TODO.md` — to je czyta `/orchestrator` na starcie.

## Stack technologiczny

- **Język**: Python 3.11-3.13 (u autora 3.13). 3.14 odpada: PyAudio nie ma dla niej gotowej paczki na Windows.
- **GUI**: PyQt6 (frameless window, system tray, overlay)
- **Audio**: PyAudio (PCM 16 kHz mono)
- **STT** (wybór dostawcy): **Groq** (`whisper-large-v3-turbo`) — domyślny/rekomendowany
  tor (najszybszy, darmowy tier); **Gemini** (`gemini-2.5-flash`); **lokalny Whisper**
  (faster-whisper) — fallback offline, 0 zł, bez kluczy.
- **AI post-processing** (wybór dostawcy): Groq (`llama-3.3-70b-versatile`) /
  Gemini (`gemini-2.5-flash`) / Anthropic Claude (`claude-sonnet-5`).
- **Baza danych**: Turso (libSQL, HTTP API) — opcjonalna (historia transkrypcji).
- **Hotkey**: pynput (globalny nasłuch, domyślnie prawy Alt)
- **Packaging**: PyInstaller → `dist/windows/VoiceFlow.exe`

## Struktura projektu

```
VoiceFlow/
├── main.py                  # punkt wejścia — QApplication + VoiceFlowApp
├── generate_icons.py        # generuje ikony .png (tray) do assets/common; icon.ico jest commitowany as-is
├── requirements.txt         # -r requirements/windows.txt (kompatybilność wsteczna)
├── requirements/
│   ├── base.txt             # zależności wspólne (PyQt6, pynput, requests, anthropic, faster-whisper)
│   ├── windows.txt          # base + PyAudio + PyInstaller
│   └── macos.txt            # base + PyAudio + PyInstaller (wymaga portaudio z brew)
├── packaging/
│   ├── windows/
│   │   ├── voiceflow.spec       # konfiguracja PyInstaller (Windows)
│   │   └── build.ps1            # one-command Windows build
│   └── macos/                   # konfiguracja PyInstaller (macOS), na razie tylko README z planem
├── assets/
│   ├── common/               # ikony wspólne (icon.png, icon_rec.png, icon_proc.png), bundlowane do .exe
│   ├── windows/               # icon.ico
│   └── macos/                 # icns przyjdzie później, na razie tylko README z planem
├── .claude/memory/          # kontekst produktu + plan rozwoju (strategia, prowadzona przez /doradca)
├── TODO/                    # operacyjne TODO (TODO.md: aktywny fokus + backlog) — czytane przez /orchestrator
├── TEMP/                    # strefa robocza (materiały + artefakty robocze), gitignorowana
├── voiceflow/
│   ├── app.py               # bootstrap: inicjalizacja wszystkich komponentów
│   ├── api/                 # base_client, claude_client, gemini_client, groq_client, local_whisper_client
│   ├── config/              # schema.py (AppConfig) + settings_manager.py → %APPDATA%/VoiceFlow/config.json
│   ├── core/                # pipeline.py (maszyna stanów), audio_recorder, hotkey_manager,
│   │                        #   text_injector, autostart, logger
│   ├── storage/             # history_db.py (Turso, opcjonalna)
│   └── ui/                  # main_window, tray, overlay, styles, theme,
│                            #   tabs/ (home, history, stats, settings), widgets/ (toggle_switch, hotkey_capture)
├── build/windows/           # artefakty PyInstaller (nie commitować)
└── dist/windows/VoiceFlow.exe   # finalny plik wykonywalny
```

## Pipeline (maszyna stanów)

```
IDLE → RECORDING → TRANSCRIBING → PROCESSING → INJECTING → IDLE
```

Każda zmiana kodu musi być spójna z tym przepływem. Hotkey (prawy Alt) wyzwala nagrywanie; audio → STT (Groq / Gemini / lokalny Whisper) → opcjonalny AI post-processing → wklejenie tekstu przez schowek + Ctrl+V. Gdy STT i AI to oba Gemini, pipeline robi jedno połączone wywołanie (`transcribe_and_process`). Timeout przetwarzania: 30 s (auto-cancel).

## Kluczowe zasady

### 1. Zmiany muszą być widoczne w VoiceFlow.exe

Każda modyfikacja kodu **musi** przekładać się na rzeczywiste zachowanie aplikacji po uruchomieniu `dist/windows/VoiceFlow.exe`. Oznacza to:

- Zmiany w logice, UI, konfiguracji — edytuj pliki źródłowe w `voiceflow/`.
- Zmiany w assets (ikony, style) — upewnij się, że są bundlowane przez `packaging/windows/voiceflow.spec`.
- Po każdej serii zmian przypomnij użytkownikowi o przebudowaniu .exe komendą:
  ```powershell
  powershell -ExecutionPolicy Bypass -File packaging/windows/build.ps1
  ```
- Nie wprowadzaj zmian tylko w `dist/` bezpośrednio — zawsze źródło jest nadrzędne.

### 2. Podejście do requestów użytkownika

Zanim zaczniesz implementować:

1. **Dopytaj** o niejasne wymagania — co dokładnie ma robić, jak ma wyglądać, jakie edge case'y uwzględnić.
2. **Zasugeruj ulepszenia** requestu — jeśli wiesz z doświadczenia lub z internetu, że istnieje lepsze podejście (biblioteka, wzorzec, UX pattern), zaproponuj je zanim zaczniesz kodować.
3. **Korzystaj z aktualnej wiedzy** — przed implementacją wyszukaj najlepsze praktyki dla danego problemu (PyQt6, audio processing, AI APIs, UX dla desktop apps), żeby nie implementować przestarzałych rozwiązań.
4. Po uzgodnieniu podejścia — implementuj bez zbędnych pytań.

### 3. Standardy kodu

- Nie dodawaj komentarzy wyjaśniających CO robi kod — nazwy są wystarczające.
- Komentarz tylko gdy WHY jest nieoczywiste (obejście bugu, ukryte ograniczenie).
- Nie dodawaj obsługi błędów dla scenariuszy, które nie mogą zajść.
- Nie wprowadzaj abstrakcji na zapas — trzy podobne linie są lepsze niż przedwczesna abstrakcja.
- Żadnych emoji w kodzie ani dokumentacji, chyba że użytkownik wyraźnie prosi.

### 4. Bezpieczeństwo

- Klucze API przechowywane tylko w `%APPDATA%/VoiceFlow/config.json` — nigdy w kodzie źródłowym ani w git.
- `.gitignore` musi wykluczać `config.json`, `dist/`, `build/`, `__pycache__/`.

## Jak przebudować .exe

```powershell
# Z katalogu głównego repo:
powershell -ExecutionPolicy Bypass -File packaging/windows/build.ps1
# Gotowy plik: dist/windows/VoiceFlow.exe
```

Skrypt bierze Pythona z `.venv` w repo, a gdy go nie ma, `python` z PATH (tak buduje autor, bez .venv). Najpierw sprawdza, czy ten Python ma PyInstaller, PyQt6, pynput, pyaudio, requests i anthropic, potem wywołuje `python -m PyInstaller packaging/windows/voiceflow.spec --distpath dist/windows --workpath build/windows`. Inny interpreter: parametr `-Python <ścieżka>`.

Przebudowa jest wymagana po każdej zmianie kodu, żeby efekty były widoczne dla użytkownika.
