# VoiceFlow na Maca, test u Ciebie

Dzięki, że pomagasz przetestować VoiceFlow na Macu. To wersja robocza, jeszcze nikt jej nie
uruchamiał na prawdziwym Macu, więc może coś nie zadziałać, o to właśnie chodzi w teście.

## 1. Instalacja

1. Rozpakuj pobrany plik `VoiceFlow-macos-arm64.zip` (dwuklik w Finderze).
2. Przeciągnij `VoiceFlow.app` do folderu Aplikacje.
3. Uruchom go z Aplikacji (dwuklik).
4. macOS pewnie zablokuje uruchomienie, bo aplikacja nie jest podpisana przez Apple. To normalne,
   robimy to bez płatnego konta deweloperskiego. Zależnie od wersji systemu:
   - **macOS 15 (Sequoia) i nowsze:** pojawi się okno blokady, kliknij w nim **"Gotowe"** (nie
     "Przenieś do kosza"). Potem wejdź w Ustawienia systemowe > Prywatność i ochrona, zjedź na
     sam dół do sekcji Bezpieczeństwo i kliknij **"Otwórz mimo to"**. Wpisz hasło do Maca. Może
     pojawić się jeszcze raz pytanie "Otwórz mimo to", potwierdź.
   - **macOS 14 i starsze:** kliknij prawym przyciskiem na `VoiceFlow.app` > Otwórz, potwierdź w
     oknie, które się pokaże.
5. Przy pierwszym uruchomieniu pokaże się okno powitalne po polsku. Zamknij je przyciskiem
   **"Zaczynam"**.

## 2. Uprawnienia

Po pierwszym uruchomieniu macOS zapyta o kilka uprawnień, zgódź się na wszystkie:

- **Dostępność** (Accessibility), potrzebne, żeby klawisz skrótu i wklejanie tekstu działały.
- Włącz też ręcznie **Monitorowanie wprowadzania** (Input Monitoring) w tym samym miejscu w
  Ustawieniach systemowych > Prywatność i ochrona, jeśli VoiceFlow samo nie poprosi.
- **Mikrofon**, o to VoiceFlow zapyta dopiero, gdy pierwszy raz przytrzymasz prawy Option. Kliknij
  Pozwól i spróbuj nagrać jeszcze raz (pierwsza próba się nie liczy, bo dopiero wtedy system pyta
  o zgodę).

Po włączeniu Dostępności i Monitorowania wprowadzania zamknij VoiceFlow (ikona w pasku menu >
"Quit") i otwórz go ponownie z Aplikacji. Bez tego klawisz skrótu może jeszcze nie zadziałać, mimo
że uprawnienia są już włączone.

## 3. Gdzie jest ikona i jak sterować oknem

VoiceFlow siedzi w pasku menu na górze ekranu, po prawej stronie. Nie ma ikony w Docku. Jeśli
masz Maca z notchem (wcięciem na górze ekranu) i ikon jest dużo, może się pod notch schować,
sprawdź czy się tam nie ukrywa.

Kliknij ikonę VoiceFlow w pasku menu i wybierz **"Open VoiceFlow"**, żeby otworzyć okno aplikacji.
Zamknięcie okna nie kończy działania VoiceFlow, aplikacja dalej działa w tle, w pasku menu. Żeby
całkiem zamknąć VoiceFlow: ikona w pasku menu > **"Quit"**.

## 4. Klucz do Groq (do transkrypcji mowy)

1. Wejdź na console.groq.com/keys, załóż konto/zaloguj się, utwórz klucz API.
2. W VoiceFlow: Settings > API Keys > Groq API Key, wklej klucz, kliknij Save Settings.

## 5. Co sprawdzić

Przejdź po kolei, przy każdym punkcie zapamiętaj (albo zrób zrzut ekranu), czy zadziałało tak jak
opisane:

1. Zip się rozpakował, aplikacja wystartowała, ikona jest w pasku menu.
2. Po nadaniu uprawnień przytrzymanie prawego Option zaczyna nagrywanie.
3. Podyktowany tekst wkleja się poprawnie w Notatkach, w Slacku i w przeglądarce (Cmd+V), a okno,
   w którym piszesz, zostaje na pierwszym planie (fokus się nie przełącza).
4. Esc w trakcie nagrywania anuluje dyktowanie. Overlay (mały wskaźnik nagrywania) jest widoczny
   nawet nad aplikacją w trybie pełnoekranowym.
5. Drugie uruchomienie VoiceFlow nie otwiera drugiej kopii aplikacji. Jeśli włączysz Start at
   login w Ustawieniach, VoiceFlow wystartuje samo po ponownym zalogowaniu.
6. W Ustawieniach spróbuj przełączyć rozpoznawanie mowy na lokalny model Whisper (działa bez
   klucza API, offline) i sprawdź, czy model się pobiera i czy transkrypcja działa.
7. Jeśli pojawi się baner o nowej wersji, sprawdź, czy kliknięcie w niego otwiera stronę do
   pobrania.
8. **W Notatkach wpisz polskie znaki ą, ę albo ł przez prawy Option** (tak jak na Windowsie
   AltGr). VoiceFlow nasłuchuje prawego Optiona w tle cały czas, niezależnie od tego, w jakiej
   aplikacji akurat piszesz, więc samo przytrzymanie tego klawisza (nawet do wpisania polskiej
   litery, a nie do dyktowania) może uruchomić nagrywanie. Sprawdź, czy przy wpisywaniu ą/ę/ł
   pojawia się overlay nagrywania i czy VoiceFlow rzeczywiście zaczyna nagrywać, mimo że nie o to
   Ci chodziło.

Nie musisz naprawiać żadnego problemu, po prostu zapisz, co się nie zgadza.

## 6. Jak odesłać wyniki

1. **Wersja macOS:** menu Apple (logo jabłka w lewym górnym rogu) > "Ten Mac" (About This Mac),
   zrzut ekranu tego okna wystarczy.
2. **Zrzut ekranu każdej wiadomości**, którą pokaże VoiceFlow (okna z uprawnieniami, błędy,
   cokolwiek niestandardowego).
3. **Log aplikacji:** w Finderze wejdź w menu Idź > Idź do folderu (albo skrót Cmd+Shift+G),
   wklej:
   ```
   ~/Library/Application Support/VoiceFlow
   ```
   i wyślij plik `voiceflow.log` z tego folderu. W środku nie ma kluczy API ani tego, co
   podyktowałeś, więc możesz go spokojnie wysłać.

Dzięki za pomoc.
