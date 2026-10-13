# Adresy PRG z komisjami

Uruchomienie w PowerShell z katalogu projektu:

```powershell
& 'C:/Program Files/QGIS 4.0.2/bin/python-qgis.bat' przypisz_adresy_PRG.py
```

Ponowne wygenerowanie wyników: dopisz `--overwrite` (zastępuje GeoPackage).
Parametry: `--input`, `--gdb`, `--output-dir`. Domyślnym wejściem jest
`obwody_glosowania_Lublin_granice.xlsx`. Aby użyć innego wyniku pierwszego skryptu,
np. `Plik_wynikowy.xlsx`, wskaż go przez `--input Plik_wynikowy.xlsx`.
Aktualne domyślne źródło: `Adresy_PRG_Geoportal.gdb`.
Domyślny skoroszyt pochodzi z `wyniki_PRG_Geoportal/01_granice`.
Wymagania: Python 3.10+, GDAL z OpenFileGDB i GPKG, openpyxl oraz
`rozbij_granice.py` obok skryptu. Ten skrypt korzysta z GDAL, nie z ArcPy.

## Wyniki w folderze wyniki_PRG_Geoportal/02_przypisanie

- `adresy_komisje_PRG.gpkg`: warstwa punktowa z geometrią, układem współrzędnych
  i atrybutami oryginalnego PRG oraz polami przypisań.
- `adresy_komisje_PRG.csv`: jeden rekord na punkt PRG, do złączenia przez `ID_IIP`.
- `adresy_do_weryfikacji.csv`: braki, konflikty i nietypowe numery.
- `raport_regul.csv`: status i liczba punktów dla każdej granicy wejściowej.
- `podsumowanie.json`: liczby wynikowe i ścieżki źródeł.

GeoPackage można dodać bezpośrednio w QGIS lub ArcGIS Pro. Można też złączyć CSV
z `PRG_PunktyAdresowe_Lublin` przez tekstowe pole `ID_IIP` i wyeksportować punkty
do nowej klasy obiektów w geobazie. CSV ma UTF-8 BOM i separator średnik;
`NUMER_PORZ` należy wczytać jako tekst. Oryginalna geobaza pozostaje zachowana.

`NR_KOMISJI` jest liczbą z kolumny `Numer` dla obwodu stałego, wypełnioną tylko
przy jednym przypisaniu. `KOMISJE_STALE` i `KOMISJE_ODREBNE` zawierają listy
numerów oddzielonych `|`. Szpital, DPS i areszt są obwodami odrębnymi i nie
zastępują komisji stałej adresu. `STATUS` przyjmuje `PRZYPISANY`, `KONFLIKT`
lub `BRAK_PRZYPISANIA`. Konflikt oznacza różne komisje stałe, a nie powtórzenie
tej samej reguły. `REGULY` wskazuje arkusz, wiersz i kolumnę źródłową.

## Zasady i ograniczenia

Skrypt wybiera istniejące adresy PRG zamiast tworzyć hipotetyczne numery.
Porównuje pełne nazwy ulic, zachowując rozróżnienie Sadowa/Sądowa.
Parzystość wynika z części liczbowej numeru. Zakres 1–41 obejmuje też 41A,
a 1–41B kończy się na 41B. Pojedynczy numer 2 oznacza dokładnie 2, bez 2A.
Te konwencje należy zweryfikować przy granicznych adresach dla zastosowania
operacyjnego. Litery porównywane są bez rozróżnienia wielkości.

Numery złożone (np. 4-6 lub 7/9/3) objęte regułą ograniczoną numerami lub
parzystością trafiają do kontroli, ponieważ ich interpretacja może być
niejednoznaczna. Reguła obejmująca całą ulicę może przypisać taki punkt.
Nieobsługiwane ograniczenia nie powodują przypisania całej ulicy.
Jeżeli źródłowy `Opis granic` oznacza plac/skwer, a pierwszy skrypt uzgodnił
go z nazwą ulicy bez tego oznaczenia, reguła trafia do kontroli zamiast
przypisywać całą ulicę. Dotyczy to placu Jana Kochanowskiego w tych danych.
Fragmenty zawierające kolejne jawne `ul.` są rozdzielane; brak końcowego nawiasu
przy słowie `parzyste` lub `nieparzyste` jest naprawiany i zapisany w raporcie.

Dane spoza Lublina są pomijane przy przypisaniu. Nazwy nieobecne w PRG,
nowe adresy, braki danych i nakładające się opisy mogą pozostawić punkty bez
jednoznacznego przypisania. Warstwa obejmuje wszystkie punkty PRG, również te
wymagające kontroli; nie oznacza to potwierdzenia kompletności opisów obwodów.

Testy:
```powershell
& 'C:/Program Files/QGIS 4.0.2/bin/python-qgis.bat' -m unittest test_przypisz_adresy_PRG.py
```
