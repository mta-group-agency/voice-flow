# VoiceFlow — instrukcje dla Claude Code

## Cel, odbiorca, scope

- **Czym jest**: desktopowy klon Wispr Flow na Windows — narzędzie STT. Hotkey →
  nagrywanie → transkrypcja → opcjonalny AI post-processing → wklejenie tekstu.
- **Dla kogo**: przede wszystkim dla autora (narzędzie osobiste); przy okazji dzielone
  z kolegami przez release'y w organizacyjnym repo GitHub — każdy na własnych kluczach API.
- **Cele nadrzędne**: stabilność (zero crashy) + koszt ≈ 0 zł (darmowe tory domyślne).
- **Scope**: Windows. **Poza scope (świadomie)**: macOS, Linux, web, mobile, i18n UI.
- Szerszy kontekst i plan: `.claude/memory/` (`produkt-kontekst.md`, `plan-rozwoju.md`, `TODO.md`).

## Stack technologiczny

- **Język**: Python 3.x
- **GUI**: PyQt6 (frameless window, system tray, overlay)
- **Audio**: PyAudio (PCM 16 kHz mono)
- **STT** (wybór dostawcy): **Groq** (`whisper-large-v3-turbo`) — domyślny/rekomendowany
  tor (najszybszy, darmowy tier); **Gemini** (`gemini-2.5-flash`); **lokalny Whisper**
  (faster-whisper) — fallback offline, 0 zł, bez kluczy.
- **AI post-processing** (wybór dostawcy): Groq (`llama-3.3-70b-versatile`) /
  Gemini (`gemini-2.5-flash`) / Anthropic Claude (`claude-sonnet-4-6`).
- **Baza danych**: Turso (libSQL, HTTP API) — opcjonalna (historia transkrypcji).
- **Hotkey**: pynput (globalny nasłuch, domyślnie prawy Alt)
- **Packaging**: PyInstaller → `dist/VoiceFlow.exe`

## Struktura projektu

```
VoiceFlow/
├── main.py                  # punkt wejścia — QApplication + VoiceFlowApp
├── voiceflow.spec           # konfiguracja PyInstaller
├── generate_icons.py        # generowanie ikon (.ico/.png) z assets
├── requirements.txt
├── assets/                  # ikony (icon.ico, icon.png, icon_rec/proc.png) — bundlowane do .exe
├── .claude/memory/          # kontekst produktu, plan rozwoju, TODO (backlog pomysłów)
├── voiceflow/
│   ├── app.py               # bootstrap: inicjalizacja wszystkich komponentów
│   ├── api/                 # base_client, claude_client, gemini_client, groq_client, local_whisper_client
│   ├── config/              # schema.py (AppConfig) + settings_manager.py → %APPDATA%/VoiceFlow/config.json
│   ├── core/                # pipeline.py (maszyna stanów), audio_recorder, hotkey_manager,
│   │                        #   text_injector, autostart, logger
│   ├── storage/             # history_db.py (Turso, opcjonalna)
│   └── ui/                  # main_window, tray, overlay, styles, theme,
│                            #   tabs/ (home, history, stats, settings), widgets/ (toggle_switch, hotkey_capture)
├── build/                   # artefakty PyInstaller (nie commitować)
└── dist/VoiceFlow.exe       # finalny plik wykonywalny
```

## Pipeline (maszyna stanów)

```
IDLE → RECORDING → TRANSCRIBING → PROCESSING → INJECTING → IDLE
```

Każda zmiana kodu musi być spójna z tym przepływem. Hotkey (prawy Alt) wyzwala nagrywanie; audio → STT (Groq / Gemini / lokalny Whisper) → opcjonalny AI post-processing → wklejenie tekstu przez schowek + Ctrl+V. Gdy STT i AI to oba Gemini, pipeline robi jedno połączone wywołanie (`transcribe_and_process`). Timeout przetwarzania: 30 s (auto-cancel).

## Kluczowe zasady

### 1. Zmiany muszą być widoczne w VoiceFlow.exe

Każda modyfikacja kodu **musi** przekładać się na rzeczywiste zachowanie aplikacji po uruchomieniu `dist/VoiceFlow.exe`. Oznacza to:

- Zmiany w logice, UI, konfiguracji — edytuj pliki źródłowe w `voiceflow/`.
- Zmiany w assets (ikony, style) — upewnij się, że są bundlowane przez `voiceflow.spec`.
- Po każdej serii zmian przypomnij użytkownikowi o przebudowaniu .exe komendą:
  ```bash
  pyinstaller voiceflow.spec
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

```bash
# W katalogu głównym projektu:
pyinstaller voiceflow.spec
# Gotowy plik: dist/VoiceFlow.exe
```

Przebudowa jest wymagana po każdej zmianie kodu, żeby efekty były widoczne dla użytkownika.
