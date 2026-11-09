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
make run_visual_olist           # wizualizacja na zamówieniach Olist (port 8522)
make scenarios                  # scenariusze, wyniki w output/scenarios/
```

Inne cele: `visual` (wizualizacja demo), `baseline` (szybki pomiar),
`olist_report`, `olist_validation`, `olist_plots`, `queue_validation`.

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

## Stan projektu

**Działa**
- Wszystkie elementy modelu z opisu projektu, w tym ładowanie, awarie
  i oba sposoby przydziału zadań.
- Zamówienia z Olist (kalibracja na 2017, walidacja na 2018: 4 z 5
  porównań zgodne).
- Walidacja z teorią kolejek: 6 z 8 ustawień w przedziale ufności.
- Runner wszystkich scenariuszy z opisu (bez awarii a pilnych zamówień).
- Przy małym ruchu (zwykły dzień, kilka robotów) symulacja przechodzi.

**Nie działa: zakleszczenia robotów**
- Przy większym ruchu albo większej flocie roboty się blokują
  (`DeadlockError`). W pilotażu żaden przebieg w szczycie nie doszedł do
  końca. W wizualizacji przy ruchu ×20 zakleszcza się 25–80% przebiegów,
  zależnie od liczby robotów.
- Przyczyna: alejki o szerokości jednego pola z ruchem w obie strony,
  a do tego bezczynne roboty na miejscach startowych przy stanowiskach.
  Odsunięcie miejsc startowych pomaga tylko częściowo.
- Do decyzji zespołu: jazda pustego robota pod regałami (jak w Kiva),
  alejki jednokierunkowe, szersze alejki albo lepsze rozładowywanie korków.
- Przy 2 robotach i dużym ruchu roboty potrafią też krążyć przy
  stanowiskach, aż rozładują baterie (model tego nie wykrywa).

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
1. Decyzja i poprawka zakleszczeń.
2. Sprawdzenie poprawki runnerem na wszystkich scenariuszach.
3. Pełne liczenie scenariuszy (ok. 45 min), wykresy i wnioski.
