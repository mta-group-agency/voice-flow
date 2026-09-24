# packaging/macos

Konfiguracja buildu VoiceFlow na macOS. Na razie tylko plan: pliki poniżej powstaną w fazie F4,
opisanej w `TODO/plan-mac.md`, sekcja "F4. Build na Maca w chmurze".

Zanim zaczniesz:

- build Maca da się zrobić tylko na Macu albo w GitHub Actions (runner `macos-latest`). Na Windowsie
  nie: PyInstaller buduje tylko dla systemu, na którym działa, więc `VoiceFlow.app` nie powstanie z Windowsa,
- F4 ma sens po F3 (kod pod Maca, ten sam plik planu): bez F3 `VoiceFlow.app` się zbuduje, ale wywali się
  na starcie, bo kod ma jeszcze wpięte rozwiązania tylko dla Windowsa.

Docelowo w tym katalogu:

- `voiceflow.spec`: konfiguracja PyInstaller z sekcją `BUNDLE`, pakująca aplikację jako `VoiceFlow.app`
  (zamiast pojedynczego pliku `.exe` jak na Windows). Punkt wyjścia: `packaging/windows/voiceflow.spec`.
  Różnice: ukryte importy `pynput.keyboard._darwin` i `pynput.mouse._darwin` zamiast `_win32`, ikona
  `assets/macos/icon.icns`, a w `Info.plist` wpisy `NSMicrophoneUsageDescription` (tekst prośby
  o mikrofon, bez niego macOS nie pozwoli nagrywać) i `LSUIElement` = true (tylko ikona w pasku menu, bez Docka).
- `entitlements.plist`: uprawnienia aplikacji (mikrofon, dostępność/monitorowanie klawiatury)
  wymagane przez macOS.
- `build.sh`: skrypt buildu: `brew install portaudio`, `pip install -r requirements/macos.txt`, `pyinstaller`,
  podpis ad-hoc (`codesign --force --deep -s -`), spakowanie do zipa przez `ditto`.

Poza tym katalogiem:

- `.github/workflows/build-macos.yml`: build w GitHub Actions. Musi leżeć w `.github/workflows/`, bo GitHub
  szuka workflowów tylko tam (jedyny wyjątek od zasady "build dla systemu w `packaging/<system>/`").
  Po tagu `v*` uruchamia `packaging/macos/build.sh` i dokleja `VoiceFlow-macos-arm64.zip` do release'u.
- `requirements/macos.txt`: zależności Pythona na Macu (PyAudio wymaga wcześniej `brew install portaudio`).
- `assets/macos/`: ikony Maca, opis w `assets/macos/README.md`.

Wynik buildu ląduje w `dist/macos/` (`VoiceFlow.app` i `VoiceFlow-macos-arm64.zip`). F4 jest skończone,
gdy workflow w GitHub Actions jest zielony, zip jest w artefaktach, a w logu widać wynik `codesign -dv`.
