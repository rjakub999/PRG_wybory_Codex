# Przypisanie komisji na podstawie najbliższych adresów

Skrypt `przypisz_sasiedztwo_PRG.py` uzupełnia punkty z `STATUS = BRAK_PRZYPISANIA`
i pustym `NR_KOMISJI`. Analizuje 5 najbliższych jednoznacznie przypisanych
punktów z tej samej gminy (`TERYT_GMI`) i wybiera komisję z największą liczbą
głosów. Wynik 3:2 daje komisję z 3 głosami. Wynik 2:1:1:1 daje komisję z 2
głosami; wynik 2:2:1 jest remisem i punkt pozostaje nieprzypisany.

## Uruchomienie

W PowerShell, w katalogu projektu:

```powershell
& 'C:/Program Files/QGIS 4.0.2/bin/python-qgis.bat' przypisz_sasiedztwo_PRG.py
```

Wymagania: Python 3.10+, GDAL z obsługą GPKG. Analiza działa w projektowanym
układzie współrzędnych o jednostce metr, np. EPSG:2180. Nie wymaga SciPy ani QGIS
Processing. Odległości są prostoliniowe, liczone z geometrii punktów.

Opcje:

```powershell
python przypisz_sasiedztwo_PRG.py --k 5 --max-distance 200 --teryt 0663011
python przypisz_sasiedztwo_PRG.py --input wejscie.gpkg --layer adresy_komisje_PRG --output wynik.gpkg
```

`--max-distance` ogranicza wyszukiwanie do podanej odległości w metrach.
Domyślnie nie ma limitu. Skrypt wymaga pełnych `k` sąsiadów; nie przypisuje,
gdy sąsiadów jest mniej. `--teryt` opcjonalnie ogranicza analizowane punkty do
jednej gminy. Domyślnie analizowane są wszystkie gminy, każda osobno.
Przy równej odległości kolejność wyznacza `ID_IIP`, dzięki czemu wynik jest
powtarzalny. Zastąpienie istniejącego wyniku wymaga `--overwrite`.

## Wyniki

Domyślne wejście znajduje się w `wyniki_PRG_Geoportal/02_przypisanie`.
Domyślne pliki wynikowe w `wyniki_PRG_Geoportal/04_sasiedztwo`:

- `adresy_komisje_sasiedztwo.gpkg`, warstwa `adresy_komisje_sasiedztwo`.
- `adresy_komisje_sasiedztwo.csv`, wszystkie punkty do złączenia przez `ID_IIP`.
- `adresy_komisje_sasiedztwo_raport.csv`, decyzja dla każdego nieprzypisanego punktu.
- `adresy_komisje_sasiedztwo_podsumowanie.json`, liczby wynikowe i parametry.

Plik wejściowy pozostaje zachowany. Skrypt kopiuje wszystkie geometrie i pola.
Przy nowym przypisaniu zmienia `NR_KOMISJI`, `KOMISJE_STALE` i ustawia
`STATUS = PRZYPISANY_SASIEDZTWO`. Komisje odrębne i źródłowe uwagi pozostają
zachowane. `NR_KOMISJI_PRZED` i `STATUS_PRZED` zapisują stan wcześniejszy
analizowanych punktów. Nowe pola `SAS_` opisują metodę i decyzję:

- `SAS_STATUS`: przypisanie, remis, brak sąsiadów lub inna przyczyna pominięcia.
- `SAS_K`, `SAS_GLOSY`, `SAS_UDZIAL`: liczba sąsiadów, największa liczba głosów
  i jej udział. Udział nie jest prawdopodobieństwem poprawnego przypisania.
- `SAS_DMIN`, `SAS_DMAX`: odległość najbliższego i najdalszego użytego sąsiada.
- `SAS_WYNIK_GLOSOW`: rozkład głosów w JSON.
- `SAS_SASIEDZI`: identyfikatory, komisje, adresy i odległości sąsiadów w JSON.

Punkty referencyjne muszą mieć wejściowy `STATUS = PRZYPISANY`, zgodne
`NR_KOMISJI` i `KOMISJE_STALE`. Nowe przypisania nie stają się sąsiadami dla
kolejnych punktów. Konflikty nie są automatycznie rozstrzygane.
Skrypt odrzuca wejście z istniejącymi polami `SAS_`, zapobiegając przypadkowemu
powtórzeniu analizy na wynikach poprzedniego uruchomienia.

To przypisanie szacowane z sąsiedztwa, a nie potwierdzenie opisem granic.
Zwłaszcza przy granicach obwodów, naprzemiennych numerach ulic lub dużych
odległościach wymaga oceny. Można na tym wyniku ponownie wykonać Voronoi
i agregację, ale warstwy z poprzedniego kroku nie są automatycznie zastępowane.

## Kontrola

```powershell
& 'C:/Program Files/QGIS 4.0.2/bin/python-qgis.bat' -m unittest test_przypisz_sasiedztwo_PRG.py
```

Po wykonaniu skrypt sprawdza zachowanie wszystkich geometrii, CRS, liczby
punktów i atrybutów nieobjętych nowymi przypisaniami w zapisanym GeoPackage.
