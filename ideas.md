**Nice to have**: Aktorzy w symulacji jako agenci ML wytrenowani na zebranych danych; Przynajmniej jako część aktorów.

## Logistyka i infrastruktura

### Autonomiczny magazyn i system kompletacji zamówień

Symulacja centrum logistycznego z robotami transportowymi, pracownikami, stacjami kompletacji, kolejkami zamówień, ładowarkami i awariami. Projekt pozwoli porównać rozmieszczenie produktów oraz strategie przydzielania zadań i planowania tras pod względem czasu realizacji, przepustowości, energii i liczby konfliktów robotów. Szczegółowy opis znajduje się w pliku [`autonomiczny-magazyn.md`](autonomiczny-magazyn.md).

### Autoskalowanie aplikacji w centrum danych

Symulacja infrastruktury serwerowej obsługującej zmienne obciążenie, z kolejkami żądań, serwerami o różnych parametrach, awariami i mechanizmami uruchamiania oraz wyłączania instancji. Można porównać autoskalowanie reaktywne, predykcyjne i oparte na uczeniu maszynowym, badając kompromis między kosztem, opóźnieniem i niezawodnością. Szczegółowy opis znajduje się w pliku [`autoskalowanie-centrum-danych.md`](autoskalowanie-centrum-danych.md).

### Zarządzanie ruchem pociągów i opóźnieniami w sieci kolejowej

Symulacja sieci kolejowej z pociągami pasażerskimi i towarowymi, ograniczoną przepustowością torów, rozjazdami, priorytetami, rozkładem jazdy oraz zakłóceniami. Celem jest sprawdzenie, czy dynamiczne ustalanie priorytetów i zmiana kolejności przejazdu ogranicza propagowanie opóźnień skuteczniej niż sztywne reguły dyspozytorskie. Szczegółowy opis znajduje się w pliku [`ruch-pociagow-i-opoznienia.md`](ruch-pociagow-i-opoznienia.md).

## Ruch pojazdów

**Potrzebne**: Dane z ruchu kierowców, mapowanie na model ML kierowców w symulacji, żeby wyłapać styl jazdy przeciętnego kierowcy, najlepiej z konkretnych miejsc, które będą brane pod uwagę.

Środowisko najprawdopodobniej Python z uwagi na pracę z danymi oraz C++ przez wymagające warunki sprzętowe dla symulacji z dużą ilością kierowców na raz

### Symulacja ruchu kierowców i pojazdów autonomicznych

Porównanie wypadkowości, przepustowości i dynamiki ruchu samochodowego przy różnym udziale pojazdów autonomicznych oraz różnych stylach jazdy kierowców. Szczegółowy opis znajduje się w pliku [`ruch-kierowcow-i-pojazdow-autonomicznych.md`](ruch-kierowcow-i-pojazdow-autonomicznych.md).

Pojazdy autonimiczne będa reprezentowane za pomcocą deterministycznych warunków (np. if else)

**Teza**: Pojazdy autonomiczne usprawniają ruch drogowy oraz robią go bardziej bezpiecznym.

### Symulacja zastąpienia skrzyżowań rondami

Budowa modelu ronda mieszczącego się na obszarze istniejącego skrzyżowania i porównanie obu rozwiązań przy różnym natężeniu oraz strukturze ruchu. Szczegółowy opis znajduje się w pliku [`zastepowanie-skrzyzowan-rondami.md`](zastepowanie-skrzyzowan-rondami.md).

**Teza**: Ronda zawsze mają większą przepustowość dla małych i średnich skrzyżowań (plus są tańsze w budowie), natomiast skrzyżowania mają sens dopiero przy większym ruchu.
Znaleźć ten punkt graniczny za pomocą symulacji z różnym natężeniem ruchu drogowego
