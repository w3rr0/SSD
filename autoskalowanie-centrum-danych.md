# Autoskalowanie aplikacji w centrum danych

## Streszczenie

Projekt będzie symulował usługę internetową działającą na zbiorze serwerów lub instancji chmurowych. Do systemu napływają żądania o różnym czasie obsługi i priorytecie, a kontroler decyduje o rozdzielaniu ruchu, uruchamianiu nowych instancji oraz wyłączaniu niepotrzebnych. Model uwzględni rozgrzewanie instancji, kolejki, limity zasobów, awarie i skoki obciążenia.

System pozwoli porównać proste reguły autoskalowania z metodami predykcyjnymi. Dzięki temu można zbadać rzeczywisty kompromis: mniejszy koszt infrastruktury często oznacza większe opóźnienia, a utrzymywanie dużej rezerwy serwerów poprawia jakość kosztem zasobów.

## Model systemu

### Elementy

- **Generator żądań** — tworzy zadania według danych historycznych lub zadanego scenariusza.
- **Żądanie** — ma klasę usługi, wymagania CPU i pamięci, czas obsługi oraz deadline.
- **Load balancer** — kieruje żądania do aktywnych instancji.
- **Instancja** — ma określoną przepustowość, limit równoległych zadań i czas uruchomienia.
- **Kolejka** — przechowuje żądania oczekujące na zasób; może mieć osobne klasy priorytetowe.
- **Kontroler autoskalowania** — obserwuje metryki i zmienia liczbę instancji.
- **Monitor** — zbiera opóźnienia, błędy, zużycie zasobów i koszt.

### Stany instancji

`wyłączona -> uruchamiana -> gotowa -> przeciążona -> wygaszana -> wyłączona`, z dodatkowym stanem `uszkodzona`.

Żądanie może być w stanie `oczekujące`, `przetwarzane`, `zakończone`, `odrzucone` albo `przerwane przez awarię`.

### Zdarzenia

- pojawienie się żądania,
- rozpoczęcie i zakończenie obsługi,
- przekroczenie deadline'u,
- pomiar metryk,
- decyzja o dodaniu lub usunięciu instancji,
- zakończenie rozgrzewania,
- awaria i przywrócenie serwera,
- zmiana ceny lub limitu zasobów,
- wzrost albo spadek ruchu.

## Strategie autoskalowania

1. **Stała pula** — liczba instancji nie zmienia się w trakcie eksperymentu.
2. **Reguła progowa** — dodanie instancji po przekroczeniu CPU lub długości kolejki przez określony czas.
3. **Reguła z histerezą** — inne progi skalowania w górę i w dół, aby uniknąć ciągłego przełączania.
4. **Predykcja obciążenia** — uruchamianie instancji przed spodziewanym pikiem.
5. **Kontroler wielokryterialny** — decyzja oparta jednocześnie na opóźnieniu, długości kolejki, koszcie i ryzyku awarii.
6. **Agent ML** — opcjonalnie agent uczący się wyboru liczby instancji na podstawie stanu systemu.

Ważnym elementem będzie model kosztu: instancje mogą mieć różną wydajność, cenę i niezawodność, a uruchomienie dodatkowej instancji nie jest natychmiastowe.

## Dane

Najlepszym źródłem śladów obciążenia są:

- Google Cluster Workload Traces,
- Alibaba Cluster Trace,
- publiczne zbiory obciążenia serwerów i aplikacji,
- dane o ruchu HTTP dostępne w publicznych benchmarkach,
- publiczne cenniki instancji chmurowych, jeśli do modelu zostaną wprowadzone koszty.

Przygotowanie danych:

1. wybór kolumn opisujących czas, liczbę zadań i wymagane zasoby,
2. usunięcie błędnych, ujemnych i zduplikowanych rekordów,
3. agregacja do ustalonego kroku czasowego,
4. normalizacja jednostek CPU, pamięci i czasu,
5. rozdzielenie śladu na okres kalibracyjny i testowy,
6. przygotowanie osobnych scenariuszy: obciążenie stabilne, sezonowe, nagły pik i wielokrotne piki.

Nie należy zakładać, że jeden trace jest reprezentatywny. Każdy wariant powinien być uruchamiany na kilku fragmentach danych i z kilkoma ziarnami losowymi.

## Teza i eksperymenty

**Teza:** autoskalowanie oparte wyłącznie na bieżącym średnim obciążeniu reaguje zbyt późno na krótkie skoki ruchu, natomiast predykcja obciążenia może ograniczyć liczbę przekroczeń czasu odpowiedzi bez proporcjonalnego zwiększenia kosztu infrastruktury.

Eksperymenty:

- zmiana czasu rozgrzewania instancji,
- różne długości okna obserwacji,
- różne progi skalowania,
- błędna lub opóźniona predykcja,
- nagłe piki i obciążenie okresowe,
- awaria części instancji,
- żądania z różnymi deadline'ami,
- różne limity liczby instancji.

Metryki:

- średnie, medianowe i percentylowe opóźnienie odpowiedzi,
- odsetek żądań po deadline'ie,
- liczba odrzuconych i przerwanych zadań,
- koszt działania instancji,
- średnie i maksymalne wykorzystanie CPU oraz pamięci,
- liczba operacji skalowania,
- czas pozostawania w przeciążeniu,
- odporność na awarie.

## Środowisko i plan realizacji

Projekt można napisać w Pythonie, używając własnego kalendarza zdarzeń lub kolejki priorytetowej. `pandas` i `numpy` obsłużą trace'y, `matplotlib` i `seaborn` analizę wyników, a `scikit-learn` prosty model predykcyjny. Część odpowiedzialną za symulację warto utrzymać niezależnie od modelu ML, aby można było uczciwie porównać go z regułami bazowymi.

Etapy:

1. pojedynczy typ instancji i kolejka żądań,
2. wiele instancji oraz load balancing,
3. uruchamianie, wygaszanie i koszt,
4. dane rzeczywiste i scenariusze pików,
5. awarie, priorytety i deadline'y,
6. predykcja obciążenia lub uczenie ze wzmocnieniem.

