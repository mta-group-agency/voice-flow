# packaging/macos

Konfiguracja buildu VoiceFlow na macOS. Stan (2026-09-25, zgodny z `TODO/plan-mac.md`): F1, F3
i F4 zrobione, F2 porzucone. F4 (ten katalog) zrobione, ale jeszcze nieprzetestowane: build leci
w GitHub Actions na tagu `v*`, na branchu `mac-port` (do testów) albo ręcznie, tylko pierwszy
przebieg CI jeszcze się nie odbył. Dalej: F5 (test u kolegi z Makiem), potem F6 (release).

Zanim zaczniesz:

- build Maca da się zrobić tylko na Macu albo w GitHub Actions (runner `macos-14`, arm64). Na Windowsie
  nie: PyInstaller buduje tylko dla systemu, na którym działa, więc `VoiceFlow.app` nie powstanie z Windowsa,
- F4 ma sens po F3 (kod pod Maca, ten sam plik planu): bez F3 `VoiceFlow.app` się zbuduje, ale wywali się
  na starcie, bo kod ma jeszcze wpięte rozwiązania tylko dla Windowsa.

## Pliki w tym katalogu

- `voiceflow.spec`: konfiguracja PyInstaller (onedir + `BUNDLE` -> `VoiceFlow.app`). Punkt wyjścia:
  `packaging/windows/voiceflow.spec`. Różnice: ukryte importy `pynput.keyboard._darwin` /
  `pynput.mouse._darwin` (zamiast `_win32`) plus moduły pyobjc (`Quartz`, `AppKit`,
  `ApplicationServices`) zebrane przez `collect_submodules`, ikona `assets/macos/icon.icns`
  (jeśli jej brak, spec buduje bez ikony zamiast się wywalić), `excludes` bez `xml` (bo
  `voiceflow/platform/macos.py` używa `plistlib`, a ten potrzebuje `xml.parsers.expat`),
  `Info.plist` z `CFBundleIdentifier` = `com.mta.voiceflow`, wersją czytaną z
  `voiceflow/__version__.py`, `LSUIElement` = true (tylko ikona w pasku menu, bez Docka) i
  `NSMicrophoneUsageDescription`.
- `entitlements.plist`: jedno uprawnienie, `com.apple.security.device.audio-input` (mikrofon).
  Minimalne celowo; nie ma hardened runtime (podpis jest ad-hoc, nie od Apple Developer).
- `build.sh`: generuje `assets/macos/icon.icns` (jeśli go nie ma) z `assets/common/icon.png`
  przez `sips` + `iconutil` (źródło ma 64px, powiększenie do 1024px jest akceptowalne), buduje
  `.app` przez PyInstaller, podpisuje ad-hoc (`codesign --force --deep --sign -`), weryfikuje
  (`codesign -dv`), pakuje do zipa przez `ditto`. Działa tylko na macOS, z dowolnego katalogu
  roboczego. Zakłada, że zależności Pythona są już zainstalowane (patrz niżej).

Poza tym katalogiem:

- `.github/workflows/build-macos.yml`: build w GitHub Actions (musi leżeć w `.github/workflows/`,
  jedyny wyjątek od zasady "build dla systemu w `packaging/<system>/`"). Instaluje `portaudio`
  przez brew, `requirements/macos.txt`, odpala `build.sh`, robi smoke test
  (import modułów `voiceflow` z `QT_QPA_PLATFORM=offscreen`, sprawdzenie że binarka jest arm64),
  wrzuca zip jako artefakt (14 dni) zawsze, a na tagu `v*` dokleja go do release'u tego taga
  (czeka do ~10 minut, aż release się pojawi, bo `/release` na Windowsie tworzy go ręcznie i
  może to zrobić już po wypchnięciu taga; jeśli po tym czasie release nadal nie istnieje, tworzy
  szkic).
- `requirements/macos.txt`: zależności Pythona na Macu (PyAudio wymaga wcześniej `brew install portaudio`;
  zawiera też `pyobjc-framework-Quartz` i `pyobjc-framework-ApplicationServices`, potrzebne przez
  darwinowy backend `pynput`).

## Dla właściciela: jak odpalić build i wysłać go koledze (Windows, bez programowania)

### 1. Wypchnij branch testowy

W folderze repo, w PowerShellu albo terminalu, najpierw sprawdź `git status`, żeby się upewnić,
że nie wisi tam nic niespodziewanego (np. pliki z `TEMP/` albo `dist/`). Potem:

```
git switch -c mac-port
git add -A
git commit -m "port na Maca: test builda"
git push -u origin mac-port
```

Jeśli branch `mac-port` już istnieje (np. z poprzedniego razu), zamiast pierwszej komendy użyj:

```
git switch mac-port
```

Kolejne zmiany na ten sam branch to już tylko:

```
git add -A
git commit -m "..."
git push
```

Każde wypchnięcie na `mac-port` samo odpala build w GitHub Actions.

Przycisk "Run workflow" (ręczne odpalenie bez pushowania) pojawia się w Actions dopiero, gdy plik
workflow (`.github/workflows/build-macos.yml`) jest na branchu `main`. Dopóki zmiana nie jest
zmergowana, jedyny sposób na odpalenie builda to push na `mac-port` jak wyżej.

### 2. Obejrzyj build

GitHub > zakładka Actions > "Build macOS" > najnowszy przebieg na `mac-port`. Zielony haczyk = build
się udał.

### 3. Pobierz wynik i wyślij koledze

1. W tym przebiegu, sekcja Artifacts > pobierz `VoiceFlow-macos-arm64` (to jest zip zawierający
   w środku plik `VoiceFlow-macos-arm64.zip`).
2. Na Windowsie kliknij na pobrany plik prawym > "Wyodrębnij wszystkie" **dokładnie raz**. W
   wyodrębnionym folderze znajdziesz `VoiceFlow-macos-arm64.zip`, to jest właściwa paczka dla Maca.
3. Wyślij koledze ten wewnętrzny plik `VoiceFlow-macos-arm64.zip` **bez zmian** (Slack, Dysk, mail:
   cokolwiek, byle nie przez GitHuba, bo kolega bez dostępu do repo i tak nie ściągnie artefaktu z
   Actions).

**Nie rozpakowuj tego wewnętrznego zipa na Windowsie i nie pakuj go ponownie.** Windows przy
rozpakowaniu i ponownym spakowaniu gubi uprawnienia wykonywalne pliku i linki symboliczne w środku
`.app`, aplikacja u kolegi wtedy się nie otworzy. Wystarczy to jedno "Wyodrębnij wszystkie" z kroku
2, żeby wyjąć wewnętrzny zip z zewnętrznego opakowania Actions; sam wewnętrzny zip zostaje
nietknięty.

Gotowa treść wiadomości dla kolegi (co zrobić po stronie Maca): `packaging/macos/WIADOMOSC-DLA-TESTERA.md`.

## Instalacja u kolegi z Makiem

1. Pobierz `VoiceFlow-macos-arm64.zip` (z Artifacts albo z release'u), rozpakuj (Safari robi to
   automatycznie), przeciągnij `VoiceFlow.app` do Applications.
2. Pierwsze uruchomienie (podpis jest ad-hoc, nie od Apple Developer, więc Gatekeeper blokuje):
   - macOS 15 (Sequoia) i nowsze: spróbuj otworzyć, macOS zablokuje; potem Ustawienia systemowe >
     Prywatność i ochrona > przy komunikacie o VoiceFlow kliknij "Otwórz mimo to".
   - macOS 14 i starsze: kliknij prawym na `VoiceFlow.app` > Otwórz > potwierdź w oknie.
3. Po starcie nadaj uprawnienia (System Settings > Privacy & Security): Microphone (nagrywanie),
   Accessibility i Input Monitoring (obsługa hotkeya i wklejanie tekstu). Po nadaniu zamknij
   VoiceFlow z paska menu i uruchom ponownie.

Wynik buildu ląduje w `dist/macos/` (`VoiceFlow.app` i `VoiceFlow-macos-arm64.zip`). F4 jest skończone,
gdy workflow w GitHub Actions jest zielony, zip jest w artefaktach, a w logu widać wynik `codesign -dv`.
