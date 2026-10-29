# Symulacja ruchu kierowców i pojazdów autonomicznych

## Streszczenie

Projekt zakłada stworzenie mikroskopowej symulacji ruchu drogowego, w której każdy pojazd jest osobnym aktorem posiadającym pozycję, prędkość, przyspieszenie, trasę i zestaw reguł zachowania. Celem nie jest jedynie wyznaczenie średniej prędkości na drodze, ale zbadanie wpływu stopniowego wprowadzania pojazdów autonomicznych na bezpieczeństwo i przepustowość.

W symulacji wystąpią zarówno pojazdy prowadzone przez ludzi, jak i pojazdy autonomiczne. Kierowcy będą różnić się stylem jazdy: ostrożnością, czasem reakcji, preferowanym odstępem, skłonnością do zmiany pasa oraz reakcją na ryzyko. Pojazdy autonomiczne mogą początkowo korzystać z deterministycznego kontrolera, a później zostać rozszerzone o model wyuczony na danych.

## Model systemu

### Elementy

- **Sieć drogowa** — skrzyżowania, pasy ruchu, odcinki dróg, ograniczenia prędkości i sygnalizacja.
- **Pojazd** — długość, masa, maksymalna prędkość, przyspieszenie, hamowanie i aktualna trasa.
- **Kierowca ludzki** — czas reakcji, styl jazdy, obserwowany odstęp oraz prawdopodobieństwo zmiany pasa.
- **Kontroler autonomiczny** — obserwuje otoczenie, planuje prędkość i podejmuje decyzje o hamowaniu lub zmianie pasa.
- **Sygnalizacja** — cykle świateł, fazy dla poszczególnych kierunków i ewentualna adaptacja do kolejki.
- **Zdarzenie drogowe** — kolizja, gwałtowne hamowanie, blokada pasa lub opuszczenie trasy.

### Stany pojazdu

`oczekuje na wjazd -> jedzie -> hamuje -> stoi w kolejce -> zmienia pas -> przejeżdża skrzyżowanie -> zakończył trasę`.

Dodatkowe stany to `awaryjne hamowanie`, `kolizja` i `zablokowany`. Przejścia między stanami zależą od odległości do poprzedzającego pojazdu, sygnalizacji, planowanej trasy i zachowania innych uczestników.

### Zdarzenia

- pojawienie się pojazdu na wlocie,
- aktualizacja decyzji kierowcy lub kontrolera,
- zmiana fazy sygnalizacji,
- rozpoczęcie i zakończenie zmiany pasa,
- przejazd przez skrzyżowanie,
- gwałtowne hamowanie,
- kolizja lub sytuacja bliska kolizji,
- awaria pojazdu,
- opuszczenie sieci przez pojazd.

Symulacja powinna działać w krokach czasowych, na przykład 0,1–0,5 sekundy, ponieważ reakcja kierowcy i chwilowe odstępy mają znaczenie dla bezpieczeństwa. Zdarzenia o większej skali, takie jak pojawienie się pojazdu i zmiana świateł, można obsługiwać przez osobny kalendarz zdarzeń.

## Modele zachowania

### Kierowcy ludzcy

Można rozpocząć od parametrów inspirowanych modelami IDM i MOBIL:

- model podążania za pojazdem określa bezpieczną prędkość i odstęp,
- model zmiany pasa ocenia korzyść z manewru oraz ryzyko,
- rozkłady czasu reakcji i przyspieszenia różnicują kierowców,
- osobne klasy opisują kierowcę ostrożnego, przeciętnego i agresywnego.

### Pojazdy autonomiczne

Kontroler autonomiczny może uwzględniać:

- bezpieczny odstęp zależny od prędkości,
- ograniczenie gwałtownych zmian przyspieszenia,
- predykcję ruchu sąsiednich pojazdów,
- zakaz wjazdu przy niewystarczającej luce,
- komunikację z sygnalizacją albo innymi pojazdami.

Ważne jest, aby pojazdy autonomiczne miały jawnie określone ograniczenia percepcji, opóźnienie reakcji i błędy pomiaru. W przeciwnym razie porównanie z kierowcami ludzkimi byłoby nierealistyczne.

## Dane

Możliwe źródła:

- highD i rFpro, jeśli warunki licencji pozwolą na użycie odpowiednich nagrań lub trajektorii,
- NGSIM, zawierający trajektorie pojazdów z wybranych odcinków dróg,
- inD lub inD Intersection Dataset dla ruchu na skrzyżowaniach,
- OpenStreetMap do odtworzenia geometrii sieci,
- dane o wypadkach i natężeniu ruchu publikowane przez instytucje transportowe,
- dane pogodowe do scenariuszy deszczu, śliskiej nawierzchni i ograniczonej widoczności.

Przygotowanie danych:

1. wybrać jeden lub kilka odcinków o znanej geometrii,
2. ujednolicić układ współrzędnych i jednostki,
3. usunąć trajektorie z brakującymi fragmentami lub oznaczyć je jako niepewne,
4. wygładzić szum pomiarowy bez usuwania rzeczywistych gwałtownych manewrów,
5. wyznaczyć prędkość, przyspieszenie, odstępy i częstość zmian pasa,
6. dopasować rozkłady parametrów kierowców,
7. oddzielić dane kalibracyjne od scenariuszy testowych.

Dane z rzeczywistych pojazdów autonomicznych mogą być ograniczone. Dlatego ich zachowanie należy opisać osobnym zestawem parametrów i testować w scenariuszach kontrolowanych, zamiast udawać, że pochodzi ono bezpośrednio z obserwacji zwykłego ruchu.

## Teza i eksperymenty

**Teza:** wzrost udziału pojazdów autonomicznych zmniejsza liczbę niebezpiecznych interakcji i stabilizuje ruch, ale efekt na przepustowość zależy od ich parametrów, zachowania kierowców ludzkich oraz geometrii drogi.

Scenariusze:

- 0%, 10%, 25%, 50%, 75% i 100% pojazdów autonomicznych,
- mały, średni i duży napływ pojazdów,
- różny udział kierowców agresywnych,
- skrzyżowanie z sygnalizacją i odcinek wielopasmowy,
- deszcz, ograniczona widoczność i gorsza przyczepność,
- różne czasy reakcji i konserwatywność kontrolera autonomicznego,
- awaria sygnalizacji albo pojedyncza blokada pasa.

Metryki:

- przepustowość i średni czas przejazdu,
- długość oraz czas oczekiwania w kolejce,
- liczba kolizji,
- liczba sytuacji bliskich kolizji i gwałtownych hamowań,
- rozrzut prędkości oraz stabilność przepływu,
- liczba zmian pasa,
- zużycie energii lub paliwa,
- sprawiedliwość opóźnień między kierunkami ruchu.

Każdy eksperyment powinien być powtarzany z różnymi ziarnami losowymi. Wyniki należy przedstawiać z przedziałami ufności, a nie tylko pojedynczą wartością.

## Środowisko i plan realizacji

Prototyp można przygotować w Pythonie z `numpy`, `pandas` i `matplotlib`. Sieć drogową oraz geometrię można początkowo reprezentować własnymi strukturami, a cięższe eksperymenty przenieść do C++. Przydatny będzie własny silnik krokowy z kolejką zdarzeń, aby zachować kontrolę nad regułami i pomiarem.

Etapy:

1. jeden pas i model podążania za pojazdem,
2. wiele pasów, zmiana pasa i skrzyżowanie,
3. różne profile kierowców,
4. kontroler pojazdu autonomicznego,
5. kalibracja na trajektoriach rzeczywistych,
6. scenariusze bezpieczeństwa i analiza udziału pojazdów autonomicznych,
7. opcjonalny model ML przewidujący zachowanie kierowcy.

