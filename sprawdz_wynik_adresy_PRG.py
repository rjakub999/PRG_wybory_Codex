"""Kontrola spójności gotowego wyniku ze źródłowymi punktami PRG."""
import csv
from osgeo import ogr
from rozbij_granice import BASE

ogr.UseExceptions()
source = ogr.Open(str(BASE / 'Obwody_PRG_ArcGIS.gdb'))
output = ogr.Open(str(BASE / 'wyniki_adresy_PRG/adresy_komisje_PRG.gpkg'))
a = source.GetLayerByName('PRG_PunktyAdresowe_Lublin')
b = output.GetLayerByName('adresy_komisje_PRG')
assert a.GetFeatureCount() == b.GetFeatureCount(), 'Zmiana liczby punktów'
assert a.GetSpatialRef().IsSame(b.GetSpatialRef()), 'Zmiana układu współrzędnych'
lookup = {f['ID_IIP']: f.Clone() for f in b}
rows = list(csv.DictReader((BASE / 'wyniki_adresy_PRG/adresy_komisje_PRG.csv').open(encoding='utf-8-sig'), delimiter=';'))
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
