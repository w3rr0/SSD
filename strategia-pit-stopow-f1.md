# Strategia pit stopów w Formule 1

## Problem

W wyścigu F1 strateg zespołu podejmuje kilka kluczowych decyzji: kiedy zjechać do alei serwisowej, jakie opony założyć i czy zareagować na safety car, deszcz albo ruch rywali. Każda decyzja jest kompromisem. Świeże opony dają szybsze okrążenia, ale pit stop kosztuje kilkanaście–kilkadziesiąt sekund i może wrzucić kierowcę w ruch na torze. Safety car może obniżyć koszt zjazdu, ale pojawia się nieprzewidywalnie.

Problem dobrze pasuje do symulacji zdarzeń dyskretnych: wyścig składa się z okrążeń, pit stopów, neutralizacji i zmian pogody, a nie z ciągłego przepływu.

## Konkretne pytanie badawcze

> Czy strateg uczący się na danych historycznych wybiera pit stopy lepiej niż stała strategia ustalona przed wyścigiem, zwłaszcza gdy w wyścigu pojawia się safety car lub zmienia się pogoda?

## Zakres modelu

### Elementy

- **Kierowca i samochód** — bazowe tempo, wrażliwość na zużycie opon, zużycie paliwa (spadek masy), ryzyko błędu.
- **Opony** — mieszanka (miękka, średnia, twarda, przejściowa, deszczowa), wiek, spadek tempa wraz z wiekiem.
- **Tor** — liczba okrążeń, koszt zjazdu do alei (strata czasu), trudność wyprzedzania.
- **Pozostali kierowcy** — zachowują się według uproszczonych reguł lub według strategii odtworzonych z danych historycznych.
- **Neutralizacje** — safety car, wirtualny safety car, czerwona flaga.
- **Pogoda** — sucho, mokro, przejściowo.
- **Strateg** — agent, który po każdym okrążeniu wybiera: zostać na torze albo zjechać i założyć daną mieszankę.

### Zdarzenia dyskretne

- zakończenie okrążenia przez kierowcę,
- decyzja strategiczna po okrążeniu,
- zjazd do alei i wyjazd po pit stopie,
- wyprzedzenie lub utrata pozycji,
- pojawienie się i zakończenie safety cara lub VSC,
- zmiana pogody,
- awaria lub kolizja,
- ukończenie wyścigu.

Czas wyścigu jest przeskakiwany od zdarzenia do zdarzenia. Nie jest potrzebny model fizyki samochodu, wystarczy rozkład czasów okrążeń zależny od wieku opony, paliwa i ruchu przed kierowcą.

## Strategie do porównania

1. **Stały plan** — pit stop w z góry ustalonych okrążeniach.
2. **Reguła zużycia** — zjazd, gdy tempo spadnie o zadany próg.
3. **Reakcja na neutralizację** — jak wyżej, z tanim zjazdem pod safety carem.
4. **Strateg z uczeniem ze wzmocnieniem** — polityka wyuczona (np. PPO lub DQN) na symulowanych wyścigach z różnymi scenariuszami.
5. **Strategia odtworzona z danych** — imitacja decyzji rzeczywistych zespołów jako punkt odniesienia.

## Dane i ich przygotowanie

Możliwe źródła:

- **FastF1** — biblioteka Pythona, która pobiera czasy okrążeń, mieszanki opon, wiek opon, pit stopy, neutralizacje i pogodę; dane od 2018 r.,
- **Jolpica / Ergast** — wyniki wyścigów, pozycje startowe i końcowe, pit stopy (Ergast API zostało wycofane, sprawdzić aktualny następca),
- dane o torach: długość, strata czasu w alei, liczba wyprzedzeń.

Przygotowanie danych:

1. wybrać kilka torów i sezonów, np. 2019–2024,
2. odrzucić okrążenia pit stopów, startu i neutralizacji w analizie spadku tempa opon,
3. dopasować krzywą spadku tempa w funkcji wieku opony i mieszanki,
4. oszacować koszt pit stopu na każdym torze oraz rozkład czasu postoju,
5. wyznaczyć częstość i długość safety carów na każdym torze,
6. zostawić część wyścigów do testów, nieużywaną przy kalibracji.

Uwaga: nie ma pełnych danych o stanie samochodu i strategii rywali w czasie rzeczywistym, więc część parametrów (np. tempo bazowe) trzeba wyznaczać z samych czasów okrążeń.

## Teza i metryki

**Teza:** strateg uczący się reagować na bieżącą sytuację (wiek opon, pozycja, neutralizacja) osiąga lepszy wynik końcowy niż stała strategia, a różnica jest największa w wyścigach z safety carem lub zmienną pogodą; w spokojnych wyścigach strategia stała jest prawie optymalna.

Metryki:

- średnia i mediana pozycji końcowej,
- różnica czasu do zwycięzcy,
- liczba pit stopów,
- liczba punktów zdobytych w sezonie symulowanych wyścigów,
- odsetek wyścigów, w których strategia pobiła stałą,
- wynik w scenariuszach z safety carem i bez niego,
- odporność na błędny model opon (zmiana parametrów o ±10–20%).

Eksperymenty powinny uwzględniać wiele ziaren losowych oraz osobno spokojne i chaotyczne wyścigi. Wynik interesujący to próg częstości neutralizacji, od którego strategia ucząca się zaczyna wyraźnie wygrywać.

## Środowisko

Python. Silnik zdarzeń można napisać od zera na `heapq`. `fastf1`, `pandas` i `numpy` posłużą do danych, a `matplotlib` do wykresów. Agenta można zbudować w `stable-baselines3` lub `gymnasium`, ale środowisko (symulator wyścigu) zostaje napisane od zera. Część "nice to have" z `ideas.md` (aktorzy jako agenci ML) jest tu rdzeniem projektu.

Źródła:

- [FastF1](https://docs.fastf1.dev/),
- [Jolpica F1 API](https://github.com/jolpica/jolpica-f1).
