# PRG — granice obwodów głosowania w Lublinie

Repozytorium tego projektu należy do Jakuba:
https://github.com/rjakub999/PRG_wybory_Codex.

## Przetwarzanie

1. `rozbij_granice.py`: odczytuje `Opis granic` ze skoroszytu i zapisuje
   kolumny `Granica_01`, `Granica_02` itd. z nazwami ulic uzgodnionymi z PRG.
   Szczegóły: [README_granice.md](README_granice.md).
2. `przypisz_adresy_PRG.py`: wybiera istniejące punkty adresowe PRG zgodnie
   z ulicami, zakresami numerów i parzystością. Tworzy tabelę CSV do złączenia
   przez `ID_IIP` oraz warstwę punktową GeoPackage z komisjami.
   Szczegóły: [README_adresy_PRG.md](README_adresy_PRG.md).

Komisje stałe i odrębne są zapisane osobno. Braki i konflikty wymagają kontroli;
skrypty nie wybierają arbitralnie komisji przy niejednoznacznym przypisaniu.

## Dane wejściowe

Dane pozostają lokalnie i nie są publikowane w repozytorium:

- `obwody_glosowania_Lublin.xlsx`
- `Obwody_PRG_ArcGIS.gdb`, zawierająca `PRG_Ulice_Lublin`
  i `PRG_PunktyAdresowe_Lublin`.

Wymagania: Python 3.10+, openpyxl, GDAL z obsługą OpenFileGDB i GPKG.
Pierwszy skrypt obsługuje także ArcPy; drugi wymaga GDAL.

## Uruchomienie

W środowisku Python z wymaganymi bibliotekami:

```console
python rozbij_granice.py
python przypisz_adresy_PRG.py
python -m unittest test_rozbij_granice.py test_przypisz_adresy_PRG.py
python sprawdz_wynik_adresy_PRG.py
```

Ostatnia kontrola wymaga lokalnych danych i wygenerowanych wyników w domyślnych
lokalizacjach. Porównuje identyfikatory, atrybuty, geometrie, układ współrzędnych
i zgodność CSV z warstwą punktową.
