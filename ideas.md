**Nice to have**: Aktorzy w symulacji jako agenci ML wytrenowani na zebranych danych; Przynajmniej jako część aktorów.

## Ruch pojazdów

**Potrzebne**: Dane z ruchu kierowców, mapowanie na model ML kierowców w symulacji, żeby wyłapać styl jazdy przeciętnego kierowcy, najlepiej z konkretnych miejsc, które będą brane pod uwagę.

Środowisko najprawdopodobniej Python z uwagi na pracę z danymi oraz C++ przez wymagające warunki sprzętowe dla symulacji z dużą ilością kierowców na raz

### Symulacja ruchu kierowców i pojazdów autonomicznych

Porównanie wypadkowości, przepustowości i dynamiki ruchu samochodowego przy danym % pojazdów autonomicznych.

Pojazdy autonimiczne będa reprezentowane za pomcocą deterministycznych warunków (np. if else)

**Teza**: Pojazdy autonomiczne usprawniają ruch drogowy oraz robią go bardziej bezpiecznym.

### Symulacja zastąpienia skrzyżowań rondami

Budowa ronda mieszczącego się na obszarze danego skrzyżowania oraz zasymulowanie przepustowości w obu przypadkach

**Teza**: Ronda zawsze mają większą przepustowość dla małych i średnich skrzyżowań (plus są tańsze w budowie), natomiast skrzyżowania mają sens dopiero przy większym ruchu.
Znaleźć ten punkt graniczny za pomocą symulacji z różnym natężeniem ruchu drogowego
