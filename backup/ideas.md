**Nice to have**: Aktorzy w symulacji jako agenci ML wytrenowani na zebranych danych; Przynajmniej jako część aktorów.

## Konkretne problemy operacyjne

### Kolejność operacji na Lotnisku Chopina przy zamkniętym pasie

Symulacja ma odpowiedzieć, jaka polityka ustalania kolejności startów i lądowań najlepiej ogranicza propagację opóźnień podczas czasowego zamknięcia jednego pasa na Lotnisku Chopina. Model obejmie kolejki przylotów i odlotów, czasy kołowania i obsługi naziemnej, stanowiska postojowe oraz utratę kolejnych slotów. Szczegółowy opis znajduje się w pliku [`lotnisko-chopina-zamkniety-pas.md`](lotnisko-chopina-zamkniety-pas.md).

### Dynamiczny odbiór dużych pojemników BRB w Krakowie

Symulacja ma zbadać, czy MPO Kraków powinno opróżniać duże pojemniki na odpady segregowane według stałego harmonogramu, czy dynamicznie na podstawie przewidywanego poziomu zapełnienia. Model obejmie zmienne tempo napełniania, pojemność pojazdów, czas opróżniania, zgłoszenia przepełnienia i przeplanowanie tras. Szczegółowy opis znajduje się w pliku [`pojemniki-brb-krakow.md`](pojemniki-brb-krakow.md).

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

### Adaptacja kierowców do deterministycznych pojazdów autonomicznych na rondzie

Badanie, czy kierowcy nauczeni na podstawie rzeczywistego ruchu zaczną wykorzystywać przewidywalne zachowanie deterministycznych pojazdów autonomicznych, gdy funkcją nagrody będzie skrócenie własnego czasu przejazdu. Najpierw kierowcy uczą się przejazdu przez konkretne rondo, potem do ruchu wprowadza się AV, a w kolejnych epizodach kierowcy douczają się na podstawie interakcji z nimi. Szczegółowy opis znajduje się w pliku [`adaptacja-kierowcow-do-av-na-rondzie.md`](adaptacja-kierowcow-do-av-na-rondzie.md).

### Symulacja zastąpienia skrzyżowań rondami

Budowa modelu ronda mieszczącego się na obszarze istniejącego skrzyżowania i porównanie obu rozwiązań przy różnym natężeniu oraz strukturze ruchu. Szczegółowy opis znajduje się w pliku [`zastepowanie-skrzyzowan-rondami.md`](zastepowanie-skrzyzowan-rondami.md).

**Teza**: Ronda zawsze mają większą przepustowość dla małych i średnich skrzyżowań (plus są tańsze w budowie), natomiast skrzyżowania mają sens dopiero przy większym ruchu.
Znaleźć ten punkt graniczny za pomocą symulacji z różnym natężeniem ruchu drogowego
