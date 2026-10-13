# Rozdzielanie granic obwodów

Skrypt `rozbij_granice.py` odczytuje kolumnę `Opis granic` (nagłówki w pierwszym
wierszu) i dopisuje kolumny `Granica_01` itd. do kopii skoroszytu. Zachowuje
kolejność wpisów, zakresy numerów, litery numerów, parzystość i zwrot „do końca”.
Jeden wpis ulicy z zakresem to jedna komórka; skrypt nie rozwija zakresów do
wszystkich punktów adresowych i nie sprawdza istnienia każdego numeru w PRG.

## Uruchomienie na tym komputerze

W PowerShell, w katalogu projektu:

```powershell
& 'C:/Program Files/QGIS 4.0.2/bin/python-qgis.bat' rozbij_granice.py
```

Wymagania: Python 3.9+, `openpyxl` oraz GDAL (`osgeo.ogr`) z obsługą OpenFileGDB.
Alternatywnie można użyć Python ArcGIS Pro z ArcPy i aktywną licencją.
Odczyt geobazy nie zmienia jej zawartości. Oryginalny XLSX pozostaje zachowany.

```powershell
python rozbij_granice.py --input dane.xlsx --gdb Obwody_PRG_ArcGIS.gdb --output wynik.xlsx --report kontrola.csv --sheet Arkusz1
python -m unittest test_rozbij_granice.py
```

## Uzgadnianie nazw

Aktualnym źródłem jest `Adresy_PRG_Geoportal.gdb`. Źródłem pisowni wynikowej
jest `NAZWA_ULC` w warstwach zaczynających się od `PRG_Ulice`
i `PRG_PunktyAdresowe` (po jednej warstwie każdego rodzaju). Pola `NAZWA_TER1` i `NAZWA_TER2` pomagają
w dopasowaniu patronów. Nazwy ulic w wyniku nie mają dodatkowego `ul.`, chyba że
taki tekst znajduje się w samej nazwie PRG. Aleje i place zachowują zapis PRG.

Najpierw porównywana jest pełna nazwa z polskimi znakami. Następnie dopuszczane
są różnice wielkości liter, interpunkcji, diakrytyki, oznaczeń ulic i wybranych
tytułów (ks., gen., dr, prof.). Automatyczna zamiana wymaga jednego kandydata.
Podobieństwo tekstowe służy tylko do sugestii w raporcie, nigdy do zamiany.

Raport CSV (UTF-8 BOM, separator średnik) zawiera każdy fragment, wynik,
wiersz źródłowy i status: `PRG`, `BRAK_W_PRG`, `NIEJEDNOZNACZNE` lub
`POZA_LUBLINEM`. Fragmenty spoza Lublina oraz niedopasowane pozostają
w oryginalnej postaci. Geobaza Lublina nie potwierdza nazw miejscowości
z sąsiednich gmin. Pełnej zgodności wszystkich wpisów z PRG nie można zapewnić,
jeżeli wpisu brakuje w dostarczonym rejestrze.

Domyślne wyniki: `obwody_glosowania_Lublin_granice.xlsx`
i `raport_dopasowania_PRG.csv` w `wyniki_PRG_Geoportal/01_granice`.
Ponowne uruchomienie tego pojedynczego skryptu zastępuje te wyniki.
Skrypt odrzuca źródło z istniejącymi kolumnami `Granica_XX`, aby nie dublować kolumn.
