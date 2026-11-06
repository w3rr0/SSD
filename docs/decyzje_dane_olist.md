# Dane Olist, generator zamówień i walidacja: problemy i decyzje

Ten plik zbiera decyzje podjęte przy kalibracji symulacji na danych Olist:
co było problemem, jakie były opcje, co wybraliśmy i dlaczego. Liczby
pochodzą z prawdziwych danych (Kaggle, „Brazilian E-Commerce Public Dataset
by Olist”).

Pliki, których to dotyczy:

| Plik | Co robi |
| --- | --- |
| `data/download_olist.py` | pobiera dane z Kaggle do `data/raw/` |
| `src/data/olist.py` | wczytuje dane i liczy rozkłady |
| `src/orders/olist_generator.py` | generuje zamówienia z tych rozkładów |
| `runners/olist_report.py` | raport z danych (`make olist_report`) |
| `runners/olist_validation.py` | walidacja generatora na 2018 (`make olist_validation`) |
| `runners/olist_plots.py` | wykresy danych i walidacji (`make olist_plots`) |
| `src/validation/queueing.py` | wzór z teorii kolejek i przedział ufności |
| `tests/test_queueing.py` | walidacja kolejki: samo stanowisko vs wzór |
| `runners/queue_validation.py` | walidacja kolejki: cały magazyn vs wzór (`make queue_validation`) |

## 1. Dane i narzędzia

### pandas czy polars
- **Problem:** do obróbki tabel można użyć pandas albo polars.
- **Decyzja:** pandas.
- **Powód:** danych jest około 100 tys. wierszy, więc przewaga polars
  w szybkości nic tu nie daje. pandas jest szerzej znany i dobrze współpracuje
  z Mesą.

### Gdzie trzymać dane
- **Problem:** pliki z Kaggle mają kilkadziesiąt MB i własną licencję.
- **Decyzja:** dane nie trafiają do repozytorium. `data/raw/` jest
  w `.gitignore`, a skrypt `data/download_olist.py` pobiera i rozpakowuje
  tylko dwa potrzebne pliki (`olist_orders_dataset.csv`,
  `olist_order_items_dataset.csv`).
- **Powód:** rozmiar repozytorium i licencja. Skrypt korzysta tylko
  z biblioteki standardowej, więc nie dodaje zależności.

## 2. Wczytywanie danych

### Które zamówienia liczymy
- **Problem:** zamówienia w Olist mają statusy (`delivered`, `shipped`,
  `canceled`, `unavailable`…).
- **Opcje:** wszystkie zamówienia albo bez anulowanych i niedostępnych.
- **Decyzja:** pomijamy `canceled` i `unavailable`.
- **Powód:** takie zamówienia nie zostały zrealizowane i często nie mają
  żadnych produktów, więc nie powstałby z nich kurs robota w magazynie.

### Kilka sztuk tego samego produktu
- **Problem:** Olist zapisuje każdą sztukę jako osobny wiersz.
- **Decyzja:** sztuki tego samego produktu w jednym zamówieniu łączymy w jedną
  pozycję z liczbą sztuk (`quantity`).
- **Powód:** w magazynie to jeden regał i jedno pobranie kilku sztuk, a nie
  kilka osobnych kursów. Liczba sztuk wydłuża tylko czas kompletacji.

### Termin wysyłki
- **Problem:** w Olist termin nadania (`shipping_limit_date`) ma każdy
  sprzedawca osobno, a jedno zamówienie może mieć kilku sprzedawców.
- **Decyzja:** termin zamówienia to najwcześniejszy z terminów jego
  sprzedawców.
- **Powód:** w symulacji jest jeden magazyn, więc zamówienie musi być gotowe
  w całości do pierwszego terminu.

### Czas
- **Decyzja:** czas zakupu zostaje w czasie lokalnym Brazylii, bez zmiany
  strefy, i zachowujemy pełną datę (nie tylko dzień tygodnia i godzinę).
- **Powód:** profil dnia ma odpowiadać zachowaniu klientów, a pełna data
  pozwala wyciągnąć dni wyjątkowe, np. Black Friday.

## 3. Statystyki z danych

Z danych liczymy (osobno dla 2017 i 2018):

- **liczba różnych produktów w zamówieniu**: udział zamówień z 1, 2, 3…
  produktami; mówi, ile regałów trzeba przywieźć,
- **liczba sztuk w pozycji**: udział pozycji z 1, 2, 3… sztukami; wpływa na
  czas kompletacji,
- **profil przyjść**: tabela 7 × 24, średnia liczba zamówień w danym dniu
  tygodnia i godzinie,
- **liczba zamówień każdego dnia kalendarza** (dni bez zamówień liczą się
  jako 0, żeby nie zawyżać średnich),
- **popularność produktów**,
- **czas od zakupu do terminu wysyłki**.

### Jak mierzyć popularność
- **Opcje:** A) w ilu zamówieniach produkt występuje, B) ile sztuk sprzedano.
- **Decyzja:** liczymy obie, a rozmieszczenie ABC i generator używają A.
- **Powód:** jedno zamówienie z produktem to jeden przyjazd regału do
  stanowiska, niezależnie od liczby sztuk. ABC ma skracać właśnie te kursy.
  Sprawdzenie na danych: obie miary dają prawie tę samą kolejność (korelacja
  rang 0,94, 91 ze 100 najpopularniejszych produktów wspólnych).

### Co pokazały dane

| | 2017 | 2018 |
| --- | --- | --- |
| Zamówienia (bez anulowanych) | 44 375 | 53 531 |
| Zakres | 361 dni (od 5.01) | 246 dni (do 3.09) |
| Średnio zamówień dziennie | 123 | 218 |
| Zamówienia z 1 produktem | 96,7% | 96,8% |
| Pozycje z 1 sztuką | 93,1% | 93,1% |
| Różnych produktów | 17 159 | 20 376 |

Wnioski:
- prawie każde zamówienie to jeden produkt, więc zamówienia rzadko wymagają
  kilku regałów,
- sklep urósł o ~77% między latami (ważne przy walidacji),
- Black Friday 2017 (24.11) miał 1166 zamówień, ok. 9,5 razy więcej niż
  średni dzień.

## 4. Generator zamówień

### Jak powstają zamówienia
- **Decyzja:** niejednorodny proces Poissona. W każdej godzinie zegarowej
  oczekiwana liczba zamówień to wartość z profilu dla tego dnia tygodnia
  i godziny, razy mnożnik `volume_factor`. Liczbę zamówień losujemy
  z rozkładu Poissona, a ich momenty równomiernie w tej godzinie. Każde
  zamówienie dostaje liczbę produktów, konkretne produkty (z wagą popularności,
  bez powtórzeń) i liczbę sztuk, wszystko losowane z rozkładów z 2017.
- **Powód:** opis każe odtworzyć z danych liczbę produktów w zamówieniu,
  rozkład w czasie i popularność. Proces Poissona to standardowy model
  niezależnych klientów i pasuje do walidacji z teorią kolejek.
- Generator tworzy zamówienia tylko dla symulowanego okna (np. jednego dnia
  albo zmiany), a nie dla całego roku. Szczyt, np. Black Friday, robimy
  mnożnikiem `volume_factor`.

### Termin wysyłki w generatorze
- **Opcje:** A) losować prawdziwe czasy „zakup → termin” z 2017,
  B) stały termin, np. 2 dni.
- **Decyzja:** A.
- **Powód:** rozkład zostaje taki jak w danych, a nie wymyślony przez nas.
- **Zauważony problem:** terminy w Olist są długie, najczęściej 4–7 dni
  (mediana 6 dni, minimum 95 h). W symulacji jednego dnia żadne zamówienie
  się nie spóźni. Przydział zadań według terminu nadal działa (wcześniejszy
  termin idzie pierwszy), ale „spóźnienie” jako metryka nie wystąpi.
  Ustalenie, czym są „pilne zamówienia”, zostawiamy na scenariusze.

### Nietypowe terminy w danych
- **Problem:** 110 zamówień z 2017 (0,25%) ma termin dłuższy niż 30 dni,
  a 2 mają termin w 2020 (ok. 1050 dni).
- **Sprawdzenie:** większość z nich to 30–50 dni (mediana 38), a ten sam ogon
  jest w 2018. To raczej normalna część danych (np. produkty na zamówienie),
  a nie błędy. Wyraźnie błędne wyglądają tylko te 2 z 2020.
- **Opcje:** A) zostawić wszystko, B) usunąć tylko terminy po końcu danych,
  C) usunąć wszystko powyżej 30 dni.
- **Decyzja:** A, nic nie usuwamy.
- **Powód:** próg 30 dni byłby arbitralny i wyciąłby prawdopodobnie prawdziwe
  zamówienia. Wpływ jest pomijalny: średni termin 7,06 dnia z ogonem
  i 6,93 bez niego. Generator wylosuje jeden z dwóch błędnych terminów mniej
  więcej raz na 22 tys. zamówień, a w symulacji jednego dnia działa on tak
  samo jak każdy długi termin (zamówienie najmniej pilne).

## 5. Walidacja generatora na 2018

Generator dopasowany do 2017 generuje tyle dni, ile obejmują dane 2018
(246 dni od 1.01.2018). Te same statystyki liczymy dla wygenerowanych i dla
prawdziwych zamówień z 2018 i porównujemy.

### Procenty zamiast liczb
- **Problem:** w 2018 było o 77% więcej zamówień dziennie. Generator z 2017
  zawsze da ich mniej, i to nie z jego winy, tylko dlatego, że firma urosła.
- **Opcje:** A) porównać kształt (udziały procentowe), a wolumen podać osobno,
  B) przeskalować generator mnożnikiem i porównać liczby.
- **Decyzja:** A.
- **Powód:** walidacja ma sprawdzić wzorzec: kiedy klienci kupują, ile
  produktów biorą i co jest popularne. Wolumen to parametr scenariusza
  (`volume_factor`), a wzrost raportujemy jako jedną liczbę (×1,77).

### Kiedy uznajemy wynik za zgodny
- **Opcje:** A) test statystyczny (np. chi-kwadrat), B) największa różnica
  udziałów z progiem.
- **Decyzja:** B, próg 2 punkty procentowe.
- **Powód:** przy dziesiątkach tysięcy zamówień test chi-kwadrat odrzuca
  nawet różnice rzędu 0,1%, które w praktyce nic nie znaczą. Różnica
  w punktach procentowych jest prosta do zrozumienia i oceny.

### Black Friday a profil zwykłego dnia
- **Problem:** pierwsza walidacja dała piątek +2,07 pp ponad 2018. Przyczyną
  był Black Friday 2017: profil liczy średnią po wszystkich piątkach, więc ten
  jeden dzień podbijał każdy zwykły piątek. Bez niego piątek w 2017 to 13,0%,
  a w 2018 13,3%.
- **Opcje:** A) liczyć profil zwykłego dnia bez dni wyjątkowych, a szczyt
  robić mnożnikiem, B) zostawić i opisać różnicę.
- **Decyzja:** A. Dni wyjątkowe są wpisane jawnie w `EXCEPTIONAL_DAYS`
  w `src/data/olist.py` (na razie tylko 24.11.2017). Pozostałe statystyki
  (popularność, liczba produktów) dalej liczymy ze wszystkich dni.
- **Powód:** pasuje do scenariusza z opisu „normalny dzień vs szczyt”.
  Zwykły dzień nie powinien zawierać wpływu Black Friday.

### Jak mierzyć koncentrację popularności
- **Problem:** pierwsza miara („jaki procent zamówień pokrywa top 1% / 10% /
  50% produktów”) dała różnice do 7 pp. Okazało się, że zależy od liczby
  zamówień: im mniej zamówień, tym mniej różnych produktów się pojawia, więc
  „1% produktów” to inna grupa.
- **Drugi powód różnic:** asortyment się wymienia. 15,4 tys. z 20,4 tys.
  produktów sprzedanych w 2018 nie występowało w 2017, a 55% zamówień z 2018
  zawiera taki nowy produkt. Generator zna tylko katalog z 2017.
- **Opcje:** A) porównać top 10, 100 i 1000 produktów (stała liczba),
  B) zostawić „top X%”.
- **Decyzja:** A.
- **Powód:** dla ABC liczy się czołówka, a magazyn w symulacji i tak ma stały
  katalog. Różnice w długim ogonie opisujemy jako znane ograniczenie.

### Wynik walidacji

| Porównanie | Największa różnica | Wynik |
| --- | --- | --- |
| Liczba produktów w zamówieniu | 0,13 pp | zgodne |
| Liczba sztuk w pozycji | 0,10 pp | zgodne |
| Godzina doby | 0,69 pp | zgodne |
| Dzień tygodnia | 0,99 pp | zgodne |
| Koncentracja (top 10 / 100 / 1000) | 0,41 / 0,48 / 2,65 pp | niezgodne na top 1000 |

Wolumen: 2017 to 123 zamówienia dziennie (120 bez Black Friday), 2018 to 218,
a generator daje ok. 120.

### Znane ograniczenia
- **Top 1000 produktów (2,65 pp).** Generator jest bardziej skupiony na
  czołówce niż prawdziwy 2018. Przyczyną jest długi ogon i wymiana
  asortymentu: generator losuje tylko z produktów 2017, a w prawdziwym 2018
  część zamówień trafia w nowe, rzadkie produkty. Przy wolumenie
  przeskalowanym do 2018 różnica spada do ok. 1,75 pp, więc część różnicy
  wynika z samej liczby zamówień. Czołówka (top 10 i 100), która decyduje
  o ABC, się zgadza.
- **Brak nowych produktów.** Generator nie tworzy produktów, których nie było
  w 2017. W symulacji magazyn ma stały katalog, więc to świadome
  uproszczenie.
- **Brak świąt w 2018.** Dane 2018 kończą się 3.09, więc szczytu
  (Black Friday) nie da się zwalidować na 2018. Wzór szczytu opiera się na
  jednym dniu z 2017.

## 6. Walidacja symulacji z teorią kolejek

### Po co
Walidacja generatora sprawdza dane wejściowe. Ta sprawdza silnik symulacji:
czy magazyn poprawnie liczy czas czekania. Bierzemy przypadek, dla którego
teoria kolejek podaje dokładny wynik, i porównujemy go z symulacją. Celowo bez
danych Olist, bo wzór zakłada stały ruch, a Olist zmienia się co godzinę.
Ten sam test warto powtarzać po każdej większej zmianie modelu.

### Wzór
Stanowisko to kolejka FIFO z jednym pracownikiem. Przy przyjazdach
z rozkładu Poissona (λ na sekundę) i czasie obsługi S średni czas czekania
w kolejce to wzór Pollaczka–Chinczyna dla M/G/1:
`Wq = λ·E[S²] / (2·(1 − ρ))`, gdzie `ρ = λ·E[S]` to obciążenie stanowiska.
Dla stałej obsługi (M/D/1) to `ρ·E[S] / (2(1 − ρ))`, dla wykładniczej (M/M/1)
dwa razy więcej. Przykład: obsługa 15 s, robot co 30 s, ρ = 0,5, czekanie 7,5 s.

### Co testujemy
- **Opcje:** A) samo stanowisko, któremu sami podajemy przyjazdy z rozkładu
  Poissona (bez siatki i jazdy robotów), B) cały magazyn z jednym
  stanowiskiem, C) oba.
- **Decyzja:** oba. B to główna walidacja wymagana przez opis, A to test
  dodatkowy.
- **Powód:** w A założenia wzoru są spełnione w 100%, więc A pokazuje, czy
  sama kolejka działa. Jeśli B odbiega od wzoru, a A nie, różnicę robi ruch
  robotów, a nie błąd w kolejce.

### Ustawienia
- Zamówienia: 1 produkt, 1 sztuka, przychodzą ze stałą intensywnością
  (proces Poissona), produkt losowany równomiernie ze 160 regałów. Obsługa:
  5 s + 10 s za sztukę, czyli 15 s.
- Obciążenie stanowiska ρ: 0,3; 0,5; 0,7; 0,9, każde przy obsłudze stałej
  i wykładniczej.
- 40 robotów. Sprawdzone, że to nie ogranicza wyniku: przy 120 robotach
  wynik był taki sam.
- Zgodność: każde ustawienie 20 razy z innym seedem, odrzucamy początek
  przebiegu (pusty magazyn), liczymy średnią i 95% przedział ufności.
  Zgodne, jeśli wzór mieści się w przedziale.

### Długość przebiegów
- **Problem:** przy krótkich przebiegach (20 000 s) symulacja zaniżała czas
  czekania przy dużym obciążeniu (ρ = 0,9: 55 s zamiast 67,5 s). Kolejka
  przy prawie zapchanym stanowisku długo się rozkręca od zera i mocno się
  waha, więc krótki przebieg jej nie „łapie”. Liczba robotów nie miała
  wpływu.
- **Opcje:** A) dłuższe przebiegi tylko przy dużym obciążeniu i kilka
  procesów naraz, B) zostawić krótkie i opisać zaniżenie, C) mniej ustawień.
- **Decyzja:** A. Przy ρ 0,3 i 0,5: 2 000 s rozgrzewki + 20 000 s pomiaru,
  przy 0,7: 5 000 + 40 000 s, przy 0,9: 10 000 + 80 000 s. Całość trwa
  ok. 7 minut na 4 rdzeniach.
- **Powód:** sprawdza też duże obciążenie, a czas jest akceptowalny.

### Wynik

Część A (samo stanowisko, 100 000 robotów na ustawienie): zgodne ze wzorem,
błąd do 3,5% przy ρ = 0,5 i do 8,8% przy ρ = 0,8 (sprawdzone na 30 seedach).

Część B (cały magazyn):

| Obsługa | ρ | Wzór [s] | Symulacja [s] | Wynik |
| --- | --- | --- | --- | --- |
| stała | 0,3 | 3,2 | 3,0 ± 0,2 | tuż poza przedziałem |
| stała | 0,5 | 7,5 | 7,2 ± 0,5 | zgodne |
| stała | 0,7 | 17,5 | 16,6 ± 0,9 | zgodne |
| stała | 0,9 | 67,5 | 63,9 ± 5,9 | zgodne |
| wykładnicza | 0,3 | 6,4 | 6,3 ± 0,8 | zgodne |
| wykładnicza | 0,5 | 15,0 | 14,0 ± 1,8 | zgodne |
| wykładnicza | 0,7 | 35,0 | 32,8 ± 2,3 | zgodne |
| wykładnicza | 0,9 | 135,0 | 117,1 ± 11,4 | niezgodne |

### Znane różnice
- **Symulacja wychodzi o 3–7% poniżej wzoru we wszystkich ustawieniach.**
  Roboty ruszają się co 1 s (tik symulacji), więc dojeżdżają do stanowiska
  tylko w pełnych sekundach. Przez to przyjazdy są trochę bardziej regularne
  niż czysto losowe: współczynnik zmienności odstępów to 0,97 zamiast 1.
  Według przybliżenia Kingmana czas czekania rośnie z (C²ₐ + C²ₛ)/2, co daje
  ok. 6% mniej przy obsłudze stałej i ok. 3% mniej przy wykładniczej. To się
  zgadza z wynikami, a przy ρ = 0,3 i obsłudze stałej wystarcza, żeby wyjść
  tuż poza przedział. To cecha modelu z krokiem 1 s, a nie błąd. Sprawdzone
  też, że kolejka podana dokładnie tymi przyjazdami, które wygenerowała
  symulacja, daje ten sam czas czekania co stanowisko w modelu.
- **ρ = 0,9 przy obsłudze wykładniczej** jest nadal zaniżone o 13%. To
  najbardziej zmienny przypadek. Dłuższe przebiegi zbliżały wynik do wzoru
  (przy 8 przebiegach po 80 000 s: 120 ± 25 s), ale dalsze wydłużanie
  zajmuje zbyt dużo czasu.

## Sprawy otwarte
- Czym są „pilne zamówienia” w scenariuszu awarii, skoro prawdziwe terminy to
  kilka dni.
- Produkty z Olist trafią do symulacji dopiero po rozmieszczeniu ich na
  regałach (model przyjmuje tylko produkty, które leżą na regałach).
