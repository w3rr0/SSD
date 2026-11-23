# Symulacja magazynu Kiva

Symulacja magazynu, w którym roboty przywożą regały z produktami do stanowisk
kompletacji, jak roboty Kiva w magazynach Amazona. Cel: sprawdzić, jak
rozmieszczenie produktów i sposób sterowania robotami wpływają na czas
realizacji zamówień. Pełny opis: `topic/deliverable1.txt`.

## Uruchomienie

Potrzebny Python 3.15 i [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run data/download_olist.py   # dane Olist do data/raw/ (szczegóły: data/README.md)
make test                       # testy
make visual                     # wizualizacja w przeglądarce (port 8521)
make scenarios                  # scenariusze, wyniki w output/scenarios/
```

Inne cele: `download_olist`, `record` (zapis jednego przebiegu do CSV/JSON),
`run_visual_olist` (ta sama wizualizacja na porcie 8522), `baseline` (szybki pomiar),
`olist_report`, `olist_validation`, `olist_plots`, `queue_validation`.

## Wizualizacja

`make visual` otwiera stronę z planem magazynu, statystykami na żywo
(baterie, średni i ostatni czas realizacji, bezczynność, czas w korkach
i kolejkach, wykorzystanie stanowisk) oraz listą napływających zamówień.
W panelu bocznym wybiera się magazyn (pliki `layouts/*.json`), liczbę
robotów, źródło zamówień (Olist albo demo), rozmieszczenie i natężenie;
zmiany działają po kliknięciu Reset. Zakleszczenie zatrzymuje symulację
i podświetla roboty, których dotyczy. Bez danych Olist strona używa
zamówień demo.

## Co jest w repozytorium

| Część | Pliki |
| --- | --- |
| Model: siatka, roboty, trasy A*, rezerwacje pól, konwoje, kolejki, ładowanie, awarie, metryki | `src/core/`, `src/agents/`, `src/pipeline/`, `src/environment/`, `src/metrics/` |
| Przydział zadań: najbliższy robot albo termin + bateria | `src/strategies/assignment.py` |
| Rozmieszczenie produktów: losowe, ABC, powrót na najbliższe wolne miejsce | `src/strategies/placement.py` |
| Dane Olist i generator zamówień | `src/data/olist.py`, `src/orders/olist_generator.py` |
| Walidacja: generator na danych 2018, kolejka ze wzorem z teorii kolejek | `runners/olist_validation.py`, `runners/queue_validation.py`, `src/validation/` |
| Parametry robota z publikacji o Kiva | `src/core/config.py`, `docs/zrodla_parametry_robota.md` |
| Scenariusze z powtórzeniami i przedziałami ufności | `src/experiments/scenarios.py`, `runners/run_scenarios.py` |
| Decyzje (problem, opcje, wybór, powód) | `docs/decyzje_dane_olist.md` |
| Wizualizacja: plan magazynu (SVG), statystyki i zamówienia na żywo | `src/visualization/` |
| Układy magazynu wczytywane z JSON (opis formatu w README katalogu) | `layouts/`, `src/environment/layout_io.py` |

## Stan projektu

**Działa**
- Wszystkie elementy modelu z opisu projektu, w tym ładowanie, awarie
  i oba sposoby przydziału zadań.
- Zamówienia z Olist (kalibracja na 2017, walidacja na 2018: 4 z 5
  porównań zgodne).
- Runner wszystkich scenariuszy z opisu (bez awarii a pilnych zamówień).
- Zakleszczenia usunięte zasadami ruchu (`TrafficParams`, opis w
  `docs/decyzje_dane_olist.md`, sekcja 10): 1,6% zakleszczonych przebiegów
  zamiast 47%; zwykły dzień i ruch do ×5 bez zakleszczeń.

**Walidacja z teorią kolejek**
- Część A (samo stanowisko, `tests/test_queueing.py`) zgadza się ze wzorem
  M/G/1.
- Część B (cały magazyn, `runners/queue_validation.py`) po zasadach ruchu nie
  mieści się w przedziale ufności w żadnym z 8 ustawień: przekazanie
  stanowiska wydłuża kolejkę, a limit 3 robotów przy stanowisku przy ρ = 0,9
  ogranicza wykorzystanie stanowiska do 78% (kod `LIMIT`). Szczegóły i opcje:
  sekcja 11 w `docs/decyzje_dane_olist.md`.

**Zostaje**
- Kilka zakleszczeń przy Black Friday (głównie układ `hala_L`) i przeciążenie
  szczytu w całej dobie (`TimeoutError`).
- Przy 2 robotach i dużym ruchu roboty potrafią krążyć przy stanowiskach,
  aż rozładują baterie (model tego nie wykrywa).

**Do ustalenia**
- **Pilne zamówienia w scenariuszu z awariami.** Opis projektu każe
  zbadać wpływ awarii na pilne zamówienia, ale dane tego nie definiują.
  Terminy wysyłki w Olist to dni (najkrótszy 95 h, mediana 6 dni),
  a symulujemy jedną dobę, więc żadne zamówienie nie zbliży się do
  terminu. Z tego samego powodu przydział „termin + bateria” w praktyce
  patrzy tylko na baterię. Model ma pole `urgent` (pilne dostają robota
  pierwsze), ale generator Olist go nie ustawia. Opcje: A) pilne to np.
  10% zamówień z najkrótszym terminem z Olist i mierzymy ich czas
  realizacji z awariami i bez; B) pilne losowo z własnym limitem, np.
  „gotowe w 1 h”, i liczymy spóźnienia; C) terminy z Olist skrócone do
  skali jednej zmiany.
- Podpięcie powrotu na najbliższe wolne miejsce w samym modelu (na razie
  przez podklasę w runnerach).

**Następne kroki**
1. Decyzja o walidacji części B (opcje A–C w sekcji 11 decyzji).
2. Runner scenariuszy: odróżnić zakleszczenie od przeciążenia (`TimeoutError`).
3. Pełne liczenie scenariuszy (najpierw usunąć stary `output/scenarios/runs.csv`),
   wykresy i wnioski do sprawozdania.
