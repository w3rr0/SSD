# Dane Olist i generator zamówień: problemy i decyzje

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

## Sprawy otwarte
- Czym są „pilne zamówienia” w scenariuszu awarii, skoro prawdziwe terminy to
  kilka dni.
- Produkty z Olist trafią do symulacji dopiero po rozmieszczeniu ich na
  regałach (model przyjmuje tylko produkty, które leżą na regałach).
