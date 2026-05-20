# VoiceFlow — instrukcje dla Claude Code

## Stack technologiczny

- **Język**: Python 3.x
- **GUI**: PyQt6 (frameless window, system tray, overlay)
- **Audio**: PyAudio (PCM 16 kHz mono)
- **STT**: Google Gemini (`gemini-2.5-flash`)
- **AI post-processing**: Anthropic Claude (`claude-sonnet-4-6`) lub Gemini
- **Baza danych**: Turso (libSQL, HTTP API)
- **Hotkey**: pynput (globalny nasłuch, domyślnie prawy Alt)
- **Packaging**: PyInstaller → `dist/VoiceFlow.exe`

## Struktura projektu

```
VoiceFlow/
├── main.py                  # punkt wejścia — QApplication + VoiceFlowApp
├── voiceflow.spec           # konfiguracja PyInstaller
├── requirements.txt
├── assets/                  # ikony (.ico, .png) — bundlowane do .exe
├── voiceflow/
│   ├── app.py               # bootstrap: inicjalizacja wszystkich komponentów
│   ├── api/                 # klienty AI (claude_client.py, gemini_client.py)
│   ├── config/              # AppConfig (schema.py) + zapis do %APPDATA%/VoiceFlow/config.json
│   ├── core/                # pipeline.py (maszyna stanów), audio, hotkey, text injector
│   ├── storage/             # history_db.py (Turso)
│   └── ui/                  # main_window, tray, overlay, tabs/, widgets/
├── build/                   # artefakty PyInstaller (nie commitować)
└── dist/VoiceFlow.exe       # finalny plik wykonywalny
```

## Pipeline (maszyna stanów)

```
IDLE → RECORDING → TRANSCRIBING → PROCESSING → INJECTING → IDLE
```

Każda zmiana kodu musi być spójna z tym przepływem. Hotkey (prawy Alt) wyzwala nagrywanie; audio → Gemini STT → opcjonalny AI post-processing → wklejenie tekstu przez schowek + Ctrl+V.

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
