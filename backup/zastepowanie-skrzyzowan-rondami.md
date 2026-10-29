# Symulacja zastępowania skrzyżowań rondami

## Streszczenie

Projekt ma porównać dwa sposoby organizacji ruchu w tej samej lokalizacji: klasyczne skrzyżowanie z sygnalizacją świetlną oraz rondo zaprojektowane w granicach porównywalnego obszaru. Dla obu wariantów zostanie zbudowany model geometrii, zasad pierwszeństwa i przepływu pojazdów.

Najważniejszym celem nie jest potwierdzenie, że jedno rozwiązanie zawsze jest lepsze, lecz znalezienie punktu granicznego zależnego od natężenia i struktury ruchu. Należy uwzględnić między innymi nierównomierne obciążenie wlotów, skręty w lewo, ruch pieszy, różny udział ciężarówek oraz nierównowagę kierunków.

## Model systemu

### Wariant skrzyżowania z sygnalizacją

- wloty i wyloty skrzyżowania,
- pasy do jazdy prosto i skrętu,
- program sygnalizacji z fazami i czasem międzyfazowym,
- kolejki na każdym wlocie,
- detektory pojazdów lub stały harmonogram,
- przejścia dla pieszych,
- konfliktowe kierunki ruchu.

### Wariant ronda

- jezdnia pierścieniowa z jednym lub większą liczbą pasów,
- wloty i wyloty,
- zasada pierwszeństwa pojazdów na rondzie,
- punkty włączania i opuszczania pierścienia,
- zmiana pasa na rondzie,
- przejścia dla pieszych,
- blokowanie wlotu przez kolejkę na sąsiednim wylocie.

Oba warianty powinny mieć porównywalne ograniczenia: ten sam obszar, zbliżoną liczbę pasów, te same źródła ruchu i te same rozkłady kierunków podróży. Jeżeli geometria wymaga dodatkowego pasa lub większej powierzchni, należy uwzględnić to jako osobny wariant, a nie ukryte założenie.

## Zdarzenia i zachowanie pojazdów

- pojawienie się pojazdu na wlocie,
- dojazd do końca kolejki,
- zmiana fazy sygnalizacji,
- uzyskanie prawa przejazdu,
- wjazd i zjazd ze skrzyżowania lub ronda,
- zatrzymanie i ruszenie pojazdu,
- blokowanie wylotu,
- przejście pieszego,
- konflikt lub wymuszenie pierwszeństwa,
- opuszczenie obszaru symulacji.

Pojazdy powinny mieć trasę określającą wlot i wylot, klasę (samochód osobowy, autobus, ciężarówka), reakcję kierowcy i wymagany odstęp. Na rondzie trzeba dodatkowo modelować akceptację luk oraz możliwość chwilowego zablokowania wlotu przez ruch na pierścieniu.

## Dane

Możliwe źródła:

- OpenStreetMap do geometrii istniejących skrzyżowań i rond,
- dane o natężeniu ruchu z miejskich systemów pomiarowych,
- Generalny Pomiar Ruchu oraz lokalne pomiary natężenia,
- dane z kamer lub pętli indukcyjnych, jeśli są publicznie dostępne,
- dane o wypadkach i kolizjach z otwartych rejestrów,
- dane o ruchu pieszym, jeżeli są publikowane,
- parametry projektowe i przepustowości z wytycznych inżynierii ruchu.

Przygotowanie danych:

1. wybrać istniejące skrzyżowanie i odpowiadający mu wariant ronda,
2. uprościć geometrię do grafu pasów, wlotów, wylotów i punktów konfliktu,
3. ujednolicić przedziały czasowe pomiarów,
4. rozdzielić pomiary według wlotu, kierunku i typu pojazdu,
5. oszacować rozkłady odstępów między pojazdami,
6. wyznaczyć macierz relacji origin-destination,
7. skalibrować model na jednym okresie i testować na innym.

Jeżeli dane dla obu wariantów nie istnieją, wariant alternatywny należy zbudować na podstawie geometrii i zasad ruchu, a jego parametry skalibrować na istniejącym skrzyżowaniu. Wyniki powinny jasno oddzielać obserwacje rzeczywiste od założeń projektowych.

## Teza i eksperymenty

Początkowa teza z `ideas.md` wymaga doprecyzowania, ponieważ słowo „zawsze” jest zbyt mocne:

> Rondo może mieć większą przepustowość i mniejsze opóźnienia przy małym oraz średnim, względnie równomiernym ruchu, natomiast przy dużym lub silnie asymetrycznym natężeniu sygnalizacja może zapewnić lepszą kontrolę przepływu. Istnieje punkt graniczny zależny od geometrii i struktury ruchu.

Eksperymenty:

- stopniowe zwiększanie całkowitego natężenia ruchu,
- ruch równomierny i silnie obciążony jednym wlotem,
- różny udział skrętów w lewo i w prawo,
- różny udział autobusów i ciężarówek,
- krótkie i długie cykle sygnalizacji,
- sterowanie stałoczasowe i adaptacyjne,
- rondo jedno- i dwupasowe,
- różne natężenie ruchu pieszego,
- blokowanie wylotu i nierównomierne odstępy pojazdów.

Metryki:

- przepustowość całkowita oraz osobno dla każdego wlotu,
- średnie, medianowe i maksymalne opóźnienie,
- długość i czas kolejek,
- czas przejazdu przez obszar,
- liczba zatrzymań,
- wykorzystanie pasów i wlotów,
- liczba konfliktów oraz sytuacji bliskich kolizji,
- wpływ ruchu pieszego na przepustowość,
- zajęta powierzchnia i złożoność infrastruktury jako metryki pomocnicze.

Punkt graniczny można wyznaczyć jako natężenie, przy którym przewaga jednego wariantu nad drugim zmienia znak. Trzeba raportować go osobno dla różnych proporcji kierunków, a nie podawać jednej uniwersalnej wartości.

## Środowisko i plan realizacji

Python będzie odpowiedni do przygotowania danych, kalibracji i analizy wyników. Sam model można napisać jako własną symulację krokową lub hybrydę kroków czasowych i kalendarza zdarzeń. `numpy`, `pandas` i `matplotlib` wystarczą do pierwszej wersji; `pygame` albo prosta wizualizacja webowa mogą pokazywać kolejki i zajętość pasów.

Etapy:

1. pojedynczy wlot i model kolejki,
2. czterowlotowe skrzyżowanie z sygnalizacją,
3. model ronda i akceptacji luk,
4. kalibracja na danych natężenia ruchu,
5. porównanie przy różnych macierzach origin-destination,
6. ruch pieszy, ciężarówki i blokowanie wylotów,
7. analiza punktu granicznego oraz niepewności wyników.

Do tego projektu ML nie jest konieczne. Można jednak dodać agenta sterującego sygnalizacją adaptacyjną i porównać go ze stałoczasowym oraz klasycznym sterowaniem opartym na długości kolejek.
