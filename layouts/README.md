# Układy magazynu

Każdy plik `*.json` w tym katalogu pojawia się w wizualizacji na liście
„Magazyn”. Plik z błędem jest pomijany na liście; przyczynę pokaże:

```
uv run python -c "from src.environment.layout_io import load_layout; load_layout('layouts/moj.json')"
```

## Mapa rysowana znakami

```json
{
  "name": "Mała hala",
  "description": "Opis widoczny nad mapą.",
  "map": [
    "##########",
    "#.RRRR...C",
    "S........#",
    "#BB......#",
    "##########"
  ]
}
```

| Znak | Znaczenie |
| --- | --- |
| `#` | ściana lub słup (rysowana na ciemno) |
| ` ` (spacja) | poza budynkiem (nie rysowane), np. wycięty narożnik hali w kształcie L |
| `.` | podłoga / alejka |
| `R` | regał |
| `S` | stanowisko kompletacji |
| `C` | ładowarka |
| `B` | miejsce startowe robota |

- Pierwszy wiersz to góra hali, tak jak na ekranie.
- Krótsze wiersze są dopełniane spacjami (poza budynkiem).
- Regały, stanowiska i ładowarki są przeszkodami: każdy musi dotykać alejki
  połączonej z resztą magazynu, inaczej plik zostanie odrzucony.
- Brakujące miejsca startowe robotów są dobierane z wolnych alejek (od dołu),
  więc liczba `B` nie ogranicza liczby robotów.
- Stanowiska i ładowarki zwykle stoją w linii ściany, z alejką przed nimi.

## Generator Kiva

Zamiast mapy można podać parametry `WarehouseLayout.generate`:

```json
{
  "name": "Kiva 6×4",
  "generator": {"block_columns": 6, "block_rows": 4, "num_stations": 3}
}
```

Dozwolone klucze: `block_columns`, `block_rows`, `block_length`,
`block_depth`, `num_stations`, `num_chargers`, `num_robots`, `width`,
`height`.
