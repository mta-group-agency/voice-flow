# VoiceFlow na Maca, test u Ciebie

Dzięki, że pomagasz przetestować VoiceFlow na Macu. To wersja robocza, jeszcze nikt jej nie
uruchamiał na prawdziwym Macu, więc może coś nie zadziałać, o to właśnie chodzi w teście.

## 1. Instalacja

1. Rozpakuj pobrany plik `VoiceFlow-macos-arm64.zip` (dwuklik w Finderze). Jeśli Safari
   rozpakowało go samo, w Pobranych leży już `VoiceFlow.app`, wtedy pomiń ten krok.
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
   - **Jeśli "Otwórz mimo to" się nie pojawia albo macOS pisze, że aplikacja jest uszkodzona:**
     otwórz Terminal (Cmd+spacja, wpisz `Terminal`, Enter), wklej tę linię i naciśnij Enter:
     ```
     xattr -dr com.apple.quarantine /Applications/VoiceFlow.app
     ```
     Potem uruchom VoiceFlow normalnie z Aplikacji.
5. Przy pierwszym uruchomieniu pokaże się okno powitalne po polsku. Zamknij je przyciskiem
   **"Zaczynam"**. Zaraz potem pokażą się okna o uprawnieniach (po angielsku, jedno od VoiceFlow i jedno od macOS). Co w nich kliknąć, opisuje sekcja 3; klucz z sekcji 2 możesz wkleić potem. Jeśli po około 30 sekundach nic się nie pokazało, przejdź do sekcji 5.

## 2. Klucz do Groq (do transkrypcji mowy)

1. Wejdź na console.groq.com/keys, załóż konto/zaloguj się, utwórz klucz API.
2. W oknie VoiceFlow: zakładka **Settings** > sekcja **API Keys** > pole **Groq API Key**, wklej
   klucz, kliknij **Save Settings** (na dole zakładki).

## 3. Uprawnienia

Po pierwszym uruchomieniu VoiceFlow i macOS poproszą o kilka uprawnień, zgódź się na wszystkie:

- **Dostępność** (Accessibility) i **Monitorowanie wprowadzania** (Input Monitoring), potrzebne,
  żeby klawisz skrótu i wklejanie tekstu działały. VoiceFlow pokaże okno po angielsku z przyciskiem
  **"Open Accessibility Settings"** (albo "Open Input Monitoring Settings"), kliknij go i włącz
  przełącznik przy VoiceFlow. Jeśli VoiceFlow nie ma na liście, kliknij **+** i wybierz VoiceFlow
  z Aplikacji. Oba ustawienia są w Ustawieniach systemowych > Prywatność i ochrona, sprawdź, czy
  włączone są oba.
- **Mikrofon**, o to VoiceFlow zapyta dopiero, gdy pierwszy raz przytrzymasz prawy Option. Kliknij
  Pozwól i spróbuj nagrać jeszcze raz (pierwsza próba się nie liczy, bo dopiero wtedy system pyta
  o zgodę).

Po włączeniu Dostępności i Monitorowania wprowadzania zamknij VoiceFlow (ikona w pasku menu >
"Quit") i otwórz go ponownie z Aplikacji. Bez tego klawisz skrótu może jeszcze nie zadziałać, mimo
że uprawnienia są już włączone.

## 4. Gdzie jest ikona i jak sterować oknem

VoiceFlow siedzi w pasku menu na górze ekranu, po prawej stronie. Nie ma ikony w Docku. Jeśli
masz Maca z notchem (wcięciem na górze ekranu) i ikon jest dużo, może się pod notch schować,
sprawdź czy się tam nie ukrywa.

Kliknij ikonę VoiceFlow w pasku menu i wybierz **"Open VoiceFlow"**, żeby otworzyć okno aplikacji.
Zamknięcie okna nie kończy działania VoiceFlow, aplikacja dalej działa w tle, w pasku menu. Żeby
całkiem zamknąć VoiceFlow: ikona w pasku menu > **"Quit"**.

## 5. Jeśli aplikacja się nie uruchamia albo nic nie widać

1. Poczekaj do około 30 sekund. Pierwsze uruchomienie jest wolne, bo macOS sprawdza wtedy
   wszystkie pliki aplikacji.
2. Sprawdź pasek menu, także pod notchem (sekcja 4).
3. Jeśli macOS pisze, że aplikacja jest uszkodzona, albo w sekcji 1 punkt 4 nie pojawia się
   "Otwórz mimo to": otwórz Terminal (Cmd+spacja, wpisz `Terminal`, Enter), wklej tę linię i
   naciśnij Enter:
   ```
   xattr -dr com.apple.quarantine /Applications/VoiceFlow.app
   ```
   Potem uruchom VoiceFlow normalnie z Aplikacji.
4. Jeśli dalej nic nie widać albo okno powitalne w ogóle się nie pokazało, uruchom VoiceFlow z
   Terminala, żeby zobaczyć, co się dzieje:
   - naciśnij Cmd+spacja, wpisz `Terminal` i naciśnij Enter,
   - wklej tę linię i naciśnij Enter:
     ```
     /Applications/VoiceFlow.app/Contents/MacOS/VoiceFlow
     ```
   - zrób zrzut ekranu okna Terminala albo skopiuj cały tekst, który się tam pojawi, i wyślij mi
     go, razem z plikiem `voiceflow.log` (sekcja 7), jeśli po tej próbie w ogóle powstał.
5. Jeśli VoiceFlow nagle znika albo macOS pokazuje okno "VoiceFlow nieoczekiwanie zakończył
   działanie": kliknij w nim "Zgłoś..." ("Report..."), skopiuj cały pokazany tekst i wyślij mi go.
   Alternatywnie znajdziesz te same dane w plikach `VoiceFlow*.ips`: w Finderze Idź > Idź do
   folderu (Cmd+Shift+G), wklej `~/Library/Logs/DiagnosticReports` i wyślij mi pliki stamtąd.

Zamknięcie Terminala zamyka też VoiceFlow uruchomione w ten sposób, to w porządku, służy to tylko
do zebrania komunikatów. Jeśli po wpisaniu tej linii pojawi się okno "VoiceFlow is already
running", to znaczy, że aplikacja działa, tylko nie widać ikony: napisz mi o tym.

## 6. Co sprawdzić

Przejdź po kolei, przy każdym punkcie zapamiętaj (albo zrób zrzut ekranu), czy zadziałało tak jak
opisane:

1. Zip się rozpakował, aplikacja wystartowała, ikona jest w pasku menu.
2. Po nadaniu uprawnień przytrzymanie prawego Option zaczyna nagrywanie.
3. Podyktowany tekst wkleja się poprawnie w Notatkach, w Slacku i w przeglądarce (Cmd+V), a okno,
   w którym piszesz, zostaje na pierwszym planie (fokus się nie przełącza).
4. Esc w trakcie nagrywania anuluje dyktowanie. Overlay (mały wskaźnik nagrywania) jest widoczny
   nawet nad aplikacją w trybie pełnoekranowym.
5. Drugie uruchomienie VoiceFlow nie otwiera drugiej kopii aplikacji. Jeśli włączysz **Start at
   login** (zakładka Settings, sekcja System), VoiceFlow wystartuje samo po ponownym zalogowaniu.
6. W zakładce Settings, w sekcji **Speech-to-Text**, wybierz pozycję zaczynającą się od **"Local"** (działa
   bez klucza API, offline), kliknij **"Download / load model"**, a po pobraniu (pojawi się
   "Model ready") kliknij **Save Settings**. Sprawdź, czy model się pobrał i czy transkrypcja
   działa.
7. Jeśli pojawi się baner o nowej wersji, sprawdź, czy kliknięcie w nim "Update" otwiera stronę do
   pobrania.
8. **W Notatkach wpisz polskie znaki ą, ę albo ł przez prawy Option** (tak jak na Windowsie
   AltGr). VoiceFlow nasłuchuje prawego Optiona w tle cały czas, niezależnie od tego, w jakiej
   aplikacji akurat piszesz, więc samo przytrzymanie tego klawisza (nawet do wpisania polskiej
   litery, a nie do dyktowania) może uruchomić nagrywanie. Sprawdź, czy przy wpisywaniu ą/ę/ł
   pojawia się overlay nagrywania i czy VoiceFlow rzeczywiście zaczyna nagrywać, mimo że nie o to
   Ci chodziło.

Nie musisz naprawiać żadnego problemu, po prostu zapisz, co się nie zgadza.

## 7. Jak odesłać wyniki

Skopiuj ten szablon, uzupełnij i odeślij (numery odpowiadają punktom z sekcji 6):

```
Wersja macOS (menu Apple > Ten Mac, np. macOS 15.3):
1. Instalacja i ikona w pasku menu: OK / nie: co się stało
2. Prawy Option zaczyna nagrywanie: OK / nie: co się stało
3. Wklejanie w Notatkach, Slacku, przeglądarce: OK / nie: co się stało
4. Esc anuluje, overlay nad pełnym ekranem: OK / nie: co się stało
5. Brak drugiej kopii, Start at login: OK / nie: co się stało
6. Lokalny Whisper: OK / nie: co się stało
7. Baner nowej wersji: OK / nie / nie pojawił się
8. Polskie znaki przez prawy Option: OK / nie: co się stało
Inne uwagi:
```

Do tego dołącz:

1. **Zrzut ekranu każdej wiadomości**, którą pokaże VoiceFlow (okna z uprawnieniami, błędy,
   cokolwiek niestandardowego).
2. **Log aplikacji:** w Finderze wejdź w menu Idź > Idź do folderu (albo skrót Cmd+Shift+G),
   wklej:
   ```
   ~/Library/Application Support/VoiceFlow
   ```
   i wyślij plik `voiceflow.log` z tego folderu. W środku nie ma kluczy API ani tego, co
   podyktowałeś, więc możesz go spokojnie wysłać. Jeśli aplikacja się nie uruchomiła, wyślij
   zarówno tekst z Terminala (sekcja 5), jak i ten plik, jeśli w ogóle powstał.

Dzięki za pomoc.
