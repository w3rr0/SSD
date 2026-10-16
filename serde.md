#Dyskretno-zdarzeniowa symulacja autonomicznej regulacji rytmu serca

## Streszczenie

Projekt zakłada symulację pracy naturalnego rozrusznika serca, który odpowiada za częstotliwość uderzeń tętna. Na rozrusznik wpływają dwa przeciwstawne stany organizmu:
1. Stres: układ nerwowy wysyła sygnały pobudzające (adrenalinę i pokrewne substancje), które nakazują sercu przyspieszyć.
2. Odpoczynek: układ nerwowy wysyła sygnały uspokajające, które obniżają puls.

Aby sygnał zadziałał, substancje muszą połączyć się z wolnymi receptorami (punktami odbioru sygnału) na powierzchni komórek serca. Liczba tych receptorów jest ograniczona. W symulacji wprowadzamy również lek z grupy beta-blokerów. Cząsteczki leku zajmują receptory odpowiedzialne za stres, fizycznie blokując do nich dostęp, ale same nie wywołują przyspieszenia tętna.

Model bada, jak podanie leku chroni serce przed niebezpiecznie wysokim tętnem podczas silnego stresu, jednocześnie sprawdzając, czy organizm zachowuje zdolność do normalnego uspokajania rytmu w spoczynku.

## Model systemu

### Elementy
- **Rozrusznik serca:** wewnętrzny licznik, który zbiera ładunek elektryczny. Po osiągnięciu określonego poziomu progowego następuje uderzenie serca, licznik się zeruje i cykl zaczyna się od nowa.
- **Pula receptorów stresu:** ograniczona liczba miejsc na komórkach, z którymi mogą łączyć się cząsteczki stresu lub cząsteczki leku.
- **Pula receptorów odpoczynku:** oddzielna pula miejsc, z którymi łączą się substancje spowalniające rytm serca.
- **Generator stresu:** proces, który w momentach napięcia wysyła określoną liczbę cząsteczek przyspieszających tętno.
- **Generator odpoczynku:** proces, który regularnie wysyła porcje cząsteczek uspokajających (ich intensywność zmienia się m.in. w rytm spokojnego oddechu).
- **Moduł leku (Beta-bloker):** pula cząsteczek leku, które po przyjęciu dawki trafiają do otoczenia komórek i blokują receptory stresu na określony czas.
- **Mechanizm oczyszczania:** proces usuwania wolnych i odłączonych cząsteczek z otoczenia. Cząsteczki odpoczynku znikają niemal natychmiast, natomiast cząsteczki stresu i leku utrzymują się znacznie dłużej.

### Stany pojedynczego receptora stresu
`wolny` -> `połączony z cząsteczką stresu` (tętno przyspiesza) -> `odłączenie cząsteczki` -> `wolny`.

Gdy podano lek:  
`wolny` -> `zablokowany przez lek` (stan nieaktywny, brak reakcji, stres nie może się połączyć) -> `odłączenie leku` -> `wolny`.

### Stany rozrusznika serca
`spoczynkowe ładowanie` -> `przyspieszone ładowanie (pod wpływem stresu)` -> `spowolnione ładowanie (pod wpływem odpoczynku)` -> `osiągnięcie progu (uderzenie serca)` -> `krótka pauza powrotna (brak reakcji na bodźce)` -> `nowy cykl`.

### Stany awaryjne do wykrywania
`niebezpieczna tachykardia` (zbyt wysoki puls pod wpływem stresu) oraz `nadmierna bradykardia` (zbyt mocne spowolnienie akcji serca).

### Zdarzenia

- nadejście impulsu stresu (wyrzut cząsteczek pobudzających),
- nadejście impulsu odpoczynku (wyrzut cząsteczek uspokajających),
- przyjęcie dawki leku (pojawienie się cząsteczek beta-blokera),
- połączenie cząsteczki stresu z wolnym receptorem,
- zablokowanie receptora przez cząsteczkę leku,
- odłączenie się cząsteczki stresu lub leku od receptora,
- naturalne usunięcie wolnej cząsteczki z otoczenia,
- napełnienie licznika rozrusznika i wygenerowanie uderzenia serca (`UderzenieSerca`),
- zmiana fazy oddechu (wdech / wydech — chwilowa zmiana siły odpoczynku),
- nagły skok poziomu stresu (np. symulacja nagłego przestrachu lub wysiłku).

## Sterowanie i warianty

1. **Spoczynek (Stan bazowy):** brak leku, niska intensywność stresu, naturalne tętno spoczynkowe (około 60–75 uderzeń na minutę).
2. **Ostry stres:** nagły i silny wzrost liczby impulsów stresu bez obecności leku — serce osiąga maksymalne tętno.
3. **Niska dawka leku:** zablokowanie około 25% dostępnych receptorów stresu.
4. **Wysoka dawka leku:** zablokowanie około 60–75% receptorów stresu.
5. **Konkurencja cząsteczek:** sytuacja, w której bardzo duża dawka stresu próbuje połączyć się z nielicznymi wolnymi receptorami przy obecnym leku.
6. **Sprzężenie regulacyjne organizmu:** jeśli średnie tętno z ostatnich sekund jest zbyt wysokie, organizm automatycznie zwiększa liczbę impulsów odpoczynku, by ustabilizować rytm.

Ograniczenia: liczba jednocześnie zajętych receptorów nie może przekraczać ich całkowitej puli, a serce po każdym uderzeniu wymaga ułamka sekundy przerwy przed wygenerowaniem kolejnego skurczu.

## Dane

Możliwe źródła:

- **BioNumbers (bionumbers.hms.harvard.edu):** rzeczywista liczba receptorów na pojedynczej komórce serca oraz średni czas, przez jaki cząsteczki pozostają z nimi połączone.
- **PubChem / bazy farmakologiczne:** czas działania i siła wiązania popularnych leków blokujących (np. metoprolol, propranolol).
- **PhysioNet (MIT-BIH Normal Sinus Rhythm Database):** publiczne, rzeczywiste zapisy odstępów między uderzeniami serca u zdrowych ludzi w spoczynku.
- **PhysioNet (Stress Recognition in Automobile Drivers):** rzeczywiste serie pomiarów tętna u osób poddanych nagłemu stresowi.
- **Syntetyczne profile zdarzeń:** generowane komputerowo scenariusze nagłych zmian poziomu stresu.

Przygotowanie danych:

1. wyodrębnienie czystych odstępów czasu między kolejnymi uderzeniami serca z plików PhysioNet,
2. usunięcie błędów pomiarowych i zakłóceń aparatury,
3. przeliczenie czasów reakcji chemicznych z literatury na milisekundy używane w symulatorze,
4. obliczenie referencyjnych wskaźników zmienności rytmu (jak bardzo puls naturalnie faluje w spoczynku i w stresie),
5. przygotowanie powtarzalnych scenariuszy testowych: spoczynek, nagły atak paniki, przyjęcie leku, długotrwały wysiłek.

## Teza i eksperymenty

**Teza:** dynamiczne ustalanie priorytetów na podstawie bieżących opóźnień, zajętości infrastruktury i ryzyka utraty przesiadek ogranicza całkowite opóźnienie oraz jego propagację skuteczniej niż stałe priorytety przypisane typom pociągów.

Eksperymenty:

- wzrost natężenia ruchu na wspólnym odcinku,
- opóźnienie jednego pociągu na początku symulacji,
- zamknięcie pojedynczego toru,
- awaria rozjazdu lub stacji,
- różny udział pociągów towarowych,
- różne bufory czasowe w rozkładzie,
- różne poziomy priorytetu i zasady obsługi przesiadek,
- porównanie małej i gęstej sieci.

Metryki:

- średnie, medianowe i maksymalne opóźnienie,
- opóźnienie na końcu trasy względem opóźnienia początkowego,
- liczba utraconych przesiadek,
- liczba pociągów przepuszczonych przez sieć,
- czas oczekiwania przed odcinkami i na stacjach,
- wykorzystanie torów, stacji i rozjazdów,
- punktualność osobno dla pociągów pasażerskich i towarowych,
- nierówność kosztu opóźnień między grupami pociągów.

## Środowisko i plan realizacji

Projekt zostanie zrealizowany w języku Python. Silnik kolejki zdarzeń zostanie napisany od zera przy użyciu standardowej kolejki priorytetowej (`heapq`), bez zewnętrznych bibliotek symulacyjnych. Do operacji na danych i porównania z bazą PhysioNet posłużą `numpy` oraz `scipy`, a do wykresów tętna i stanów receptorów — `matplotlib`.

### Etapy:

1. **Silnik zdarzeń i podstawowy rozrusznik:** kolejka zdarzeń sterująca czasem, generator stałego tętna bazowego.
2. **Receptory i sygnały:** dodanie puli receptorów; impulsy stresu przyspieszają kolejny skurcz, impulsy odpoczynku go opóźniają.
3. **Stochastyczne generatory:** losowe pojawianie się impulsów stresu i odpoczynku imitujące działanie prawdziwego organizmu.
4. **Moduł leku:** wprowadzenie cząsteczek blokujących receptory stresu na określony czas.
5. **Kalibracja z danymi PhysioNet:** dopasowanie parametrów symulatora do rzeczywistych wykresów tętna człowieka.
6. **Eksperymenty i analiza:** symulacja sytuacji stresowych z różnymi dawkami leku, wyliczenie metryk i stworzenie wykresów wynikowych.

Zaletą dyskretno-zdarzeniowego podejścia jest to, że program nie musi mozolnie przeliczać każdej milisekundy. Jeśli cząsteczka leku blokuje receptor na 30 minut, symulator od razu przeskakuje do kolejnego zdarzenia w kolejce, co pozwala na błyskawiczne symulowanie wielu godzin pracy serca.
