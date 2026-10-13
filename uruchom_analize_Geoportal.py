"""Powtórz wszystkie etapy na Adresy_PRG_Geoportal.gdb, zachowując wyniki."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / 'wyniki_PRG_Geoportal'
if OUT.exists() and any(OUT.iterdir()):
    raise FileExistsError('Folder wyniki_PRG_Geoportal już zawiera dane; zachowaj go pod inną nazwą przed nowym przebiegiem.')
OUT.mkdir(exist_ok=True)
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
steps = [
    ['rozbij_granice.py'],
    ['przypisz_adresy_PRG.py'],
    ['sprawdz_wynik_adresy_PRG.py'],
    ['wykonaj_voronoi_QGIS.py'],
    ['przypisz_sasiedztwo_PRG.py'],
    ['wykonaj_voronoi_QGIS.py', '--input', str(OUT / '04_sasiedztwo/adresy_komisje_sasiedztwo.gpkg'),
     '--layer', 'adresy_komisje_sasiedztwo', '--output', str(OUT / '05_voronoi_sasiedztwo/voronoi_komisje_sasiedztwo.gpkg')],
]
manifest = dict(zrodlo=str(BASE / 'Adresy_PRG_Geoportal.gdb'),
                rozpoczecie_UTC=datetime.now(timezone.utc).isoformat(), etapy=[])
for command in steps:
    print('ETAP:', ' '.join(command), flush=True)
    subprocess.run([sys.executable, '-u', str(BASE / command[0]), *command[1:]],
                   cwd=BASE, check=True)
    manifest['etapy'].append(command)
    (OUT / 'przebieg.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
manifest['zakonczenie_UTC'] = datetime.now(timezone.utc).isoformat()
manifest['status'] = 'UKONCZONO'
(OUT / 'przebieg.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('Ukończono:', OUT, flush=True)
