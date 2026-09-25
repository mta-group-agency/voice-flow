# Plan: VoiceFlow na Maca (release na GitHubie) + rozdzielenie Windows / Mac w repo

Stan (2026-09-25): F1 (układ folderów) zrobione. F2 (pomocnik błędów) porzucone i przeniesione
do backlogu. F3 (kod pod Maca) zrobione w kodzie, sprawdzone tylko na Windowsie (na Macu jeszcze
nie uruchomione). F4 (build Maca w GitHub Actions) zrobione: build w GitHub Actions działa
i sprawdza uruchomienie aplikacji, arm64, podpis ad-hoc, zip około 90 MB. Dalej: F5 (test
u kolegi z Makiem), potem F6 (release). Szczegóły niżej, w sekcji Fazy wdrożenia.

Kroki oznaczone Agent / tester / reviewer dotyczą pracy z Claude Code; człowiek może je wykonać ręcznie.

## Kontekst

Dziś VoiceFlow działa tylko na Windowsie. CLAUDE.md wpisywał macOS jako poza scope; po F1 scope
obejmuje port na Maca. Chcemy wypuszczać w tym samym repo (`mta-group-agency/voice-flow`) drugą
paczkę dla kolegów z Makami. Ustalone z Mateuszem:
- build na Maca robi darmowy runner GitHub Actions (`macos-14`), testuje kolega z Makiem,
- bez konta Apple Developer (0 zł): podpis ad-hoc + instrukcja odblokowania w Gatekeeperze
  (macOS 14 i starsze: prawy klik > Otwórz; macOS 15 Sequoia i nowsze: Ustawienia systemowe >
  Prywatność i ochrona > „Otwórz mimo to" po pierwszym zablokowanym uruchomieniu),
- na Macu na start tylko baner „jest nowa wersja, pobierz", autoaktualizacja później.

Audyt kodu pokazał, że nie ma ani jednego `sys.platform`; Windows jest wpięty na sztywno w ~12 miejscach.

## Co blokuje Maca dziś (z audytu)

Po F3 wszystkie wiersze poza Build i Release są obsłużone w kodzie (przez `voiceflow/platform/`),
ale nie były jeszcze uruchomione na prawdziwym Macu. Build i Release to F4 i F6.

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
│       └── macos.py               # flock, LaunchAgent, open, ~/Library/Application Support
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
**PORZUCONE 2026-09-25, przeniesione do backlogu.** Port na Maca idzie dalej bez tej fazy (F3 nie
zależy od F2). Rozpoczęta praca leży w `git stash` pod nazwą „F2 M1 how-to-fix (porzucone 2026-09-25)".
Poprawka klucza Gemini w logu weszła osobno (commit c56fbf8). Opis niżej zostaje jako materiał na później.

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
**Stan 2026-09-25: zrobione w kodzie, nieprzetestowane na Macu.** Na Windowsie sprawdzone: te same
ścieżki danych, ten sam wpis autostartu w rejestrze, te same teksty w oknie, ten sam wynik testu
przepływu dyktowania, `.exe` się buduje. Gałęzie Maca sprawdzone tylko symulacją na Windowsie
(podmieniony `sys.platform`), więc prawdziwy test to dopiero F5. Co powstało:
- `voiceflow/platform/__init__.py` wybiera `windows.py` albo `macos.py`; reszta aplikacji importuje tylko stamtąd,
- Mac: dane w `~/Library/Application Support/VoiceFlow/`, jedna instancja przez `flock` na pliku
  `voiceflow.lock`, autostart jako LaunchAgent `~/Library/LaunchAgents/com.mta.voiceflow.plist`
  (odmawia, gdy aplikacja działa z Pobranych w trybie App Translocation), wklejanie Cmd+V z 50 ms
  przerwy po ustawieniu schowka, bez cienia okna,
- Mac: przy starcie sprawdzenie zgody Dostępność (`AXIsProcessTrusted` przez ctypes, bez pyobjc) i
  Monitorowania wprowadzania (`IOHIDCheckAccess`); bez zgody na Dostępność najpierw systemowy
  prompt (`AXIsProcessTrustedWithOptions`, dodaje VoiceFlow do listy w Ustawieniach), potem, jeśli
  dalej brakuje którejś zgody, własne okno z instrukcją i przyciskiem do właściwego panelu,
- overlay nie bierze fokusu (też na Windowsie) i na Macu nie znika, gdy VoiceFlow nie jest aktywny,
- poprawka po pierwszym teście na Macu (2026-09-25): przy trzymaniu prawego Option macOS przełączał
  na okno VoiceFlow, więc Cmd+V trafiłby do VoiceFlow, a nie do pisanej aplikacji. Przyczyna:
  `raise_()` overlayu, które w Qt na Macu aktywuje całą aplikację (`QCocoaWindow::raise` woła
  `activateIgnoringOtherApps:`, sprawdzone w `libqcocoa.dylib` z builda CI, Qt 6.11.2). Naprawa:
  `QT_MAC_SET_RAISE_PROCESS=0` ustawiane przed startem Qt, overlay na Macu bez `raise_()`, a dla
  pewności VoiceFlow zapamiętuje aplikację z przodu na starcie nagrania i tuż przed Cmd+V przywraca
  ją na przód, jeśli z przodu stoi VoiceFlow (czeka do 150 ms). „Open VoiceFlow" z paska menu
  aktywuje aplikację jawnie, bo bez tego okno otwierałoby się bez fokusu. Windows bez zmian,
- tray: na Macu klik na ikonie otwiera menu paska menu (jak w macOS, bez dwukliku), z niego
  "Open VoiceFlow" otwiera okno; etykiety klawiszy (Right Option, Cmd, Control), podpowiedzi w
  Ustawieniach, powitanie („Prawy Option") i czcionki (Helvetica Neue, Menlo) zależne od systemu,
- teksty o GPU NVIDIA tylko na Windowsie; na Macu autostart nazywa się „Start at login",
- updater: na Macu asset `VoiceFlow-macos-arm64.zip`, bez samoaktualizacji, baner mówi „rozpakuj
  i przenieś do Applications".

Plan pierwotny:
- `voiceflow/platform/`: ścieżka danych, jedna instancja, autostart, otwarcie folderu, cień okna, klawisz wklejania,
- podpiąć w `main.py`, `autostart.py`, `settings_manager.py`, `logger.py`, `local_whisper_client.py`, `settings_tab.py`, `main_window.py`, `text_injector.py`,
- overlay: dodać flagi bez fokusu (pomaga też Windowsowi),
- tray: pojedyncze kliknięcie na Macu, etykiety klawiszy i czcionki zależne od systemu,
- tekst „zalecane GPU NVIDIA" pokazywać tylko na Windowsie,
- updater: nazwa assetu zależna od systemu (`VoiceFlow.exe` zostaje bez zmian, stare instalacje dalej się aktualizują); na Macu `can_self_update()` = False, więc zostaje baner z linkiem do pobrania,
- Mac: przy starcie sprawdzić uprawnienia Dostępności / Monitorowania wejścia i pokazać okno z instrukcją, zamiast cicho nie reagować na klawisz.
- Wykonanie: Agent sonnet (moduł po module), tester po każdym.

### F4. Build na Maca w chmurze
**Stan 2026-09-25: zrobione, build w GitHub Actions działa i sprawdza uruchomienie aplikacji
(krok "Launch test"), arm64, podpis ad-hoc, zip około 90 MB.**
Zaczynać po F3: bez niej `VoiceFlow.app` się zbuduje, ale wywali się na starcie. Budować da się tylko
na Macu albo w GitHub Actions (PyInstaller nie robi `.app` na Windowsie). Docelowe pliki opisuje też
`packaging/macos/README.md`.
- `packaging/macos/voiceflow.spec` (punkt wyjścia: `packaging/windows/voiceflow.spec`): ukryte importy
  `pynput.keyboard._darwin` i `pynput.mouse._darwin`, `BUNDLE` z `Info.plist`
  (`NSMicrophoneUsageDescription`, `LSUIElement` = tylko ikona w pasku menu, bez Docka), `.icns`,
- z F3 dla speca Maca: `CFBundleIdentifier` = `com.mta.voiceflow` (ta sama nazwa co LaunchAgent);
  z listy `excludes` usunąć `xml`, bo `plistlib` w `voiceflow/platform/macos.py` potrzebuje
  `xml.parsers.expat` (inaczej aplikacja wywali się na starcie); `datas` jak na Windowsie
  z `assets/common` (ikona okna i paska menu),
- `build.sh`: generuje ikonę, uruchamia PyInstaller, podpis ad-hoc (`codesign --force --deep -s -`), zip via `ditto`,
- workflow `.github/workflows/build-macos.yml` (GitHub szuka workflowów tylko w `.github/workflows/`, jedyny wyjątek od `packaging/<system>/`): instaluje zależności (`brew install portaudio`, `pip install -r requirements/macos.txt`), następnie buduje; krok "Launch test" odpala zbudowaną `.app` na runnerze (offscreen, świeży `$HOME`), czeka około 20 s i sprawdza, czy proces nadal działa (pierwszy start blokuje się na oknie powitalnym / prośbie o uprawnienia), zawsze drukuje `voiceflow.log`; uruchamiany na push tagu `v*`, push do gałęzi `mac-port` oraz ręczny `workflow_dispatch`; dokleja `VoiceFlow-macos-arm64.zip` do release'u tylko dla tagów `v*`; wymaga `permissions: contents: write`,
- `generate_icons.py`: dodatkowo `.icns` i ikony paska menu (do `assets/macos/`, opis w `assets/macos/README.md`).
- Wykonanie: Agent sonnet, błędy builda: `build-error-resolver`.

### F5. Test na żywym Macu (kolega)
**Stan 2026-09-25: pierwszy test wykrył przełączanie na okno VoiceFlow przy nagrywaniu (opis
i poprawka w F3), poprawione w kodzie, czeka na nowy build i ponowny test punktu 3.**
Checklista do przekazania (bez tego nie wydajemy):
1. pobranie zipa, odblokowanie w Gatekeeperze (macOS 14 i starsze: prawy klik > Otwórz;
   macOS 15 i nowsze: Ustawienia systemowe > Prywatność i ochrona > „Otwórz mimo to"),
   aplikacja startuje, ikona w pasku menu,
2. prośba o mikrofon i uprawnienia klawiatury, po nadaniu prawy Option nagrywa,
3. tekst wkleja się w Notatkach, Slacku, przeglądarce (Cmd+V, fokus zostaje; trzymanie prawego
   Option nie przełącza na okno VoiceFlow),
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
- **pynput na nowszych macOS:** znane zgłoszenia crashy, gdy nasłuch klawiatury odpytuje układ klawiatury poza głównym wątkiem. To bezpośrednio uderza w cel „zero crashy". Sprawdzamy to jako pierwszy punkt F5; bez pomocnika z F2 (porzucone) kolega odsyła log z `~/Library/Application Support/VoiceFlow/voiceflow.log`; gdy się potwierdzi, zamiana nasłuchu na Macu na Quartz event tap (pyobjc) w `voiceflow/platform/macos.py`.
- **Uprawnienia po aktualizacji:** przy podpisie ad-hoc macOS może traktować nową wersję jak nową aplikację i zdjąć zgodę na Dostępność. Łagodzimy instrukcją, sprawdzeniem uprawnień przy starcie (F3, jest w kodzie).
- **Brak Maca u autora:** każdy błąd widoczny tylko na Macu wymaga rundy przez kolegę; „Kopiuj raport" i „Diagnostyka" z F2 odpadły razem z F2, więc kolega odsyła plik logu z `~/Library/Application Support/VoiceFlow/`.

## Weryfikacja
- F1 i F3: agent `tester` + ręcznie `dist/windows/VoiceFlow.exe` (nagranie, wklejenie, autostart, aktualizacja), potem `reviewer`.
- F2 (porzucone, dotyczy powrotu z backlogu): tester wymusza zły klucz (401), limit (429), brak sieci, wyjątek w wątku i twardy crash (`faulthandler._sigsegv()` w trybie testowym); za każdym razem ma się pojawić zrozumiała instrukcja, po crashu okno przy następnym starcie, w raporcie brak kluczy.
- F4: zielony workflow w GitHub Actions, zip w artefaktach, `codesign -dv` w logu.
- F5: checklista kolegi odhaczona w całości, plus plik `voiceflow.log` z jego Maca.
- F6: release z dwoma plikami, Windows 1.3.0 wykrywa nową wersję.
