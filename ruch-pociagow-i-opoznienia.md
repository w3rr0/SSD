# Zarządzanie ruchem pociągów i opóźnieniami w sieci kolejowej

## Streszczenie

Projekt zakłada symulację fragmentu sieci kolejowej, w której pociągi pasażerskie i towarowe współdzielą tory, rozjazdy oraz stacje. Każdy pociąg ma rozkład jazdy, priorytet, ograniczenia prędkości i zestaw stacji, przez które musi przejechać. Dyspozytor lub algorytm sterujący przydziela pociągom możliwość wjazdu na ograniczone odcinki i rozwiązuje konflikty.

Model ma badać nie tylko pojedyncze opóźnienie, lecz także jego propagowanie w całej sieci. Przykładowo opóźniony pociąg może zająć tor, opóźnić skład jadący z przeciwnego kierunku, a następnie spowodować utratę przesiadek na kolejnej stacji.

## Model systemu

### Elementy

- **Sieć** — skierowany lub nieskierowany graf odcinków torów, stacji i rozjazdów.
- **Odcinek toru** — ma długość, przepustowość, ograniczenie prędkości i zasady zajmowania.
- **Stacja** — ma perony, czasy postoju, możliwość zmiany toru i połączenia przesiadkowe.
- **Rozjazd** — zasób, którego nie mogą jednocześnie używać sprzeczne przebiegi.
- **Pociąg pasażerski** — ma rozkład, priorytet, pojemność i listę postojów.
- **Pociąg towarowy** — może mieć niższy priorytet, większą długość i mniejszą prędkość.
- **Dyspozytor** — wybiera kolejność przejazdu i reaguje na zakłócenia.
- **Podróżny lub połączenie** — opcjonalny model umożliwiający liczenie utraconych przesiadek.

### Stany pociągu

`oczekuje na odjazd -> jedzie -> oczekuje przed zajętym odcinkiem -> stoi na stacji -> zmienia tor -> opóźniony -> zakończył trasę`.

Dodatkowo można modelować stany `awaria`, `skrócona relacja` i `przekierowany`, jeżeli zakłócenie wymaga zmiany planu.

### Zdarzenia

- planowy lub rzeczywisty odjazd,
- wjazd i zjazd z odcinka,
- zajęcie albo zwolnienie rozjazdu,
- przyjazd na stację i odjazd po postoju,
- wykrycie konfliktu przebiegów,
- opóźnienie pociągu,
- awaria infrastruktury lub taboru,
- zamknięcie toru,
- zmiana priorytetów przez dyspozytora,
- utrata przesiadki przez pasażerów.

## Sterowanie i warianty

1. **Rozkład statyczny** — decyzje podejmowane według pierwotnych priorytetów.
2. **Zasada first come, first served** — pierwszy pociąg w kolejce otrzymuje odcinek, poza sytuacjami bezpieczeństwa.
3. **Priorytet pasażerski** — pociągi pasażerskie mają pierwszeństwo przed towarowymi.
4. **Priorytet dynamiczny** — priorytet rośnie wraz z opóźnieniem i ryzykiem utraty przesiadek.
5. **Minimalizacja propagacji** — wybór przejazdu, który minimalizuje przewidywane opóźnienia kolejnych pociągów.
6. **Agent dyspozytora** — opcjonalny agent ML lub uczenia ze wzmocnieniem wybierający akcję na podstawie stanu zajętości sieci.

Każda strategia musi respektować ograniczenia bezpieczeństwa: dwa sprzeczne przebiegi nie mogą zostać przyznane jednocześnie, a pociąg nie może wjechać na zajęty odcinek bez zdefiniowanej reguły współdzielenia.

## Dane

Możliwe źródła:

- rozkłady jazdy w formacie GTFS lub GTFS-Realtime,
- OpenStreetMap jako źródło geometrii i podstawowej topologii,
- publiczne dane o rzeczywistych opóźnieniach przewoźników,
- otwarte dane krajowych zarządców infrastruktury,
- informacje o zamknięciach torów i remontach, jeżeli są publikowane,
- syntetyczne zakłócenia, gdy dane o awariach są niepełne.

Przygotowanie danych:

1. wybór niewielkiego, spójnego fragmentu sieci,
2. mapowanie stacji i odcinków na graf,
3. usunięcie lub oznaczenie niepoprawnych geometrii,
4. ujednolicenie czasu lokalnego i obsługa zmiany czasu,
5. połączenie rozkładu z rzeczywistymi czasami przejazdu,
6. wyznaczenie rozkładów opóźnień dla różnych typów pociągów,
7. przygotowanie scenariuszy zakłóceń niezależnych od danych historycznych.

Dane geograficzne nie zawsze zawierają wszystkie informacje eksploatacyjne, takie jak długość blokady odcinka czy dokładne zasady sygnalizacji. Te parametry należy jawnie określić i poddać analizie wrażliwości, zamiast traktować je jako dane rzeczywiste.

## Teza i eksperymenty

**Teza:** dynamiczne ustalanie priorytetów na podstawie bieżących opóźnień, zajętości infrastruktury i ryzyka utraty przesiadek ogranicza całkowite opóźnienie oraz jego propagację skuteczniej niż stałe priorytety przypisane typom pociągów.

Eksperymenty:

- wzrost natężenia ruchu na wspólnym odcinku,
- opóźnienie jednego pociągu na początku symulacji,
- zamknięcie pojedynczego toru,
- awaria rozjazdu lub stacji,
- różny udział pociągów towarowych,
- różne bufory czasowe w rozkładzie,
- różne poziomy priorytetu i zasady obsługi przesiadek,
- porównanie małej i gęstej sieci.

Metryki:

- średnie, medianowe i maksymalne opóźnienie,
- opóźnienie na końcu trasy względem opóźnienia początkowego,
- liczba utraconych przesiadek,
- liczba pociągów przepuszczonych przez sieć,
- czas oczekiwania przed odcinkami i na stacjach,
- wykorzystanie torów, stacji i rozjazdów,
- punktualność osobno dla pociągów pasażerskich i towarowych,
- nierówność kosztu opóźnień między grupami pociągów.

## Środowisko i plan realizacji

Podstawą może być Python z własnym silnikiem zdarzeń i grafem infrastruktury. `pandas` posłuży do obróbki rozkładów, `networkx` do prototypowania grafu, a `matplotlib` lub `folium` do wizualizacji tras i opóźnień. Docelowo logikę zajmowania odcinków i rozjazdów warto napisać samodzielnie, aby zachować kontrolę nad regułami modelu.

Etapy:

1. graf stacji i odcinków oraz pojedynczy pociąg,
2. rozkład jazdy, postoje i zajmowanie torów,
3. konflikty, rozjazdy i kolejki pociągów,
4. opóźnienia i podstawowe zakłócenia,
5. porównanie strategii dyspozytorskich,
6. przesiadki, awarie infrastruktury i opcjonalny agent ML.

Największym ryzykiem jest niepełna zgodność publicznych danych z rzeczywistymi zasadami prowadzenia ruchu. Dlatego projekt powinien od początku rozdzielać warstwę danych infrastruktury od parametrów modelu i raportować, które założenia są rzeczywiste, a które syntetyczne.
