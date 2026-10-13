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
3. `przypisz_sasiedztwo_PRG.py`: uzupełnia nieprzypisane adresy głosowaniem
   pięciu najbliższych przypisanych adresów w tej samej gminie. Remisy pozostają
   do kontroli. Szczegóły: [README_sasiedztwo_PRG.md](README_sasiedztwo_PRG.md).

Komisje stałe i odrębne są zapisane osobno. Braki i konflikty wymagają kontroli;
skrypty nie wybierają arbitralnie komisji przy niejednoznacznym przypisaniu.

## Dane wejściowe

Dane pozostają lokalnie i nie są publikowane w repozytorium:

- `obwody_glosowania_Lublin.xlsx`
- `Adresy_PRG_Geoportal.gdb`, zawierająca `PRG_Ulice_066301_eksport`
  i `PRG_PunktyAdresowe_066301_eksport` (aktualne źródło).

Poprzednia `Obwody_PRG_ArcGIS.gdb` oraz wyniki w `wyniki_adresy_PRG`
pozostają zachowane. Skrypty rozpoznają oba warianty nazw warstw, ale domyślnie
korzystają z Geoportalu. Zmiana źródła nie polega na przemianowaniu starej geobazy.

Wymagania: Python 3.10+, openpyxl, GDAL z obsługą OpenFileGDB i GPKG.
Pierwszy skrypt obsługuje także ArcPy; drugi wymaga GDAL.

## Uruchomienie

W środowisku Python z wymaganymi bibliotekami:

```console
python rozbij_granice.py
python przypisz_adresy_PRG.py
python -m unittest test_rozbij_granice.py test_przypisz_adresy_PRG.py test_przypisz_sasiedztwo_PRG.py
python sprawdz_wynik_adresy_PRG.py
```

Cały przebieg w Pythonie QGIS (w tym Voronoi i agregacja):

```powershell
& 'C:/Program Files/QGIS 4.0.2/bin/python-qgis.bat' uruchom_analize_Geoportal.py
```

Nowe wyniki trafiają do `wyniki_PRG_Geoportal`, z osobnymi katalogami:
`01_granice`, `02_przypisanie`, `03_voronoi`, `04_sasiedztwo`
i `05_voronoi_sasiedztwo`. Ostatni etap powtarza Voronoi i agregację po
uzupełnieniu komisji z sąsiedztwa. Pole `NR_KOMISJI` zawiera numer obwodu stałego,
a nie numer komisji odrębnej. Wszystkie parametry kolejnych etapów są zapisane
w skryptach oraz pliku `przebieg.json`. Przebieg odmawia nadpisania istniejącego,
niepustego katalogu wynikowego.

Ostatnia kontrola wymaga lokalnych danych i wygenerowanych wyników w domyślnych
lokalizacjach. Porównuje identyfikatory, atrybuty, geometrie, układ współrzędnych
i zgodność CSV z warstwą punktową.

## Ostatni zweryfikowany przebieg

Na źródle Geoportalu przetworzono 29 059 punktów, wszystkie oznaczone jako
Lublin (`0663011`). Opisy granic przypisały 28 946 punktów jednoznacznie,
pozostawiając 80 bez przypisania i 33 konflikty. Sąsiedztwo przypisało dodatkowo
76 punktów; pozostały 4 remisy i 33 konflikty. Końcowa agregacja zawiera 196
grup komisji oraz jedną grupę z pustym numerem.

Liczba otworów wewnętrznych w poligonach agregowanych wyniosła 38 przed
uzupełnieniem z sąsiedztwa i 14 po nim (224 w przebiegu na starym źródle).
Sprawdzono geometrie, atrybuty, CSV, zachowanie sumy powierzchni oraz 19 testów
jednostkowych. Przypisania z sąsiedztwa mają osobny status i są oszacowaniem.
