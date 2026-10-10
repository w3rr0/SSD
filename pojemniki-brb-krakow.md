# Dynamiczny odbiór dużych pojemników BRB w Krakowie

## Problem

MPO Kraków obsługuje dużą liczbę dużych pojemników na odpady segregowane, określanych jako BRB. Pojemniki nie napełniają się w tym samym tempie: zależy to między innymi od lokalizacji, dnia tygodnia, sezonu i sąsiednich punktów zbiórki. Stały harmonogram może powodować jednocześnie przepełnienia jednych pojemników i niepotrzebne przejazdy do prawie pustych.

Problemem jest decyzja, **kiedy wysłać pojazd i w jakiej kolejności odwiedzić pojemniki**, gdy poziom zapełnienia jest tylko częściowo znany, pojazdy mają ograniczoną pojemność, a w trakcie dnia pojawiają się nowe zgłoszenia.

## Konkretne pytanie badawcze

> Czy dynamiczne planowanie odbioru na podstawie przewidywanego poziomu zapełnienia zmniejsza liczbę przepełnień bardziej niż stały harmonogram, bez nieproporcjonalnego zwiększenia długości tras i liczby pojazdów?

Nie chodzi o samo rozwiązanie problemu najkrótszej trasy. Trasa jest częścią systemu, którego stan zmienia się w czasie. Pojemnik pominięty dziś może się przepełnić jutro, a pilny odbiór może zmienić trasę i spowodować przekroczenie pojemności pojazdu.

## Zakres modelu

### Pojemniki

Każdy BRB ma:

- lokalizację,
- pojemność,
- aktualny poziom zapełnienia,
- tempo napełniania zależne od dnia i pory,
- typ zbieranej frakcji,
- koszt przepełnienia,
- czas obsługi.

Tempo napełniania może być losowe, ale powinno być kalibrowane na podstawie rzeczywistych pomiarów lub danych z case study. Warto rozdzielić pojemniki o stabilnym profilu od tych, których napełnienie jest silnie zmienne.

### Pojazdy i baza

Pojazd ma:

- pojemność ładunkową,
- aktualne obciążenie,
- czas przejazdu,
- czas opróżniania jednego pojemnika,
- czas pracy kierowcy,
- bazę, do której musi wrócić,
- ograniczenia dotyczące frakcji odpadów.

Można zacząć od jednego typu pojazdu, a dopiero później dodać różne pojemności lub pojazd rezerwowy.

## Zdarzenia dyskretne

- przyrost zapełnienia pojemnika,
- rozpoczęcie i zakończenie trasy,
- przyjazd pojazdu do pojemnika,
- rozpoczęcie i zakończenie odbioru,
- zapełnienie pojazdu,
- powrót do bazy i rozładunek,
- zgłoszenie przepełnienia,
- awaria pojazdu,
- utrudnienie na trasie,
- przekroczenie poziomu przepełnienia,
- aktualizacja prognozy zapełnienia,
- przeplanowanie trasy.

W ten sposób można obserwować, jak pojedyncze opóźnienie albo błędna prognoza zmienia kolejne decyzje, zamiast tylko obliczyć statyczną trasę.

## Strategie do porównania

1. **Stały harmonogram** — odbiór w ustalonych dniach i kolejności.
2. **Próg zapełnienia** — odbiór po przekroczeniu np. 70%, 80% lub 90%.
3. **Najkrótsza trasa** — minimalizacja kilometrów bez pełnej prognozy przyszłego zapełnienia.
4. **Priorytet ryzyka** — pierwszeństwo pojemników, które mogą przepełnić się przed kolejnym dostępem pojazdu.
5. **Prognoza krótkoterminowa** — planowanie na podstawie historii danego pojemnika i dnia tygodnia.
6. **Planowanie odporne** — pozostawienie rezerwy czasu i pojemności na pilne zgłoszenia.
7. **Dynamiczne przeplanowanie** — aktualizacja trasy po nowych pomiarach lub zgłoszeniu przepełnienia.

## Dane i ich przygotowanie

Możliwe źródła:

- dane MPO Kraków o lokalizacji i obsłudze BRB,
- historyczne poziomy zapełnienia, jeżeli zostaną udostępnione,
- rejestry zgłoszeń przepełnienia,
- dane GPS pojazdów odbierających odpady,
- dane o trasach i czasach odbioru,
- dane drogowe o czasach przejazdu,
- publiczne opracowania dotyczące 639 BRB w Krakowie i planowania ich obsługi.

Przygotowanie danych:

1. zbudować mapę pojemników i bazy,
2. usunąć duplikaty lokalizacji i nieaktywne punkty,
3. ujednolicić czas pomiarów i tras,
4. wyznaczyć rozkłady dziennego przyrostu zapełnienia,
5. rozdzielić profile centrum miasta, osiedli mieszkaniowych i punktów o sezonowym popycie,
6. oznaczyć dni z awariami lub niepełną obsługą,
7. podzielić dane na kalibrację, test normalnego obciążenia i test sytuacji awaryjnych.

Jeżeli nie będzie dostępnych historycznych poziomów zapełnienia, należy użyć danych o rzeczywistych odbiorach i zgłoszeniach do kalibracji rozkładu napełniania. Wyniki trzeba wtedy opisać jako analizę scenariuszową, a nie dokładną prognozę dla każdego pojemnika.

## Teza i metryki

**Teza:** strategia minimalizująca długość tras może zwiększać liczbę przepełnionych pojemników; niewielki wzrost kosztu przejazdów może znacząco ograniczyć przepełnienia, jeśli poziomy zapełnienia są nierównomierne i zmienne.

Metryki:

- liczba i czas przepełnień,
- liczba zgłoszeń wymagających pilnego odbioru,
- długość tras,
- czas pracy pojazdów,
- liczba wyjazdów do bazy,
- średnie i maksymalne zapełnienie przed odbiorem,
- wykorzystanie pojemności pojazdu,
- liczba nieobsłużonych pojemników,
- koszt operacyjny,
- liczba mieszkańców potencjalnie dotkniętych przepełnieniem.

Eksperymenty powinny zmieniać:

- liczbę dostępnych pojazdów,
- próg planowego odbioru,
- dokładność prognozy,
- natężenie napełniania,
- liczbę awarii,
- czas przejazdu,
- udział pojemników o sezonowo zmiennym popycie.

Szczególnie wartościowe będzie wyznaczenie krzywej kompromisu: ile dodatkowych kilometrów trzeba przejechać, aby uniknąć kolejnego procenta przepełnień.

## Środowisko

Python jest wystarczający do modelu i eksperymentów. Dane można przygotować w `pandas`, graf drogowy przechowywać z użyciem własnych struktur lub `networkx`, a kalendarz zdarzeń obsłużyć przez kolejkę priorytetową. Algorytmy trasowania powinny być oddzielone od symulatora, aby porównać heurystyki z dynamicznym przeplanowaniem.

Źródła:

- [case study optymalizacji odbioru odpadów w polskim mieście](https://slw.wat.edu.pl/Optimizing-Municipal-Waste-Collection-a-Case-Study-of-a-City-in-Poland,176021,0,2.html),
- [opracowanie dotyczące odbioru krakowskich pojemników BRB](https://www.academia.edu/44002556/SOLVING_THE_GARBAGE_TRUCK_ROUTING_PROBLEM_FOR_COLLECTING_RECYCLABLES_FROM_BIG_RECYCLING_BINS_USING_THE_VRP_SPREADSHEET_SOLVER).
