# Parametry robota: źródła

Ten plik zbiera źródła, z których wzięliśmy parametry robota i stanowiska
kompletacji w `src/core/config.py`. Przy każdej liczbie jest dokładny cytat
i sposób przeliczenia na jednostki modelu. Cytaty są w oryginale (po
angielsku), żeby dało się je sprawdzić.

## Źródła

| Skrót | Źródło | Rok | Rodzaj |
| --- | --- | --- | --- |
| Wurman | P. R. Wurman, R. D'Andrea, M. Mountz, „Coordinating Hundreds of Cooperative, Autonomous Vehicles in Warehouses”, AAAI. [PDF](https://www.dcsc.tudelft.nl/~sc4081/2018/assign/pap/robert_kiva_paper.pdf) | 2007 | publikacja twórców Kiva |
| IEEE | E. Guizzo, „Three Engineers, Hundreds of Robots, One Warehouse”, IEEE Spectrum. [link](https://spectrum.ieee.org/three-engineers-hundreds-of-robots-one-warehouse) | 2008 | artykuł w czasopiśmie technicznym |
| RobotsGuide | „Kiva Drive Unit”, ROBOTS: Your Guide to the World of Robotics (IEEE). [link](https://robotsguide.com/robots/kiva) | 2018 | karta robota |
| MWPVL | MWPVL International, „Kiva Systems”. [link](https://www.mwpvl.com/html/kiva_systems.html) | 2012 | analiza firmy doradczej |

Amazon, który kupił Kiva w 2012, nie publikuje specyfikacji swoich robotów.
Powyższe źródła opisują pierwszy model Kiva (DU 1000).

## Prędkość robota: 1,3 m/s

| Źródło | Cytat | Przeliczenie |
| --- | --- | --- |
| IEEE | „The current production model can lift 454 kilograms and travel at 1.3 meters per second.” | 1,3 m/s |
| RobotsGuide | prędkość „4.68 km/h” | 4,68 / 3,6 = 1,3 m/s |
| MWPVL | „The robots travel at a speed of about 3 miles per hour” | 3 × 1609 m / 3600 s ≈ 1,34 m/s |

Trzy niezależne źródła podają to samo, więc to najpewniejszy parametr.

## Wielkość pola siatki: 1 m (bez zmian)

| Źródło | Cytat | Przeliczenie |
| --- | --- | --- |
| IEEE | „two-dimensional bar-coded stickers laid out by hand 1 meter from each other, in a grid” | 1 m |
| MWPVL | „2D bar codes that are placed every 40" to 60" along the street grid” | 1,0–1,5 m |
| MWPVL | regał „39" wide x 39" deep” | ok. 1 m |
| Wurman | „three foot square shelving units” | ok. 0,9 m |

## Kompletacja: 0 s stałe + 6 s na sztukę

| Źródło | Cytat |
| --- | --- |
| Wurman | „the Kiva system delivers a new pod face every six seconds, which sets a baseline picking rate of 600 lines per hour.” |
| Wurman | „operators picked at nearly 700 lines per hour” (pokaz w drogerii) |
| IEEE | „present a new item to a worker every 6 seconds, leading to a base rate of 600 picks per hour” |
| MWPVL | „Pick rates of 600+ order lines per hour are achievable in a pure picking environment” |
| MWPVL | klient z odzieżą: „operators pick between 200 - 250 lines per hour” |

Przeliczenie: 3600 s / 600 linii = 6 s na linię. Model liczy czas na sztukę
(`per_item_s`), a nie na linię. W danych Olist prawie każda linia to jedna
sztuka, więc traktujemy sztukę jak linię. Czasu stałego na wizytę regału
źródła nie podają osobno, dlatego `fixed_s = 0`.

## Bateria: ok. 2 h jazdy, czyli 0,0107% na metr

| Źródło | Cytat |
| --- | --- |
| MWPVL | robots „travel to designated charge stations every couple of hours where they receive a 5-minute battery re-charge” |
| MWPVL | „assume that at any time 5% of the robots will be out of commission for short re-charging intervals” |

Przeliczenie: „every couple of hours” przyjmujemy jako 2 h ciągłej jazdy.
2 h × 3600 s × 1,3 m/s = 9360 m, więc spadek baterii to 100% / 9360 m ≈
0,0107% na metr.

Zastrzeżenia:
- To najsłabiej udokumentowany parametr: jedno źródło, firma doradcza, a nie
  producent.
- „Co kilka godzin” to czas pracy, a nie samej jazdy. Robot część czasu stoi
  (przy stanowisku, w kolejce), więc w symulacji będzie jeździł do ładowarki
  rzadziej niż co 2 h. Dlatego sprawdzamy 1, 2 i 4 h w analizie wrażliwości.

## Ładowanie: 0,27% na sekundę

Cytat jak wyżej: „a 5-minute battery re-charge”. Model ładuje robota od
progu (`charge_threshold_pct`, 20%) do pełna. Przyjmujemy, że 5 minut to
właśnie to ładowanie: 80% / 300 s ≈ 0,27% na sekundę.

Zastrzeżenie: źródło nie mówi, od jakiego poziomu baterii liczy się te
5 minut. Próg 20% nie pochodzi ze źródeł, tylko z modelu.

## Czego źródła nie podają

- przyspieszenia i hamowania (model zakłada stałą prędkość),
- czasu podnoszenia i obracania regału (IEEE mówi tylko, że regał jest
  podnoszony o ok. 5 cm),
- liczby przegródek ani produktów na regale.

Tych rzeczy nie modelujemy, bo nie mamy dla nich liczb.

## Analiza wrażliwości

Parametry, których nie jesteśmy pewni, sprawdzamy w kilku wariantach
w scenariuszach:

| Parametr | Wartość bazowa | Warianty | Skąd warianty |
| --- | --- | --- | --- |
| prędkość | 1,3 m/s | 1,0 / 1,3 / 1,5 m/s | wokół wartości ze źródeł |
| kompletacja | 600 linii/h (6 s) | 200 / 400 / 600 / 700 linii/h | odzież (MWPVL), przenośnik (IEEE: 200–400), Kiva, rekord (Wurman) |
| bateria | 2 h | 1 / 2 / 4 h | wokół „every couple of hours” |
