# Plan: VoiceFlow na Maca (release na GitHubie) + rozdzielenie Windows / Mac w repo

Stan: F1 (układ folderów) zrobione. Dalej: F2 (pomocnik błędów) i F3 (kod pod Maca), potem
F4 (build Maca w GitHub Actions). Szczegóły niżej, w sekcji Fazy wdrożenia.

Kroki oznaczone Agent / tester / reviewer dotyczą pracy z Claude Code; człowiek może je wykonać ręcznie.

## Kontekst

Dziś VoiceFlow działa tylko na Windowsie. CLAUDE.md wpisywał macOS jako poza scope; po F1 scope
obejmuje port na Maca. Chcemy wypuszczać w tym samym repo (`mta-group-agency/voice-flow`) drugą
paczkę dla kolegów z Makami. Ustalone z Mateuszem:
- build na Maca robi darmowy runner GitHub Actions (`macos-latest`), testuje kolega z Makiem,
- bez konta Apple Developer (0 zł): podpis ad-hoc + instrukcja odblokowania w Gatekeeperze
  (macOS 14 i starsze: prawy klik > Otwórz; macOS 15 Sequoia i nowsze: Ustawienia systemowe >
  Prywatność i ochrona > „Otwórz mimo to" po pierwszym zablokowanym uruchomieniu),
- na Macu na start tylko baner „jest nowa wersja, pobierz", autoaktualizacja później.

Audyt kodu pokazał, że nie ma ani jednego `sys.platform`; Windows jest wpięty na sztywno w ~12 miejscach.

## Co blokuje Maca dziś (z audytu)

| Obszar | Plik | Problem na Macu |
|---|---|---|
| Jedna instancja | `main.py:13-24` | `ctypes.windll` (mutex, MessageBox): crash przy starcie |
| Autostart | `voiceflow/core/autostart.py` | `import winreg`: crash przy imporcie |
| Ścieżki danych | `config/settings_manager.py:23`, `core/logger.py:8`, `api/local_whisper_client.py:16` | `%APPDATA%` nie istnieje, dane lądują w `~/VoiceFlow` |
| Wklejanie | `core/text_injector.py:30-38` | Ctrl+V zamiast Cmd+V |
| Otwórz folder | `ui/tabs/settings_tab.py:667` | `os.startfile` nie istnieje |
| Cień okna | `ui/main_window.py:394-407` | `dwmapi`, dziś połykane przez `except: pass` |
| Overlay | `ui/overlay.py:102-104` | brak `WindowDoesNotAcceptFocus` / `WA_ShowWithoutActivating`: overlay może zabrać fokus i tekst wklei się nie tam |
| Tray | `ui/tray.py:66` | otwiera okno tylko na dwuklik, na Macu pasek menu nie ma dwukliku |
| Etykiety klawiszy | `ui/widgets/hotkey_capture.py:23-35`, `settings_tab.py:114,124` | „AltGr", „Win" zamiast „Prawy Option", „Cmd" |
| Czcionki | `ui/theme.py` | Segoe UI / Cascadia bez zamienników Mac |
| Aktualizacje | `core/updater.py:24-26,115-243` | asset na sztywno `VoiceFlow.exe`, podmiana przez `.bat` |
| Build | `packaging/windows/voiceflow.spec` | ukryte importy `pynput._win32`, brak `BUNDLE` (.app), brak `Info.plist` z opisem mikrofonu |
| Release | `.claude/commands/release.md` (lokalny plik autora, `.claude/` jest poza gitem) | `tasklist`, jeden asset `.exe` |

## Rekomendowany układ folderów

Rozdzielamy **pakowanie i buildy**, a **kod aplikacji zostaje wspólny**. Dwie kopie `voiceflow/`
oznaczałyby, że każdą poprawkę robi się dwa razy i wersje się rozjeżdżają. Różnice między
systemami zamykamy w jednym małym module `voiceflow/platform/`.

```
VoiceFlow/
├── main.py                        # wspólny
├── voiceflow/                     # wspólny kod
│   └── platform/                  # NOWE: jedyne miejsce z różnicami systemowymi
│       ├── __init__.py            # wybiera windows albo macos po sys.platform
│       ├── windows.py             # mutex, winreg, dwmapi, os.startfile, %APPDATA%
│       └── macos.py               # QLockFile, LaunchAgent, open, ~/Library/Application Support
├── assets/
│   ├── common/                    # icon.png, icon_rec.png, icon_proc.png
│   ├── windows/icon.ico
│   └── macos/icon.icns (+ ikony paska menu w trybie template)
├── packaging/
│   ├── windows/voiceflow.spec     # przeniesiony obecny spec
│   └── macos/
│       ├── voiceflow.spec         # BUNDLE -> VoiceFlow.app
│       ├── entitlements.plist
│       └── build.sh               # build + podpis ad-hoc + zip
├── .github/workflows/build-macos.yml   # NOWE: build Maca w chmurze na tagu vX.Y.Z
├── dist/
│   ├── windows/VoiceFlow.exe
│   └── macos/VoiceFlow.app, VoiceFlow-macos-arm64.zip
└── requirements/ (base.txt, windows.txt, macos.txt)
```

Nowe komendy buildu:
- Windows: `powershell -ExecutionPolicy Bypass -File packaging/windows/build.ps1`
- Mac (w CI albo na Macu): `packaging/macos/build.sh`

## Fazy wdrożenia

### F1. Porządek folderów, Windows bez zmian dla użytkownika
- przenieść spec, ikony, requirements wg układu wyżej; `dist/windows/`,
- zaktualizować CLAUDE.md (scope: Windows + macOS, nowe komendy), `release.md`, `.gitignore`, pamięć projektu,
- **warunek wyjścia:** `dist/windows/VoiceFlow.exe` buduje się i działa identycznie jak 1.3.0.
- Wykonanie: Agent sonnet, potem tester.

### F2. Pomocnik błędów: przy crashu i błędzie użytkownik wie, co zrobić (Windows i Mac)
Dziś: `core/logger.py:18-26` łapie nieobsłużone wyjątki tylko do logu (użytkownik nic nie widzi),
`core/pipeline.py:528-530` pokazuje surowe „Error: <treść wyjątku>", wyjątki w wątkach pobocznych
i twarde crashe biblioteki C (PyAudio, pynput) nie zostawiają śladu. Log (poziom DEBUG) zapisuje też
adresy zapytań do Gemini razem z kluczem (`?key=AIza...`), więc dziś nie da się go wysłać bez ręcznego czyszczenia.

Co dodajemy:
1. **Katalog znanych błędów** `voiceflow/core/error_help.py`: rozpoznaje błąd (typ wyjątku, kod HTTP,
   fragment treści) i zwraca: krótki tytuł, 1-2 zdania „co zrobić", przycisk naprawczy.
   Startowe wpisy:
   - zły lub wygasły klucz (401/403) -> „Sprawdź klucz", przycisk otwiera Ustawienia > Klucze API,
   - limit darmowego planu (429) -> „Odczekaj minutę albo przełącz dostawcę", przycisk do ustawień STT,
   - brak internetu / timeout -> „Sprawdź połączenie albo włącz lokalny Whisper",
   - brak mikrofonu / brak zgody -> przycisk otwiera ustawienia prywatności mikrofonu systemu
     (Windows `ms-settings:privacy-microphone`, Mac panel Mikrofon),
   - Mac: brak zgody Dostępność / Monitorowanie wejścia -> przycisk otwiera właściwy panel,
   - błąd pobierania modelu Whisper (miejsce na dysku, sieć),
   - nieznany błąd -> ogólna instrukcja + „Kopiuj raport".
2. **Nic nie ginie po cichu:** `sys.excepthook`, `threading.excepthook` i błędy workerów przechodzą
   przez katalog; użytkownik dostaje powiadomienie z przyciskiem „Jak naprawić" (okno z instrukcją).
3. **Twardy crash:** `faulthandler` pisze do `crash.log` w folderze danych; przy starcie zapisuje się
   znacznik „sesja trwa", przy czystym wyjściu znika. Jeśli przy następnym starcie znacznik został,
   okno „VoiceFlow zamknął się nieoczekiwanie": prawdopodobna przyczyna z katalogu (na podstawie
   ostatnich linii logu), przyciski „Kopiuj raport", „Otwórz folder logów", „Zgłoś na GitHubie".
4. **Pętla crashy:** dwa crashe z rzędu tuż po starcie -> propozycja „Uruchom z domyślnymi
   ustawieniami" (stary `config.json` zostaje jako kopia, klucze API przeniesione).
5. **Raport do skopiowania:** wersja, system, wybrani dostawcy, ostatnie ~200 linii logu, klucze API
   wycięte (wzorce `gsk_`, `sk-ant-`, `AIza`). Tylko do schowka, nic nie wysyła się samo (0 zł, prywatność).
6. **Przycisk „Diagnostyka" w Ustawieniach:** jedno kliknięcie sprawdza mikrofon, klucze (lekkie
   zapytanie testowe), internet i na Macu uprawnienia; lista zielone/czerwone z przyciskiem naprawy
   przy każdej czerwonej. Kolega z Makiem odsyła wynik jednym „Kopiuj raport".

Teksty w języku interfejsu aplikacji. Wykonanie: Agent sonnet (katalog + haki), tester (w tym
wymuszony crash i wymuszone 401/429), reviewer (czy instrukcje są zrozumiałe dla nietechnicznego kolegi).

### F3. Warstwa platformowa w kodzie (na Windowsie nic się nie zmienia)
- `voiceflow/platform/`: ścieżka danych, jedna instancja, autostart, otwarcie folderu, cień okna, klawisz wklejania,
- podpiąć w `main.py`, `autostart.py`, `settings_manager.py`, `logger.py`, `local_whisper_client.py`, `settings_tab.py`, `main_window.py`, `text_injector.py`,
- overlay: dodać flagi bez fokusu (pomaga też Windowsowi),
- tray: pojedyncze kliknięcie na Macu, etykiety klawiszy i czcionki zależne od systemu,
- tekst „zalecane GPU NVIDIA" pokazywać tylko na Windowsie,
- updater: nazwa assetu zależna od systemu (`VoiceFlow.exe` zostaje bez zmian, stare instalacje dalej się aktualizują); na Macu `can_self_update()` = False, więc zostaje baner z linkiem do pobrania,
- Mac: przy starcie sprawdzić uprawnienia Dostępności / Monitorowania wejścia i pokazać okno z instrukcją, zamiast cicho nie reagować na klawisz.
- Wykonanie: Agent sonnet (moduł po module), tester po każdym.

### F4. Build na Maca w chmurze
Zaczynać po F3: bez niej `VoiceFlow.app` się zbuduje, ale wywali się na starcie. Budować da się tylko
na Macu albo w GitHub Actions (PyInstaller nie robi `.app` na Windowsie). Docelowe pliki opisuje też
`packaging/macos/README.md`.
- `packaging/macos/voiceflow.spec` (punkt wyjścia: `packaging/windows/voiceflow.spec`): ukryte importy
  `pynput.keyboard._darwin` i `pynput.mouse._darwin`, `BUNDLE` z `Info.plist`
  (`NSMicrophoneUsageDescription`, `LSUIElement` = tylko ikona w pasku menu, bez Docka), `.icns`,
- `build.sh`: `brew install portaudio`, `pip install -r requirements/macos.txt`, build,
  `codesign --force --deep -s -` (ad-hoc), zip przez `ditto`,
- workflow `.github/workflows/build-macos.yml` (GitHub szuka workflowów tylko w `.github/workflows/`,
  to jedyny wyjątek od `packaging/<system>/`): na push tagu `v*` buduje i dokleja
  `VoiceFlow-macos-arm64.zip` do tego samego release'u; do doklejania potrzebuje `permissions: contents: write`,
- `generate_icons.py`: dodatkowo `.icns` i ikony paska menu (do `assets/macos/`, opis w `assets/macos/README.md`).
- Wykonanie: Agent sonnet, błędy builda: `build-error-resolver`.

### F5. Test na żywym Macu (kolega)
Checklista do przekazania (bez tego nie wydajemy):
1. pobranie zipa, odblokowanie w Gatekeeperze (macOS 14 i starsze: prawy klik > Otwórz;
   macOS 15 i nowsze: Ustawienia systemowe > Prywatność i ochrona > „Otwórz mimo to"),
   aplikacja startuje, ikona w pasku menu,
2. prośba o mikrofon i uprawnienia klawiatury, po nadaniu prawy Option nagrywa,
3. tekst wkleja się w Notatkach, Slacku, przeglądarce (Cmd+V, fokus zostaje),
4. Esc anuluje, overlay widoczny także nad aplikacją pełnoekranową,
5. drugie uruchomienie nie tworzy drugiej instancji, autostart po wylogowaniu,
6. lokalny Whisper pobiera model i transkrybuje (CPU),
7. baner nowej wersji otwiera stronę pobierania.

### F6. Release obu wersji
- `/release`: bump, build `.exe` lokalnie, tag, `gh release create` z `.exe`; CI po tagu dokleja zip Maca,
- sekcja „Instalacja na Macu" w notatkach release'u (odblokowanie w Gatekeeperze: macOS 14
  i starsze prawy klik > Otwórz, macOS 15 i nowsze Ustawienia systemowe > Prywatność i ochrona >
  „Otwórz mimo to"; uprawnienia; co zrobić, gdy po aktualizacji hotkey przestał działać:
  ponownie zaznaczyć w Dostępności),
- każdy release ma dokładnie dwa pliki do pobrania: `VoiceFlow.exe` (Windows) i
  `VoiceFlow-macos-arm64.zip` (Mac: Safari rozpakowuje go do `VoiceFlow.app`, wystarczy
  przeciągnąć do Applications),
- sprawdzenie: w release wiszą oba pliki, stary Windows 1.3.0 widzi aktualizację.

### F7. Później (osobne zadanie w TODO)
Autoaktualizacja Maca (podmiana całego `.app`), ewentualnie konto Apple, szybszy lokalny Whisper na Apple Silicon (mlx-whisper), wersja Intel.

## Główne ryzyka
- **pynput na nowszych macOS:** znane zgłoszenia crashy, gdy nasłuch klawiatury odpytuje układ klawiatury poza głównym wątkiem. To bezpośrednio uderza w cel „zero crashy". Sprawdzamy to jako pierwszy punkt F5; crash złapie pomocnik z F2 i od razu powie koledze, co odesłać; gdy się potwierdzi, zamiana nasłuchu na Macu na Quartz event tap (pyobjc) w `voiceflow/platform/macos.py`.
- **Uprawnienia po aktualizacji:** przy podpisie ad-hoc macOS może traktować nową wersję jak nową aplikację i zdjąć zgodę na Dostępność. Łagodzimy instrukcją, sprawdzeniem uprawnień przy starcie (F3) i wpisem w katalogu błędów (F2).
- **Brak Maca u autora:** każdy błąd widoczny tylko na Macu wymaga rundy przez kolegę; dlatego „Kopiuj raport" i „Diagnostyka" z F2 (log w `~/Library/Application Support/VoiceFlow/`).

## Weryfikacja
- F1 i F3: agent `tester` + ręcznie `dist/windows/VoiceFlow.exe` (nagranie, wklejenie, autostart, aktualizacja), potem `reviewer`.
- F2: tester wymusza zły klucz (401), limit (429), brak sieci, wyjątek w wątku i twardy crash (`faulthandler._sigsegv()` w trybie testowym); za każdym razem ma się pojawić zrozumiała instrukcja, po crashu okno przy następnym starcie, w raporcie brak kluczy.
- F4: zielony workflow w GitHub Actions, zip w artefaktach, `codesign -dv` w logu.
- F5: checklista kolegi odhaczona w całości, plus jeden „Kopiuj raport" z Diagnostyki.
- F6: release z dwoma plikami, Windows 1.3.0 wykrywa nową wersję.
