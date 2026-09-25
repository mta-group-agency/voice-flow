# VoiceFlow

Desktopowe narzędzie STT na Windows (klon Wispr Flow): przytrzymujesz klawisz, mówisz, a tekst
(opcjonalnie poprawiony przez AI) wkleja się w miejscu kursora.

Wybierz swoją ścieżkę:

1. [Chcę tylko używać aplikacji](#używanie-aplikacji): pobierasz gotowy VoiceFlow.exe, bez Pythona i bez tego repo.
2. [Chcę zmieniać kod](#instalacja): Instalacja, potem [Uruchomienie z kodu](#uruchomienie-z-kodu).
3. [Chcę zbudować własny VoiceFlow.exe](#budowanie): najpierw Instalacja.

Dalej: [Co gdzie leży](#co-gdzie-leży), [macOS](#macos).

## Używanie aplikacji

### Pobranie i pierwszy start

1. Pobierz `VoiceFlow.exe` (ok. 150 MB) z https://github.com/mta-group-agency/voice-flow/releases/latest,
   sekcja Assets. Jeśli Edge napisze, że plik nie jest często pobierany: najedź na plik, kliknij
   `...` > Zachowaj, potem Pokaż więcej > Zachowaj mimo to.
2. Przenieś plik do stałego folderu, np. `C:\Users\<nazwa>\VoiceFlow`. Nie do Program Files (tam
   aktualizacja nie podmieni pliku). Później go nie przenoś: autostart zapamiętuje ścieżkę.
3. Uruchom dwuklikiem. Jeśli Windows pokaże "System Windows ochronił ten komputer", kliknij
   Więcej informacji > Uruchom mimo to.
4. Okno powitalne jest po polsku, zamknij je przyciskiem Zaczynam. Dalej interfejs jest po angielsku.
5. Klucz API: zakładka Settings > sekcja API Keys > pole Groq API Key. Wklej darmowy klucz z
   https://console.groq.com/keys, kliknij Test obok. Po udanym teście klucz zapisuje się sam
   (pokaże się "Connection successful! Key saved, you can dictate now."), Save Settings na dole
   nie jest do tego potrzebny. Sam klucz Groq wystarcza do wszystkiego.
6. Dyktowanie: kliknij tam, gdzie chcesz pisać, przytrzymaj prawy Alt, mów, puść. Tekst wklei się sam.

### Na co dzień

- ikona siedzi w zasobniku obok zegara (jeśli jej nie widać, kliknij strzałkę ^); dwuklik na niej otwiera okno,
- X w oknie tylko chowa je do zasobnika; wyłączenie aplikacji: prawy klik na ikonie > Quit,
- start razem z Windowsem: Settings > System > Start with Windows,
- aktualizacje: przy starcie aplikacja sama sprawdza, czy jest nowa wersja, i pokazuje okno "Nowa wersja";
  Aktualizuj teraz pobiera ją i uruchamia aplikację ponownie, ustawienia i klucze zostają,
- ustawienia, klucze API i log leżą w `%APPDATA%\VoiceFlow\` (`config.json`, `voiceflow.log`); żeby tam
  zajrzeć, wklej `%APPDATA%\VoiceFlow` w pasek adresu Eksploratora,
- usuwanie: najpierw wyłącz Start with Windows, potem Quit i usuń `VoiceFlow.exe`; opcjonalnie usuń też
  folder `%APPDATA%\VoiceFlow` (ustawienia, klucze, log, modele lokalnego Whispera).

### Jeśli aplikacja nie działa

- okno "VoiceFlow is already running": aplikacja już działa, szukaj ikony w zasobniku (strzałka ^),
- dymek "No API key configured": wklej klucz jak w kroku 5 i kliknij Save Settings,
- "Connection failed. Check your API key." po kliknięciu Test: klucz skopiował się niecały, skopiuj go jeszcze raz,
- dymek "Recording too short": trzymaj prawy Alt przez cały czas mówienia,
- nic się nie wkleja albo dymek "Could not transcribe audio": sprawdź mikrofon; w Ustawieniach Windows >
  Prywatność i zabezpieczenia > Mikrofon musi być włączony dostęp dla aplikacji klasycznych,
- tekst nie wkleja się w programie uruchomionym jako administrator: Windows na to nie pozwala, uruchom ten program normalnie,
- coś innego: otwórz `%APPDATA%\VoiceFlow\voiceflow.log`, najnowsze wpisy są na końcu (Ctrl+End). Log nie
  zawiera kluczy API, dyktowanego tekstu ani zawartości schowka (wpisy ze starszych wersji aplikacja czyści
  sama przy starcie), więc możesz wysłać autorowi cały plik.

## Instalacja

Potrzebna tylko do zmian w kodzie i do budowania.

**Folder repo** to folder, w którym widać plik `main.py`. Od kroku 3 wszystkie komendy wpisujesz
w PowerShellu otwartym w folderze repo. Najprościej: w Eksploratorze wejdź do tego folderu, kliknij
pasek adresu, wpisz `powershell` i Enter. Kroki 1 i 2 możesz robić w PowerShellu z menu Start
(wpisz PowerShell, Enter).

### 1. Python 3.11-3.13

Sprawdź wersję:
```
python --version
```

- wypisało 3.11, 3.12 albo 3.13: przejdź dalej, w kroku 3 użyj `python -m venv .venv`,
- wypisało inną wersję (np. 3.10 albo 3.14), "Python was not found", otworzył się Microsoft Store
  albo komenda jest nieznana: zainstaluj Python 3.13 z https://www.python.org/downloads/windows/
  (najnowszy 3.13.x, "Windows installer (64-bit)", Install Now z domyślnymi opcjami), zamknij
  i otwórz PowerShell na nowo, w kroku 3 użyj `py -3.13 -m venv .venv`.

Dlaczego nie 3.14: PyAudio (nagrywanie dźwięku) nie ma jeszcze gotowej paczki dla 3.14 na Windows.

### 2. Pobranie kodu

Z gitem:
```
git clone https://github.com/mta-group-agency/voice-flow
cd voice-flow
```

PowerShell z menu Start startuje w `C:\Users\<nazwa>`, więc folder repo to `C:\Users\<nazwa>\voice-flow`,
a w każdym nowym oknie wystarczy `cd voice-flow`. Jeśli `git` jest nieznany: zainstaluj go
z https://git-scm.com/download/win (domyślne opcje) i otwórz PowerShell na nowo.

Bez gita: na https://github.com/mta-group-agency/voice-flow kliknij Code > Download ZIP, potem prawy
klik na pobranym pliku > Wyodrębnij wszystkie. Windows często tworzy folder w folderze
(`voice-flow-main\voice-flow-main`): wchodź głębiej, aż zobaczysz `main.py`, i tam otwórz PowerShell
(pasek adresu, `powershell`, Enter).

Ścieżka folderu repo nie może być bardzo długa (bezpiecznie do ok. 100 znaków), inaczej krok 4 się
nie uda. Oba sposoby wyżej mieszczą się w tym z zapasem.

### 3. Środowisko (.venv)

W folderze repo, komendą z kroku 1:
```
python -m venv .venv
```
(albo `py -3.13 -m venv .venv`). Komenda nic nie wypisuje, a obok `main.py` pojawia się folder `.venv`.

Aktywować .venv nie trzeba: komendy w tym README wołają Pythona z `.venv` wprost (`.venv\Scripts\python ...`).

### 4. Zależności

W folderze repo:
```
.venv\Scripts\python -m pip install -r requirements/windows.txt
```

Pobiera ok. 200 MB i trwa kilka minut, na końcu ma być `Successfully installed ...`. Linie `[notice]`
o nowej wersji pip możesz zignorować.

Wolisz aktywować .venv i pisać krótko `pip` i `python`? `.venv\Scripts\Activate.ps1` (w cmd
`.venv\Scripts\activate.bat`). Przy błędzie "running scripts is disabled on this system" wpisz raz
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, potwierdź Y i Enter, i powtórz aktywację.

### Jeśli instalacja się nie udała

Folder `.venv` usuwasz jak każdy inny folder, np. w Eksploratorze.

- `The module '.venv' could not be loaded` (PowerShell), "System nie może odnaleźć określonej ścieżki"
  (cmd, po angielsku "The system cannot find the path specified") albo `ERROR: Could not open requirements file`:
  nie jesteś w folderze repo albo `.venv` powstało gdzie indziej; otwórz PowerShell w folderze repo (patrz
  początek Instalacji) i powtórz stamtąd krok 3 i 4, a `.venv` utworzone w innym folderze usuń,
- `py` jest nieznany albo `No suitable Python runtime found`: nie ma Pythona 3.13 z python.org, wróć do kroku 1,
- błąd wspominający PyAudio, "Microsoft Visual C++ 14.0" albo portaudio: `.venv` ma za nowego Pythona
  (np. 3.14); usuń folder `.venv` i wróć do kroku 1,
- `Could not find a version that satisfies the requirement ... (from versions: none)`: pip nie ma
  połączenia z internetem; sprawdź sieć, a w sieci firmowej z proxy dopisz do komendy `--proxy http://adres:port`,
- `Could not install packages due to an OSError` z dopiskiem o "Long Path support": ścieżka folderu repo
  jest za długa; przenieś folder repo w krótsze miejsce (np. `C:\Users\<nazwa>\voice-flow`), usuń w nim
  `.venv` i zrób kroki 3 i 4.

## Uruchomienie z kodu

Najpierw zamknij pobrany VoiceFlow.exe, jeśli działa (prawy klik na ikonie w zasobniku > Quit).
Potem w folderze repo:
```
.venv\Scripts\python main.py
```

- otworzy się okno VoiceFlow i ikona w zasobniku, dalej jak w [Pobranie i pierwszy start](#pobranie-i-pierwszy-start)
  od kroku 4; kod z repo i pobrany .exe mają wspólne ustawienia i klucze (`%APPDATA%\VoiceFlow\config.json`),
  więc jeśli używałeś już .exe, okno powitalne się nie pokaże, a klucz jest już wpisany,
- terminal zostaje zajęty i zwykle nic nie wypisuje, to normalne; zamknięcie okna terminala zamyka też aplikację,
- zatrzymanie: prawy klik na ikonie > Quit (terminal znów przyjmuje komendy); po zmianie kodu zatrzymaj i uruchom ponownie,
- błędy działającej aplikacji trafiają do `%APPDATA%\VoiceFlow\voiceflow.log`, a nie do terminala: to
  pierwsze miejsce, gdy coś nie działa (najnowsze wpisy są na końcu pliku); w terminalu zobaczysz tylko
  błędy, przez które aplikacja w ogóle nie wystartowała,
- Start with Windows działa tylko w zbudowanym .exe, przy uruchomieniu z kodu przełącznik jest wyszarzony,
- z aktywnym .venv (patrz krok 4) wystarczy `python main.py`.

### Jeśli uruchomienie z kodu się nie udało

- `No module named 'PyQt6'` (albo inny moduł): pominięty krok 4 albo uruchamiasz innym Pythonem niż ten
  z `.venv`; użyj dokładnie komendy wyżej, a jeśli błąd zostaje, zrób krok 4,
- `can't open file ... main.py` albo `The module '.venv' could not be loaded`: nie jesteś w folderze repo
  (albo nie ma w nim `.venv`, wtedy krok 3 i 4),
- okno "VoiceFlow is already running": działa już inna kopia, zwykle pobrany VoiceFlow.exe (także z autostartu);
  zamknij ją (prawy klik na ikonie > Quit) i uruchom ponownie, inaczej testujesz starą wersję, a nie swój kod,
- okno "Nowa wersja" zaraz po starcie: kod w folderze repo jest starszy niż najnowsze wydanie; kliknij Później
  i pobierz świeży kod (`git pull` albo nowy ZIP), bo Aktualizuj teraz pobrałby tylko gotowy VoiceFlow.exe
  przez przeglądarkę.

## Budowanie

Wymaga kroków 1-4 z [Instalacji](#instalacja). W PowerShellu w folderze repo:
```
powershell -ExecutionPolicy Bypass -File packaging/windows/build.ps1
```

- .venv nie trzeba aktywować: skrypt bierze Pythona z folderu `.venv` w repo, a gdy go nie ma, `python`
  z PATH; na starcie wypisuje linię `Python: ...`, żebyś wiedział, którego użył,
- trwa kilka minut; sukces to zielone `OK: build zakończony powodzeniem.`, gotowy plik to `dist\windows\VoiceFlow.exe`,
- test buildu: zamknij działający VoiceFlow (Quit), uruchom `dist\windows\VoiceFlow.exe`, a po teście zamknij
  go i uruchom z powrotem swój zwykły VoiceFlow.exe; build ma te same ustawienia i klucze. Start with Windows
  włączaj tylko w tej kopii, którą autostart ma uruchamiać.

### Jeśli build się nie udał

- "The argument 'packaging/windows/build.ps1' to the -File parameter does not exist": nie jesteś
  w folderze repo; otwórz PowerShell w folderze repo (patrz początek Instalacji) i uruchom build ponownie,
- "w tym Pythonie brakuje modułów": skrypt podaje, których i w którym Pythonie; zrób kroki 3 i 4 z Instalacji i uruchom build ponownie,
- "nie udało się uruchomić Pythona" albo "nie znaleziono Pythona": skrypt nie ma działającego Pythona
  (brak `.venv` w repo, a `python` z PATH nie działa); zrób kroki 1-4 z Instalacji,
- "VoiceFlow z dist\windows jest uruchomiony": zamknij go (prawy klik na ikonie w zasobniku > Quit) i uruchom build ponownie,
- żółta uwaga o autostarcie: build i tak się udał; żeby autostart ruszał nową wersję: 1) zamknij działający
  VoiceFlow (prawy klik na ikonie w zasobniku > Quit), 2) uruchom `dist\windows\VoiceFlow.exe`, 3) w Settings
  wyłącz i włącz Start with Windows,
- żółta uwaga "działa inna kopia VoiceFlow": build i tak się udał, ale nie wystartuje, dopóki tej kopii nie
  zamkniesz (prawy klik na ikonie w zasobniku > Quit),
- żółta uwaga o starym `dist\VoiceFlow.exe`: build i tak się udał, to tylko przypomnienie o starym pliku,
  usuń go dopiero, gdy autostart nie wskazuje już na niego,
- inny błąd (czerwone "build zakończył się kodem ..."): przewiń w górę do pierwszej linii z ERROR albo
  Traceback; jeśli nic Ci nie mówi, skopiuj ostatnie ok. 30 linii tego okna i wyślij autorowi.

## Co gdzie leży

| Katalog | Zawartość |
|---|---|
| `voiceflow/` | wspólny kod aplikacji (GUI, pipeline, API, storage) |
| `assets/common/` | ikony wspólne dla wszystkich systemów |
| `assets/windows/` | ikony specyficzne dla Windows (`icon.ico`) |
| `assets/macos/` | ikony specyficzne dla macOS (`icon.icns` generowana przy buildzie) |
| `packaging/windows/` | konfiguracja PyInstaller i skrypt buildu dla Windows |
| `packaging/macos/` | konfiguracja buildu dla macOS, build leci w GitHub Actions (jeszcze nieprzetestowany na prawdziwym Macu) |
| `requirements/` | zależności Pythona (base + per-system) |
| `TODO/` | plany, w tym plan portu na Maca (`plan-mac.md`) |
| `dist/windows/`, `build/windows/` | wynik i pliki robocze buildu, poza gitem |
| `generate_icons.py` | generuje ikony png do `assets/common`; w folderze repo: `.venv\Scripts\python generate_icons.py` |
| `voiceflow_mockup.html` | statyczny mockup HTML interfejsu aplikacji |

### Dodajesz coś tylko dla jednego systemu?

- ikony -> `assets/<system>/`
- konfiguracja buildu -> `packaging/<system>/` (docelowe pliki dla Maca opisane w `packaging/macos/README.md`)
- build w chmurze (GitHub Actions) -> `.github/workflows/`, jedyny wyjątek od `packaging/<system>/`
  (GitHub szuka workflowów tylko tam)
- zależność Pythona -> `requirements/<system>.txt` (wspólna dla obu: `requirements/base.txt`)
- różnice w kodzie -> `voiceflow/platform/` (`windows.py` albo `macos.py`; reszta kodu importuje tylko z `voiceflow.platform`)

Nie kopiuj `voiceflow/`, kod aplikacji jest wspólny dla wszystkich systemów.

## macOS

Wersji na Maca jeszcze nie ma do pobrania. Kod ma już część dla Maca (`voiceflow/platform/macos.py`),
build leci w GitHub Actions (`packaging/macos/`, `.github/workflows/build-macos.yml`), ale nikt
jeszcze nie uruchomił ani kodu, ani builda na prawdziwym Macu, więc `python main.py` na Macu i
gotowy `.app` z CI to na razie eksperyment.

Stan: F1 (układ folderów), F3 (kod pod Maca) i F4 (build w GitHub Actions) zrobione, oba
nieprzetestowane na prawdziwym Macu (F4: build w GitHub Actions działa i sprawdza uruchomienie
aplikacji, paczka około 90 MB). F2 (pomocnik błędów) porzucone. Dalej: test u kolegi z Makiem (F5),
potem release (F6).
Szczegóły: `TODO/plan-mac.md`, a build Maca: `packaging/macos/README.md`.
