"""Kontrola spójności gotowego wyniku ze źródłowymi punktami PRG."""
import csv
import argparse
from osgeo import ogr
from rozbij_granice import BASE, GEO_RESULTS, prg_layer_name

ogr.UseExceptions()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--gdb', default=str(BASE / 'Adresy_PRG_Geoportal.gdb'))
parser.add_argument('--output', default=str(GEO_RESULTS / '02_przypisanie/adresy_komisje_PRG.gpkg'))
args = parser.parse_args()
source = ogr.Open(args.gdb)
output = ogr.Open(args.output)
a = source.GetLayerByName(prg_layer_name([l.GetName() for l in source], 'points'))
b = output.GetLayerByName('adresy_komisje_PRG')
assert a.GetFeatureCount() == b.GetFeatureCount(), 'Zmiana liczby punktów'
assert a.GetSpatialRef().IsSame(b.GetSpatialRef()), 'Zmiana układu współrzędnych'
lookup = {f['ID_IIP']: f.Clone() for f in b}
from pathlib import Path
rows = list(csv.DictReader(Path(args.output).with_suffix('.csv').open(encoding='utf-8-sig'), delimiter=';'))
assert len(rows) == len(lookup) == a.GetFeatureCount(), 'Niejednoznaczny klucz złączenia'
csv_lookup = {r['ID_IIP']: r for r in rows}
for feature in a:
    result = lookup[feature['ID_IIP']]
    for field in a.schema:
        assert feature[field.GetName()] == result[field.GetName()], field.GetName()
    geo, target = feature.GetGeometryRef(), result.GetGeometryRef()
    assert (geo is None and target is None) or geo.ExportToWkb() == target.ExportToWkb(), 'Zmiana geometrii'
    row = csv_lookup[feature['ID_IIP']]
    for field in row:
        assert row[field] == ('' if result[field] is None else str(result[field])), field
    regular = row['KOMISJE_STALE'].split('|') if row['KOMISJE_STALE'] else []
    assert (row['STATUS'] == 'PRZYPISANY') == (len(regular) == 1)
    assert (row['STATUS'] == 'KONFLIKT') == (len(regular) > 1)
    assert row['NR_KOMISJI'] == (regular[0] if len(regular) == 1 else '')
print(f'OK: {len(rows)} punktów; identyfikatory, atrybuty PRG, geometrie, CRS i CSV zgodne.')
