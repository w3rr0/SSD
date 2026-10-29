# Kolejność operacji na Lotnisku Chopina przy zamkniętym pasie

## Problem

Lotnisko Chopina w Warszawie korzysta z dwóch przecinających się pasów startowych. Czasowe zamknięcie jednego z nich zmniejsza przepustowość i powoduje konflikt między kolejką przylotów oraz kolejką odlotów. Problemem nie jest samo wyznaczenie maksymalnej liczby operacji na godzinę, ale wybór kolejności operacji w ciągu dnia, gdy opóźnienia, zajętość stanowisk i obsługa naziemna wzajemnie na siebie wpływają.

Dokumenty przepustowości lotniska wskazywały dla sezonu 2024 różne poziomy przepustowości zależnie od liczby dostępnych pasów. Można wykorzystać je jako ograniczenia modelu, nie zakładając, że deklarowana przepustowość jest osiągalna w każdym scenariuszu.

## Konkretne pytanie badawcze

> Jaka polityka ustalania kolejności startów i lądowań najlepiej ogranicza całkowite opóźnienie podczas zamknięcia jednego pasa, gdy uwzględni się zajętość stanowisk postojowych i czasy obsługi naziemnej?

Badanie powinno porównywać nie tylko opóźnienie samolotów, lecz także opóźnienie pasażerów i liczbę lotów, które tracą kolejne ograniczenia operacyjne. Priorytet przylotów może ograniczać oczekiwanie w powietrzu, ale jednocześnie zająć stanowiska potrzebne samolotom odlatującym.

## Zakres modelu

### Zasoby

- aktywny pas startowy,
- kolejka przylotów i kolejka odlotów,
- drogi kołowania,
- stanowiska postojowe,
- rękawy lub autobusy obsługi pasażerskiej,
- ekipy i pojazdy obsługi naziemnej,
- sloty czasowe,
- przestrzeń oczekiwania dla samolotów przylatujących.

### Samoloty

Każdy samolot ma:

- planowany czas przylotu lub odlotu,
- typ i wymagany czas separacji,
- czas zajęcia stanowiska,
- czas obsługi naziemnej,
- planowany kolejny lot,
- liczbę pasażerów,
- liczbę pasażerów z przesiadkami,
- tolerowane opóźnienie.

Nie trzeba odtwarzać pełnego modelu lotu. W projekcie przedmiotowym wystarczy model operacji od momentu wejścia samolotu do kolejki do opuszczenia systemu, z parametrami skalibrowanymi na danych historycznych.

## Zdarzenia dyskretne

- zgłoszenie samolotu do przylotu,
- gotowość samolotu do odlotu,
- przyznanie operacji na pasie,
- lądowanie lub start,
- rozpoczęcie i zakończenie kołowania,
- podstawienie na stanowisko,
- rozpoczęcie i zakończenie obsługi naziemnej,
- zwolnienie stanowiska,
- utrata slotu,
- opóźnienie rejsu wynikające z opóźnienia poprzedniego odcinka,
- czasowe zamknięcie lub ponowne otwarcie pasa,
- awaria pojazdu lub zasobu obsługi.

## Strategie do porównania

1. **FIFO** — kolejność według czasu gotowości samolotu.
2. **Priorytet przylotów** — ograniczanie czasu oczekiwania samolotów w powietrzu.
3. **Priorytet odlotów** — ograniczanie blokowania stanowisk i opóźnień operacji naziemnych.
4. **Naprzemienne okna** — planowe serie przylotów i odlotów.
5. **Priorytet rotacji** — pierwszeństwo samolotów, których następny rejs jest najbardziej zagrożony.
6. **Priorytet pasażerski** — uwzględnienie liczby pasażerów oraz ryzyka utraty przesiadek.
7. **Sterowanie dynamiczne** — wybór operacji na podstawie bieżącej długości kolejek, zajętości stanowisk i przewidywanego efektu kolejnych opóźnień.

Każda strategia musi respektować separację, dostępność pasa, ograniczenia stanowisk oraz czasy obsługi. Dzięki temu porównanie nie będzie wyłącznie sortowaniem listy lotów.

## Dane i ich przygotowanie

Możliwe źródła:

- deklaracje przepustowości i ograniczeń Lotniska Chopina,
- rozkłady lotów i dane o rzeczywistych operacjach,
- OpenSky Network do obserwacji trajektorii i czasów operacji,
- dane o opóźnieniach lotniczych,
- mapa pasów, dróg kołowania i stanowisk,
- dane pogodowe,
- publiczne informacje o zamknięciach infrastruktury.

Przygotowanie danych:

1. wybrać kilka dni o dużym obciążeniu,
2. połączyć planowane i rzeczywiste czasy operacji,
3. wyznaczyć rozkłady opóźnień oraz czasów obsługi,
4. sklasyfikować samoloty według typu i wymaganej separacji,
5. odtworzyć osobno scenariusz z dwoma pasami i z jednym zamkniętym pasem,
6. zachować dane testowe poza zbiorem używanym do kalibracji.

Jeżeli nie uda się uzyskać publicznych danych o stanowiskach i obsłudze naziemnej, parametry te należy zebrać z dokumentacji lub modelować jako rozkłady przedziałowe. Nie należy przedstawiać takich założeń jako dokładnego odwzorowania operacji lotniska.

## Teza i metryki

**Teza:** polityka minimalizująca bieżące opóźnienie pojedynczego samolotu nie musi minimalizować całkowitego opóźnienia pasażerów; strategia dynamiczna, która uwzględnia kolejki, stanowiska i kolejne rotacje samolotów, może ograniczyć efekt domina skuteczniej niż FIFO oraz stały priorytet przylotów.

Metryki:

- średnie i percentylowe opóźnienie przylotów oraz odlotów,
- całkowita liczba minut opóźnienia,
- liczba utraconych slotów,
- liczba utraconych przesiadek,
- czas oczekiwania samolotów w powietrzu,
- wykorzystanie pasa i stanowisk,
- długość kolejek,
- liczba odwołanych lub przekierowanych operacji,
- całkowite opóźnienie pasażerów.

Eksperymenty należy powtarzać z różnymi ziarnami losowymi i wariantami zamknięcia pasa. Interesujący wynik może mieć postać progu obciążenia, od którego dana strategia przestaje stabilizować rozkład.

## Środowisko

Python wystarczy do przygotowania danych i pierwszej wersji symulatora. Kalendarz zdarzeń można zaimplementować na kolejce priorytetowej, a wyniki analizować za pomocą `pandas`, `numpy` i `matplotlib`. Geometrię lotniska można przechowywać jako graf. Projekt powinien mieć osobną warstwę modelu operacyjnego i osobną warstwę strategii, aby porównywać polityki bez kopiowania symulatora.

Źródła:

- [deklaracja przepustowości Lotniska Chopina, sezon 2024](https://www.acl-uk.org/wp-content/uploads/2024/04/S24-WAW-Capacity-declaration-updated.pdf),
- [dane Urzędu Lotnictwa Cywilnego](https://caa.gov.pl/aktualnosci/przewozy-w-polskich-portach-lotniczych-w-2025-roku),
- [OpenSky Network](https://opensky-network.org/).

