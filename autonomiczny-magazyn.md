# Autonomiczny magazyn i system kompletacji zamówień

## Streszczenie

Projekt zakłada stworzenie symulacji centrum logistycznego, w którym zamówienia są kompletowane przez flotę autonomicznych robotów transportowych oraz pracowników obsługujących stacje kompletacji. System będzie uwzględniał ograniczoną liczbę zasobów, kolejki, priorytety zamówień, ładowanie robotów, blokowanie alejek i awarie. Najważniejszym celem będzie porównanie strategii rozmieszczenia produktów, przydzielania zadań i planowania tras.

Nie będzie to wyłącznie wizualizacja ruchu robotów. Istotą projektu będzie dyskretna symulacja całego procesu: od pojawienia się zamówienia, przez rezerwację produktów i transport, aż do spakowania paczki i opuszczenia magazynu.

## Model systemu

### Elementy

- **Magazyn** — graf alejek, skrzyżowań, stanowisk i stref składowania.
- **Produkty** — artykuły o różnej popularności, rozmiarze i wymaganiach dotyczących składowania.
- **Zamówienia** — lista produktów, priorytet, termin realizacji i ewentualne ograniczenia łączenia z innymi zamówieniami.
- **Roboty** — pojemność, bateria, prędkość, zajmowana przestrzeń i aktualny stan.
- **Stacje kompletacji** — ograniczona liczba stanowisk, przy których produkty trafiają do zamówień.
- **Pracownicy** — mogą wykonywać kompletację, uzupełniać regały i usuwać skutki awarii.
- **Ładowarki** — zasoby, do których roboty ustawiają się w kolejce.
- **Kontroler magazynu** — przydziela zadania, wybiera priorytety i reaguje na przeciążenia.

### Stany robotów

Robot może znajdować się między innymi w stanie:

`bezczynny -> jadący po produkt -> oczekujący na przejazd -> pobierający produkt -> jadący do stacji -> rozładowujący -> ładowany -> awaria`.

Przejście między stanami generuje zdarzenia. Przykładowo pobranie produktu może zakończyć się dopiero po czasie zależnym od typu produktu i dostępności pracownika.

### Zdarzenia

- pojawienie się nowego zamówienia,
- rozpoczęcie i zakończenie kompletacji,
- przydzielenie zadania robotowi,
- przyjazd do węzła grafu,
- zajęcie lub zwolnienie odcinka alejki,
- wykrycie konfliktu tras,
- rozpoczęcie i zakończenie ładowania,
- awaria oraz naprawa robota,
- uzupełnienie zapasu produktu,
- wysłanie gotowego zamówienia.

## Strategie do porównania

1. **Strategia bazowa** — stałe rozmieszczenie produktów i przydzielanie najbliższego wolnego robota.
2. **ABC** — najpopularniejsze produkty umieszczane najbliżej stacji kompletacji.
3. **Dynamic slotting** — okresowa zmiana lokalizacji produktów na podstawie ostatniego popytu.
4. **Najkrótsza trasa** — planowanie przejazdu algorytmem A* z uwzględnieniem aktualnych blokad.
5. **Planowanie konfliktów** — rezerwowanie fragmentów trasy w czasie, aby ograniczyć wzajemne blokowanie robotów.
6. **Przydział priorytetowy** — uwzględnianie terminu wysyłki, długości trasy i poziomu baterii.

Jako rozszerzenie można dodać agentów ML: model przewidujący popyt na produkty albo agenta wybierającego zadanie dla robota. Wyniki takiego agenta należy porównać z prostymi, interpretowalnymi heurystykami.

## Dane

Do kalibracji można wykorzystać:

- publiczne zbiory zamówień e-commerce, np. Brazilian E-Commerce Public Dataset by Olist,
- zbiory transakcji z informacją o liczbie i częstotliwości kupowanych produktów,
- publiczne benchmarki robotycznych magazynów i algorytmów planowania tras,
- dane o czasie kompletacji i ładowania robotów z dokumentacji producentów,
- syntetyczne mapy magazynu oraz syntetyczne awarie.

Przygotowanie danych:

1. usunięcie anulowanych i niekompletnych zamówień,
2. ujednolicenie stref czasowych i formatów dat,
3. grupowanie produktów według częstości występowania,
4. wyznaczenie rozkładów wielkości zamówień i odstępów między zamówieniami,
5. przeskalowanie liczby zamówień do rozmiaru eksperymentalnego magazynu,
6. rozdzielenie danych na zestaw kalibracyjny i scenariusze testowe.

## Teza i eksperymenty

**Teza:** dynamiczne rozmieszczanie najczęściej pobieranych produktów oraz planowanie tras uwzględniające konflikty zmniejsza średni czas realizacji zamówienia i liczbę przestojów, ale przy dużym zagęszczeniu robotów korzyść z krótszych tras ustępuje korzyści z zarządzania ruchem.

Eksperymenty powinny zmieniać:

- liczbę robotów,
- intensywność napływu zamówień,
- proporcję zamówień pilnych,
- rozkład popularności produktów,
- liczbę stacji i ładowarek,
- odsetek awarii,
- pojemność baterii.

Metryki:

- średni, medianowy i maksymalny czas realizacji,
- przepustowość magazynu,
- odsetek zamówień po terminie,
- czas oczekiwania w kolejkach,
- przebyty dystans,
- zużycie energii,
- wykorzystanie robotów, stacji i ładowarek,
- liczba konfliktów, blokad i awarii.

## Środowisko i plan realizacji

Najwygodniejsze będzie Python z własnym silnikiem zdarzeń dyskretnych, grafem magazynu i modułem eksperymentów. `pandas` i `numpy` posłużą do przygotowania danych, a `matplotlib` lub `pygame` do wizualizacji. Algorytmy grafowe można zaimplementować samodzielnie, aby projekt nie sprowadzał się do użycia gotowego symulatora.

Etapy:

1. model grafu i pojedynczego robota,
2. zamówienia, stacje i kolejki,
3. wiele robotów oraz konflikty tras,
4. ładowanie, awarie i uzupełnianie zapasów,
5. porównanie strategii i analiza statystyczna wielu powtórzeń,
6. opcjonalny model predykcji popytu lub agent ML.

