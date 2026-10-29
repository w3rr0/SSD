# Adaptacja kierowców do deterministycznych pojazdów autonomicznych na rondzie

## Streszczenie

Projekt bada, jak zmienia się zachowanie kierowców ludzkich po wprowadzeniu do ruchu pojazdów autonomicznych (AV), których sposób jazdy jest oparty na jawnym i deterministycznym algorytmie. Środowiskiem eksperymentu jest jedno konkretne rondo odtworzone na podstawie rzeczywistych trajektorii pojazdów.

Najpierw model kierowców zostanie skalibrowany na danych z rzeczywistego ruchu. Następnie kierowcy będą uczyć się przejazdu przez rondo bez pojazdów autonomicznych. W kolejnej fazie część pojazdów zostanie zastąpiona pojazdami AV. Kierowcy będą mogli aktualizować swoje zachowanie na podstawie obserwowanych interakcji, a więc nauczyć się, że określony typ pojazdu:

- utrzymuje większy odstęp,
- później wjeżdża na rondo,
- rezygnuje ze zmiany pasa w niepewnej sytuacji,
- hamuje, gdy inny pojazd wjeżdża przed niego,
- konsekwentnie ustępuje w określonych sytuacjach.

Głównym pytaniem jest, czy kierowcy zaczną strategicznie wykorzystywać te reguły, aby skrócić własny czas przejazdu. Projekt nie zakłada z góry, że kierowcy będą agresywni. Agresywne lub oportunistyczne zachowania mają pojawić się jako możliwy skutek optymalizacji funkcji nagrody i uczenia się z doświadczenia.

## Problem badawczy

Klasyczne porównanie ruchu z pojazdami autonomicznymi i bez nich zwykle zakłada, że kierowcy ludzcy zachowują się tak samo w obu scenariuszach. To może być nierealistyczne. Jeżeli zachowanie AV jest przewidywalne, kierowca może nauczyć się, że określone działanie prawie zawsze powoduje ustąpienie pojazdu autonomicznego.

Przykładowa sekwencja:

1. AV utrzymuje duży odstęp przed wjazdem na rondo.
2. Kierowca ludzki wjeżdża w powstałą lukę.
3. AV hamuje, aby zachować bezpieczny odstęp.
4. Kierowca skraca swój czas przejazdu.
5. Kierowca zapamiętuje, że ten manewr jest skuteczny.
6. W kolejnych epizodach częściej próbuje podobnych manewrów.
7. Inni kierowcy mogą zauważyć skuteczność tej strategii i również zacząć ją stosować.

W pojedynczej interakcji zachowanie AV może poprawiać bezpieczeństwo, ale w dłuższym okresie przewidywalność może stworzyć zachętę do wykorzystywania jego ograniczeń. To sprzężenie zwrotne jest właściwym przedmiotem symulacji.

## Główne pytanie badawcze

> Czy kierowcy nauczeni na podstawie rzeczywistego ruchu zaczną wykorzystywać przewidywalne zachowanie deterministycznych pojazdów autonomicznych, jeżeli będą optymalizować przede wszystkim własny czas przejazdu?

## Pytania szczegółowe

1. Jak szybko kierowca może nauczyć się reakcji określonego typu AV?
2. Czy strategiczne zachowanie pojawia się przy każdym udziale AV, czy tylko w określonym zakresie?
3. Czy bardziej defensywny AV jest częściej wykorzystywany przez kierowców?
4. Czy kierowcy uczą się wyłącznie na podstawie własnych doświadczeń, czy również przez obserwowanie innych?
5. Czy douczanie kierowców zmienia przepustowość ronda i rozkład czasów przejazdu?
6. Czy próba skrócenia czasu przejazdu przez pojedynczego kierowcę powoduje koszt dla wielu pozostałych uczestników?
7. Czy zwiększenie asertywności AV ogranicza wymuszanie pierwszeństwa bez pogorszenia bezpieczeństwa?
8. Czy algorytm AV, który jest deterministyczny, ale mniej przewidywalny na poziomie szczegółów, zmienia zachowania kierowców?

## Zakres środowiska

Projekt nie powinien zaczynać się od całej sieci miejskiej. Należy wybrać jedno rondo, które:

- ma co najmniej dwa pasy na części lub całości pierścienia,
- ma wystarczające natężenie ruchu,
- ma obserwowalne zmiany pasa i włączanie się do ruchu,
- posiada dane trajektorii albo nagrania możliwe do przetworzenia,
- ma geometrię, którą można wiarygodnie odtworzyć.

Na początku warto rozważyć rondo o prostej geometrii, bez sygnalizacji na wlotach. Dzięki temu główny problem będzie dotyczył akceptacji luk, zmiany pasa, ustępowania i wzajemnego uczenia się, a nie jednocześnie świateł, pieszych i wielu skrzyżowań.

Nazwa i lokalizacja ronda powinny zostać wybrane dopiero po sprawdzeniu jakości danych. Jeżeli dane nie pozwolą na identyfikację konkretnej lokalizacji, można użyć publicznego zbioru z jednym określonym rondem lub skrzyżowaniem i zachować jego identyfikator w konfiguracji projektu.

## Dane rzeczywiste

### Możliwe źródła

- nagrania z kamer drogowych, o ile ich wykorzystanie jest zgodne z prawem i warunkami licencji,
- publiczne zbiory trajektorii pojazdów na skrzyżowaniach i rondach,
- inD Intersection Dataset,
- NGSIM, jeżeli wybrany fragment odpowiada badanemu typowi geometrii,
- highD jako źródło zachowania na drogach wielopasmowych, choć niekoniecznie ronda,
- OpenStreetMap do geometrii i liczby pasów,
- lokalne pomiary natężenia ruchu,
- dane pogodowe dla rozdzielenia warunków normalnych i pogorszonych.

Jeżeli projekt ma dotyczyć konkretnego polskiego ronda, najlepszym rozwiązaniem byłoby uzyskanie nagrania z jednego punktu obserwacji i ręczne lub półautomatyczne oznaczenie trajektorii. Publiczny zbiór zagraniczny może być łatwiejszy technicznie, ale wtedy wnioski dotyczą badanego typu ronda, a nie polskich kierowców.

### Informacje wyznaczane z trajektorii

Z każdego pojazdu należy, o ile dane na to pozwalają, wyznaczyć:

- pozycję w kolejnych chwilach,
- prędkość,
- przyspieszenie,
- odstęp od poprzedzającego pojazdu,
- czas wjazdu na rondo,
- czas opuszczenia ronda,
- wlot i wylot,
- pas zajmowany w kolejnych momentach,
- zmianę pasa,
- czas oczekiwania przed wjazdem,
- gwałtowne hamowanie,
- minimalny odstęp czasowy i przestrzenny.

Nie należy utożsamiać każdej krótkiej zmiany toru jazdy z intencjonalnym wymuszeniem. Dane powinny rozróżniać:

- zwykłe podążanie za ruchem,
- naturalne włączenie się przy wystarczającej luce,
- zmianę pasa wymuszoną geometrią,
- zmianę pasa zakończoną bardzo małą luką,
- gwałtowną reakcję pojazdu z pierwszeństwem,
- przypadek niejednoznaczny.

### Czyszczenie danych

1. Usunąć obserwacje z utratą pojazdu na dłuższym odcinku.
2. Ujednolicić częstotliwość próbkowania.
3. Wygładzić szum pozycji, ale nie usuwać rzeczywistych hamowań.
4. Sprawdzić, czy prędkości i przyspieszenia pozostają fizycznie możliwe.
5. Zmapować współrzędne na pasy, wloty i wyloty ronda.
6. Uzupełnić krótkie braki tylko wtedy, gdy interpolacja nie zmieni decyzji kierowcy.
7. Odrzucić epizody, w których nie można ustalić całej interakcji.
8. Podzielić dane na kalibracyjne, walidacyjne i testowe według czasu nagrania, a nie losowo po pojedynczych klatkach.

Podział czasowy jest ważny, ponieważ losowe rozdzielenie klatek z tego samego przejazdu mogłoby sztucznie zawyżyć jakość walidacji.

## Odtworzenie ronda

Model środowiska powinien zawierać:

- geometrię wlotów i wylotów,
- pierścień ronda,
- liczbę pasów,
- ograniczenia prędkości,
- regułę pierwszeństwa,
- strefy, w których można zmieniać pas,
- strefy, w których zmiana pasa jest zabroniona lub ryzykowna,
- parametry widoczności,
- źródła i natężenia napływu pojazdów,
- rozkład relacji wlot-wylot.

Pojedynczy krok symulacji może mieć długość 0,1 sekundy. Taki krok jest wystarczający do obserwacji reakcji i odstępów, a nie powinien powodować nadmiernego kosztu obliczeniowego dla jednego ronda. Wydarzenia o większej skali, takie jak pojawienie się pojazdu, można obsługiwać przez generator zdarzeń, ale decyzje ruchowe powinny być aktualizowane krokowo.

## Stany pojazdu

Pojazd może znajdować się w stanie:

`oczekuje przed wlotem -> akceptuje lukę -> wjeżdża -> jedzie po pierścieniu -> zmienia pas -> oczekuje na zjazd -> opuszcza rondo`.

Dodatkowe stany:

- `hamuje przed wjazdem`,
- `hamuje z powodu innego pojazdu`,
- `wykonuje wymuszoną zmianę pasa`,
- `zatrzymany przez konflikt`,
- `sytuacja bliska kolizji`,
- `kolizja`.

Stan nie powinien być jedynym źródłem informacji o zachowaniu. Należy przechowywać również ciągłe wartości, takie jak prędkość, odstęp, przyspieszenie, położenie i prawdopodobieństwo akceptacji luki.

## Zdarzenia dyskretne

- pojawienie się pojazdu na wlocie,
- wykrycie pojazdu na rondzie,
- rozpoczęcie oceny luki,
- akceptacja lub odrzucenie luki,
- wjazd na rondo,
- rozpoczęcie zmiany pasa,
- zakończenie zmiany pasa,
- wymuszenie pierwszeństwa,
- awaryjne hamowanie,
- konflikt torów jazdy,
- opuszczenie ronda,
- aktualizacja wiedzy kierowcy,
- zmiana parametrów kontrolera AV.

Wymuszenie pierwszeństwa nie powinno być oznaczane wyłącznie na podstawie tego, że jeden pojazd znalazł się przed drugim. Powinno wynikać z połączenia cech, na przykład:

- wejście w lukę mniejszą niż minimalna luka modelu bazowego,
- reakcja hamowania pojazdu, który miał pierwszeństwo,
- skrócenie odstępu poniżej bezpiecznego progu,
- rozpoczęcie manewru mimo przewidywanego konfliktu torów.

## Populacja kierowców ludzkich

Kierowcy są agentami, ale nie powinni być identyczni. Każdy agent może mieć:

- czas reakcji,
- preferowany odstęp,
- maksymalne przyspieszenie,
- maksymalne hamowanie,
- tolerancję ryzyka,
- preferencję pasa,
- skłonność do zmiany pasa,
- tolerancję oczekiwania przed wjazdem,
- dokładność obserwacji,
- pamięć doświadczeń,
- tempo uczenia,
- skłonność do uczenia społecznego.

Początkowe rozkłady tych parametrów powinny wynikać z danych rzeczywistych. Nie należy od razu dzielić kierowców na arbitralne klasy „dobry”, „zły” i „agresywny”, jeżeli dane umożliwiają dopasowanie parametrów ciągłych.

Można jednak użyć klas pomocniczych do analizy:

- ostrożny,
- przeciętny,
- zdecydowany,
- strategiczny po nauczeniu się AV.

Ostatnia klasa nie powinna być ustawiana ręcznie w głównym eksperymencie. Powinna powstać jako wynik procesu uczenia. Ręczne ustawienie jej udziału może służyć wyłącznie do testu kontrolnego.

## Mechanizm uczenia kierowców

### Decyzje kierowcy

Agent może wybierać:

- czy zaakceptować obserwowaną lukę,
- czy przyspieszyć przed wjazdem,
- czy rozpocząć zmianę pasa,
- czy kontynuować zmianę pasa,
- czy odpuścić manewr,
- jaki odstęp utrzymywać,
- czy skorzystać z luki utworzonej przez hamujący AV.

Nie należy pozwalać agentowi bezpośrednio wybierać dowolnego przyspieszenia bez ograniczeń fizycznych. Akcja musi przejść przez model pojazdu, ograniczenia przyczepności i minimalny czas reakcji.

### Faza 1: nauka podstawowego ruchu

W pierwszej fazie nie ma AV. Kierowcy uczą się przejazdu przez rondo przy rozkładzie ruchu zgodnym z danymi rzeczywistymi.

Cel:

- uzyskanie stabilnego przejazdu przez rondo,
- odtworzenie rozkładu czasów przejazdu,
- odtworzenie rozkładu akceptowanych luk,
- odtworzenie częstości zmian pasa,
- ograniczenie liczby niebezpiecznych sytuacji.

Ta faza nie ma odpowiadać na główne pytanie badawcze. Jest etapem kalibracji populacji i sprawdzenia, czy agenci potrafią odtworzyć bazowe zachowanie.

### Faza 2: wprowadzenie AV

Do części epizodów wprowadza się określony udział AV, na przykład:

- 5%,
- 10%,
- 25%,
- 50%.

Kierowcy nie otrzymują wprost informacji o kodzie kontrolera. Poznają jego zachowanie przez obserwacje interakcji. Można porównać sytuację, w której typ AV jest widoczny, z sytuacją, w której kierowca musi go rozpoznać na podstawie zachowania.

### Faza 3: douczanie

Po każdym epizodzie kierowca aktualizuje przekonania dotyczące AV. Przykładowe przekonania:

- prawdopodobieństwo, że AV ustąpi przy zmianie pasa,
- prawdopodobieństwo, że AV zahamuje przy wjeździe w lukę,
- przewidywany minimalny odstęp AV,
- przewidywany czas reakcji AV,
- ryzyko nieudanego wymuszenia.

Można zastosować prosty model aktualizacji bayesowskiej, uczenie Q albo parametr aktualizowany metodą delta-rule. Nie jest konieczna sieć neuronowa. Ważne, aby mechanizm był interpretowalny i można było obserwować, czego agent się nauczył.

Przykład aktualizacji:

```text
przekonanie_nowe =
    przekonanie_stare
    + tempo_uczenia * (wynik_interakcji - przekonanie_stare)
```

Jeżeli AV ustąpił, wynik interakcji może zwiększyć przekonanie, że podobny manewr będzie skuteczny w przyszłości. Jeżeli AV nie ustąpił i kierowca musiał gwałtownie hamować, przekonanie powinno się zmniejszyć.

### Uczenie społeczne

W wariancie rozszerzonym kierowcy mogą uczyć się nie tylko z własnych interakcji. Mogą również obserwować:

- że inny pojazd skutecznie wjechał przed AV,
- że manewr zakończył się gwałtownym hamowaniem,
- że określony typ AV reaguje inaczej,
- że inny kierowca poniósł koszt ryzykownej decyzji.

Tempo uczenia społecznego powinno być osobnym parametrem. Pozwoli to sprawdzić, czy strategiczne zachowanie rozprzestrzenia się lokalnie, czy pozostaje cechą kilku agentów.

## Deterministyczny kontroler AV

Pojazdy autonomiczne nie korzystają z sieci neuronowej. Ich decyzje mają być jawne, powtarzalne i możliwe do przeanalizowania.

### Warstwa podążania

Można zastosować uproszczony model IDM albo własną regułę, w której prędkość zależy od:

- prędkości pojazdu poprzedzającego,
- odległości,
- prędkości względnej,
- żądanego odstępu,
- maksymalnego przyspieszenia,
- maksymalnego hamowania.

### Warstwa zmiany pasa

AV może rozpocząć zmianę pasa tylko wtedy, gdy:

- luka z przodu jest większa od progu,
- luka z tyłu jest większa od progu,
- przewidywana trajektoria nie przecina się z innym pojazdem,
- manewr pozostaje możliwy do przerwania,
- pojazd nie znajduje się w strefie zabronionej.

### Warstwa akceptacji luki

Kontroler może mieć jawne parametry:

- minimalna luka czasowa,
- minimalny odstęp przestrzenny,
- czas obserwacji,
- margines bezpieczeństwa,
- tolerowane przyspieszenie pojazdu z tyłu,
- poziom asertywności.

### Warianty kontrolera

1. **Defensywny** — duży margines bezpieczeństwa i częste rezygnowanie z manewru.
2. **Bazowy** — parametry dopasowane do założonego bezpiecznego stylu jazdy.
3. **Asertywny** — korzystanie z pierwszeństwa, gdy warunki bezpieczeństwa są spełnione.
4. **Adaptacyjny regułowo** — zmiana parametrów na podstawie częstości wymuszeń, bez użycia sieci neuronowej.
5. **Losowo zmienny** — niewielka kontrolowana zmienność decyzji przy zachowaniu twardych ograniczeń bezpieczeństwa.

Wariant losowy nie powinien być przedstawiany jako „bardziej inteligentny”. Jest eksperymentem sprawdzającym, czy mniejsza przewidywalność ogranicza strategiczne wykorzystywanie, oraz czy koszt tej zmiany nie pojawia się w postaci większej liczby nieoczekiwanych reakcji.

## Funkcja nagrody

### Wersja bazowa

W pierwszym eksperymencie można zdefiniować nagrodę kierowcy jako:

```text
R = - czas_przejazdu
```

Pozwoli to sprawdzić, jakie zachowania wyłonią się, gdy agent optymalizuje wyłącznie własny interes. Taki eksperyment jest ważny diagnostycznie, ale nie powinien być traktowany jako realistyczny model bez dodatkowych ograniczeń.

### Wersja z ograniczeniami bezpieczeństwa

Lepsza funkcja nagrody może mieć postać:

```text
R =
    - w_czas * czas_przejazdu
    - w_hamowanie * gwałtowne_hamowania
    - w_odstep * naruszenia_minimalnego_odstepu
    - w_zmiana * nieudane_zmiany_pasa
    - w_kolizja * kolizje
```

Kara za kolizję powinna być znacznie większa od pozostałych składników. Warto jednak rozważyć również twardy warunek bezpieczeństwa, ponieważ sama kara może być przez agenta „opłacalna”, jeżeli krótszy czas przejazdu równoważy ryzyko.

### Dwie interpretacje funkcji nagrody

1. **Interes własny** — kierowca optymalizuje własny czas i ponosi koszt własnego ryzyka.
2. **Interes ograniczony bezpieczeństwem** — kierowca optymalizuje czas, ale naruszenia bezpieczeństwa są niedopuszczalne albo bardzo kosztowne.

Porównanie tych wersji pokaże, czy strategiczne wykorzystywanie AV jest skutkiem samej adaptacji, czy przede wszystkim źle zdefiniowanego celu.

Nie należy traktować wysokiej nagrody jako dowodu, że zachowanie jest realistyczne. Nagroda jest narzędziem modelowania hipotezy, a nie pomiarem ludzkich preferencji.

## Teza główna

> Wprowadzenie deterministycznych i przewidywalnych pojazdów autonomicznych do ruchu na rondzie może początkowo poprawić bezpieczeństwo, lecz po douczeniu kierowców ludzkich część tej korzyści zostanie utracona, ponieważ kierowcy zaczną wykorzystywać przewidywalne decyzje AV do skracania własnego czasu przejazdu.

## Hipotezy

1. Po wprowadzeniu AV liczba strategicznych prób jest początkowo mała, a rośnie wraz z liczbą epizodów.
2. Defensywny AV jest wykorzystywany częściej niż AV bazowy i asertywny.
3. Przy małym udziale AV interakcje są zbyt rzadkie, aby populacja szybko się nauczyła.
4. Przy bardzo dużym udziale AV kierowcy strategiczni mogą mieć mniej okazji do wykorzystywania pojedynczych pojazdów, ale koszt ich działań może dotyczyć większej części ruchu.
5. Największa liczba interakcji i potencjalna destabilizacja mogą wystąpić przy pośrednim udziale AV.
6. Uczenie społeczne przyspiesza rozprzestrzenianie strategii, ale może również przekazywać błędne przekonania.
7. Zwiększenie asertywności AV zmniejsza skuteczność wymuszeń, lecz może podnieść liczbę sytuacji z małym odstępem.
8. Najlepszy kompromis nie musi odpowiadać kontrolerowi o najwyższej przepustowości w pierwszych epizodach.

## Plan eksperymentów

### Eksperyment 0: walidacja ruchu bazowego

Uruchomić symulację bez AV i porównać ją z danymi rzeczywistymi.

Porównać:

- rozkład czasów przejazdu,
- rozkład prędkości,
- odstępy,
- liczbę zmian pasa,
- czas oczekiwania przed wjazdem,
- liczbę gwałtownych hamowań,
- proporcje relacji wlot-wylot.

Jeżeli model nie odtwarza tych właściwości, nie należy przechodzić do wniosków o zachowaniu po wprowadzeniu AV.

### Eksperyment 1: nauka bez AV

Kierowcy uczą się ronda bez pojazdów autonomicznych. Celem jest sprawdzenie, czy ich zachowanie stabilizuje się oraz czy wyniki nie zależą wyłącznie od początkowych parametrów.

### Eksperyment 2: natychmiastowe wprowadzenie AV

Porównać 5%, 10%, 25% i 50% AV bez douczania kierowców. Jest to stan krótkoterminowy, który pokazuje efekt samej zmiany składu ruchu.

### Eksperyment 3: douczanie indywidualne

Kierowcy uczą się wyłącznie z własnych interakcji. Rejestrować, po ilu epizodach pojawia się zmiana zachowania i jak duże są różnice między kierowcami.

### Eksperyment 4: douczanie społeczne

Dodać możliwość obserwowania innych pojazdów. Porównać tempo rozpowszechniania strategii i odporność wyników na pojedyncze przypadkowe sukcesy.

### Eksperyment 5: różne kontrolery AV

Dla tej samej populacji kierowców porównać kontroler defensywny, bazowy i asertywny. Parametry ruchu i natężenie powinny pozostać takie same.

### Eksperyment 6: różne funkcje nagrody

Porównać optymalizację samego czasu z optymalizacją czasu ograniczoną bezpieczeństwem. Nie wolno interpretować tych eksperymentów jako porównania „dobrych” i „złych” ludzi; porównywana jest konsekwencja różnych założeń modelu.

### Eksperyment 7: odporność na zmianę parametrów

Po wyuczeniu kierowców zmienić jeden parametr AV:

- minimalny odstęp,
- próg akceptacji luki,
- czas reakcji,
- poziom asertywności.

Sprawdzić, czy kierowcy nadal stosują poprzednią strategię i jak długo trwa ponowne douczenie.

## Metryki

### Czas i przepustowość

- średni, medianowy i percentylowy czas przejazdu,
- czas oczekiwania przed wjazdem,
- długość kolejek,
- liczba pojazdów opuszczających rondo w jednostce czasu,
- udział pojazdów, których czas przejazdu przekracza ustalony próg.

### Bezpieczeństwo

- liczba kolizji,
- liczba sytuacji bliskich kolizji,
- minimalny odstęp przestrzenny,
- minimalny odstęp czasowy,
- liczba gwałtownych hamowań,
- maksymalne opóźnienie reakcji,
- liczba przerwanych zmian pasa.

### Strategiczne zachowanie

- liczba prób wjazdu w lukę przy AV,
- odsetek prób zakończonych sukcesem,
- średni zysk czasu kierowcy,
- dodatkowy czas innych pojazdów po manewrze,
- liczba prób na kierowcę i epizod,
- czas do pierwszego strategicznego zachowania,
- czas do stabilizacji strategii,
- liczba kierowców, którzy zmienili politykę.

### Efekt populacyjny

- nierówność czasów przejazdu,
- średni koszt ponoszony przez kierowców niestosujących strategii,
- liczba pojazdów dotkniętych pojedynczym wymuszeniem,
- udział ruchu, który staje się niestabilny,
- różnica między krótkoterminowym i długoterminowym wynikiem.

## Analiza wyników

Najważniejsze jest rozdzielenie trzech okresów:

1. **przed adaptacją** — kierowcy nie znają jeszcze AV,
2. **w trakcie adaptacji** — zmieniają przekonania i zachowania,
3. **po adaptacji** — populacja osiąga stan względnie stabilny albo stale oscyluje.

Nie należy ograniczać się do średniej końcowej. Dwa systemy mogą mieć taki sam średni czas przejazdu po 1000 epizodów, ale różnić się:

- szybkością pogorszenia,
- liczbą niebezpiecznych epizodów,
- rozrzutem wyników,
- stabilnością zachowania,
- wrażliwością na zmianę parametrów AV.

Warto sporządzić:

- wykresy metryk w funkcji numeru epizodu,
- wykresy względem udziału AV,
- wykresy względem odsetka kierowców uczących się społecznie,
- mapy fazowe udział AV–tempo uczenia,
- rozkłady wyników z wielu powtórzeń,
- porównanie krótkoterminowego i długoterminowego efektu.

## Walidacja i kontrola poprawności

### Walidacja ruchu bazowego

Model powinien odtwarzać podstawowe statystyki rzeczywistych przejazdów. Nie musi odtworzyć każdej trajektorii, ale musi być zgodny z rozkładami i zależnościami istotnymi dla badanego problemu.

### Testy jednostkowe

Należy osobno sprawdzić:

- czy pojazd nie przekracza ograniczeń przyspieszenia,
- czy AV nie wjeżdża w lukę poniżej twardego progu,
- czy pojazd poprawnie opuszcza rondo,
- czy kolizja jest wykrywana niezależnie od kolejności aktualizacji,
- czy aktualizacja przekonania kierowcy ma prawidłowy znak,
- czy zmiana parametru AV wpływa tylko na przewidziane reguły.

### Testy kontrolne

Warto uruchomić warianty:

- bez uczenia,
- bez AV,
- z kierowcami losowymi,
- z kierowcami o stałej polityce,
- z jednym AV,
- z identycznymi ziarnami losowymi dla porównywanych kontrolerów.

Jeżeli efekt pojawia się tylko w jednej implementacji albo znika po zmianie ziarna, nie powinien być przedstawiany jako stabilny wynik.

## Ograniczenia i ryzyka

### Dane nie obserwują intencji

Z nagrania można zobaczyć, że pojazd wjechał w lukę i drugi pojazd zahamował, ale nie można bezpośrednio udowodnić, że kierowca znał typ pojazdu ani że celowo go wykorzystał. Dlatego w projekcie należy mówić o **strategicznym zachowaniu wyłonionym w modelu**, a nie o bezpośrednim pomiarze intencji prawdziwych kierowców.

### AV nie jest rzeczywistym AV

Deterministyczny kontroler reprezentuje określony model hipotetycznego pojazdu autonomicznego. Wyniki zależą od jego parametrów i nie powinny być uogólniane na wszystkie istniejące systemy.

### Funkcja nagrody może generować sztuczne zachowania

Jeżeli kara za ryzyko jest za mała, agent może nauczyć się zachowań, których człowiek nie wykonałby w rzeczywistości. Dlatego trzeba prezentować wyniki dla kilku funkcji nagrody i badać wrażliwość na wagi.

### Pojedyncze rondo nie opisuje miasta

Wynik dotyczy geometrii, natężenia i parametrów badanego ronda. To ograniczenie jest celowe: projekt ma odpowiadać na precyzyjne pytanie, a nie udawać uniwersalnego modelu całego ruchu.

### Ryzyko pomylenia nauki z degradacją modelu

Jeżeli kierowcy zaczynają powodować kolizje wyłącznie dlatego, że mogą otrzymać wysoką nagrodę, może to oznaczać źle ustawione ograniczenia, a nie interesujące odkrycie. Każdy wynik powinien zostać sprawdzony w wariancie z twardymi ograniczeniami bezpieczeństwa.

## Środowisko i architektura

Python jest odpowiedni do przygotowania danych, prototypu i analizy. Proponowane komponenty:

- `pandas` — czyszczenie i agregacja trajektorii,
- `numpy` — obliczenia numeryczne,
- `scikit-learn` — dopasowanie rozkładów i walidacja pomocnicza,
- `matplotlib` lub `seaborn` — analiza wyników,
- `pygame` albo wizualizacja webowa — podgląd ronda,
- własny silnik krokowy — kontrola nad fizyką i zdarzeniami.

Biblioteka RL może zostać dodana dopiero po zbudowaniu działającego środowiska. Nie należy zaczynać od gotowego agenta, ponieważ najważniejsze są poprawne stany, akcje, ograniczenia oraz pomiar interakcji. Algorytm uczenia można zaimplementować samodzielnie dla prostego Q-learningu lub użyć biblioteki dopiero jako wariantu porównawczego.

W przypadku bardzo wielu powtórzeń logikę aktualizacji ruchu można później przenieść do C++, ale nie jest to konieczne dla jednego ronda.

## Plan realizacji

1. Wybrać rondo i sprawdzić legalność oraz jakość danych.
2. Przygotować geometrię i parser trajektorii.
3. Zbudować model krokowy bez uczenia.
4. Skalibrować parametry ruchu bazowego.
5. Zweryfikować model na osobnym fragmencie danych.
6. Dodać deterministyczny kontroler AV.
7. Dodać kierowców z pamięcią i aktualizacją przekonań.
8. Przeprowadzić fazę nauki bez AV.
9. Wprowadzić AV i wykonać fazę douczania.
10. Porównać uczenie indywidualne i społeczne.
11. Zbadać kontrolery defensywny, bazowy i asertywny.
12. Wykonać analizę wrażliwości oraz wiele powtórzeń.
13. Przygotować raport rozdzielający obserwacje rzeczywiste od wyników symulacji.

## Oczekiwany rezultat

Projekt powinien zakończyć się nie tylko wykresem „AV poprawia lub pogarsza ruch”, ale odpowiedzią na bardziej precyzyjne pytania:

- po ilu interakcjach kierowcy zaczynają wykorzystywać AV,
- jakie parametry AV najbardziej ułatwiają takie zachowanie,
- czy efekt utrzymuje się po zmianie kontrolera,
- jaki jest koszt dla pozostałych uczestników,
- czy można ograniczyć wykorzystywanie przez umiarkowaną asertywność bez pogorszenia bezpieczeństwa,
- czy strategiczne zachowanie jest stabilne, czy zależy od pojedynczych losowych epizodów.

## Najważniejsza teza projektu

> Przewidywalność deterministycznych pojazdów autonomicznych może początkowo poprawiać bezpieczeństwo lokalnych interakcji, ale w wielokrotnie powtarzanym ruchu kierowcy mogą nauczyć się wykorzystywać ich reguły. W rezultacie ocena AV bez uwzględnienia długoterminowej adaptacji kierowców może zawyżać przewidywaną poprawę bezpieczeństwa i płynności ruchu.
