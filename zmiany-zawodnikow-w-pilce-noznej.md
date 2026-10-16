# Zmiany zawodników w piłce nożnej

## Problem

Trener w meczu piłkarskim ma ograniczoną liczbę zmian (zwykle pięć w pięciu oknach) i musi zdecydować, kogo zmienić, kiedy i na kogo. Zawodnicy męczą się w trakcie meczu, część ma kartki, wynik się zmienia, a przeciwnik reaguje. Rzeczywiste decyzje są często oparte na intuicji i na stałych schematach (zmiany po 60. i 75. minucie).

Mecz dobrze opisuje ciąg zdarzeń: posiadanie piłki, podanie, strzał, faul, kartka, gol, zmiana. Nie jest potrzebny ciągły model ruchu, wystarczy model przejść między zdarzeniami.

## Konkretne pytanie badawcze

> Czy trener-agent, który zmienia zawodników na podstawie zmęczenia, ryzyka kartek i wyniku, osiąga lepszy bilans bramek niż trener ze stałym harmonogramem zmian?

## Zakres modelu

### Elementy

- **Drużyna** — jedenastu zawodników na boisku i ławka rezerwowych; skład i formacja.
- **Zawodnik** — jakość ofensywna i defensywna, pozycja, zmęczenie rosnące wraz z minutami i intensywnością, liczba kartek.
- **Posiadanie piłki** — aktualna drużyna, strefa boiska, ciąg zdarzeń.
- **Trener (agent)** — w oknach zmian decyduje, czy dokonać zmiany, kogo wprowadzić i kogo zdjąć.
- **Przeciwnik** — drużyna o ustalonej sile, zachowująca się według rozkładów z danych.

### Zdarzenia dyskretne

- rozpoczęcie posiadania piłki w danej strefie,
- podanie udane lub nieudane, strata piłki,
- strzał, gol, obrona lub niecelny strzał,
- faul, żółta lub czerwona kartka, rzut wolny lub karny,
- kontuzja zawodnika,
- okno zmian i decyzja trenera,
- przerwa, początek drugiej połowy, koniec meczu.

### Zmęczenie

Zmęczenie rośnie z czasem gry i z liczbą akcji zawodnika. Wpływa na prawdopodobieństwo udanej akcji, fauli i kontuzji. Parametry zmęczenia można kalibrować na podstawie spadku skuteczności zawodników w drugich połowach meczów.

## Strategie do porównania

1. **Brak zmian** — punkt odniesienia.
2. **Stały harmonogram** — zmiany w 60., 70. i 80. minucie.
3. **Wg zmęczenia** — zmiana zawodnika, którego wskaźnik zmęczenia przekroczy próg.
4. **Wg wyniku** — zmiany ofensywne przy przegranej i defensywne przy wygranej.
5. **Ryzyko kartek** — wcześniejsza zmiana zawodnika z żółtą kartką na pozycji o dużej liczbie starć.
6. **Trener uczący się** — polityka ML (np. uczenie ze wzmocnieniem lub model przewidujący wartość zmiany), której cechami są minuta, wynik, zmęczenie i kartki.

## Dane i ich przygotowanie

Możliwe źródła:

- **StatsBomb Open Data** — zdarzenia meczowe (podania, strzały, faule, zmiany, składy) z wybranych rozgrywek udostępnionych za darmo na GitHubie,
- **FBref** — statystyki zawodników i minuty,
- **Football-Data.co.uk** — wyniki i kursy z wielu lig (do walidacji wyników),
- **Transfermarkt** — informacje o kontuzjach i kartkach (uwaga na regulamin pobierania danych).

Przygotowanie danych:

1. wybrać rozgrywki i sezony z pełnymi danymi zdarzeń (np. mundial, Euro, wybrane ligi dostępne w StatsBomb),
2. policzyć rozkłady czasu posiadania, liczby podań, strzałów, fauli na minutę gry oraz strat piłki,
3. oszacować wpływ minuty meczu i zmian na skuteczność (statystyka po 60. minucie),
4. zebrać historię zmian rzeczywistych trenerów (minuta, kontekst wyniku),
5. skalibrować rozkład wyników symulowanych meczów z rozkładem rzeczywistym (liczba goli, remisów),
6. zostawić część meczów do walidacji.

Otwarte dane nie zawierają śledzenia ruchu zawodników, więc zmęczenie trzeba wnioskować pośrednio i traktować jako założenie modelu.

## Teza i metryki

**Teza:** zmiany ustalane dynamicznie (zmęczenie, kartki, wynik) dają trenerowi lepszy bilans bramek niż stały harmonogram, a przewaga rośnie, gdy skład jest nierówny i ławka mocna.

Metryki:

- średni bilans bramek i oczekiwane punkty (xP) na mecz,
- odsetek zwycięstw, remisów i porażek,
- liczba goli straconych w ostatnich 20 minutach,
- liczba kartek i kontuzji,
- średnie zmęczenie zawodników na boisku w kolejnych minutach,
- wynik przy różnej sile przeciwnika i różnej jakości ławki.

Eksperymenty: tysiące symulowanych meczów z różnymi ziarnami losowymi, różni przeciwnicy, różna jakość ławki, różne tempo narastania zmęczenia. Ciekawy wynik to moment meczu, w którym wartość zmiany jest największa.

## Środowisko

Python. Silnik zdarzeń napisany od zera (`heapq`). `pandas` i `numpy` do danych, `statsbombpy` do pobierania zdarzeń, `matplotlib` do wykresów. Trener-agent może korzystać z `scikit-learn` lub z uczenia ze wzmocnieniem (`gymnasium`, `stable-baselines3`), przy czym środowisko meczowe pozostaje własne.

Opcjonalne rozszerzenie: rotacja składu w całym sezonie (meczy co 3–4 dni, zmęczenie i ryzyko kontuzji kumulują się między meczami). Pozwala to zrobić z projektu dwa etapy: pojedynczy mecz, a potem sezon.

Źródła:

- [StatsBomb Open Data](https://github.com/statsbomb/open-data),
- [FBref](https://fbref.com/),
- [Football-Data.co.uk](https://www.football-data.co.uk/).
