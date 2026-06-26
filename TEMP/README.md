# TEMP/ — strefa robocza (człowiek ↔ Claude)

Tu lądują pliki **niezwiązane z core'em projektu**. Dwa źródła:

1. **Wrzucane przez Ciebie** — materiały źródłowe, briefe, transkrypcje, screenshoty, notatki, eksporty, dane wejściowe. Zwłaszcza na **starcie projektu**: zanim odpalisz `/initiate`, wrzuć tutaj wszystko, co opisuje co chcesz osiągnąć — `/initiate` przeczyta ten folder jako bazę wiedzy.
2. **Generowane przez Claude** — drafty, robocze wersje, eksporty, pliki pomocnicze, które nie są częścią właściwego projektu.

## Czym to NIE jest
- **Nie jest core'em projektu.** Nic, co tu leży, nie powinno być potrzebne do działania projektu. Gdy plik staje się częścią projektu — przenieś go do właściwego katalogu (np. `src/` dla kodu, `docs/`/`dokumentacja/` dla dokumentów, `dane/` dla zbiorów danych — wg struktury z `CLAUDE.md`).
- **Nie jest systemowym scratchpadem.** Scratchpad Claude Code to czysty śmietnik na ulotne pliki sesji. `TEMP/` jest **wspólną, widoczną strefą** wewnątrz repo — przeżywa sesję, Ty i Claude oboje tu zaglądacie.

## Git
Zawartość `TEMP/` jest **ignorowana** (`.gitignore` w tym folderze) — śmietnik nie wchodzi do repo. Śledzone są tylko `README.md` i `.gitignore`. Jeśli jakiś materiał źródłowy chcesz wersjonować — przenieś go poza `TEMP/`, do właściwego katalogu projektu (zgodnie ze strukturą repo w `CLAUDE.md`).
