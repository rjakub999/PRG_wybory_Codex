"""Uzupełnij brakujące komisje przez głosowanie k najbliższych adresów PRG.

Wymaga GDAL (osgeo.ogr). Sąsiedzi pochodzą wyłącznie z wejściowych,
jednoznacznie przypisanych punktów tej samej gminy. Brak propagacji przypisań.
"""
from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent


def vote(neighbors, k):
    """neighbors: lista słowników z commission; unikalna przewaga wystarcza."""
    counts = Counter(n['commission'] for n in neighbors)
    if len(neighbors) < k:
        return None, 'ZA_MALO_SASIADOW', counts
    maximum = max(counts.values())
    winners = [committee for committee, count in counts.items() if count == maximum]
    if len(winners) != 1:
        return None, 'REMIS', counts
    return winners[0], 'PRZYPISANO', counts


def nearest(target, candidates, k, max_distance=None):
    def ranked():
        for candidate in candidates:
            if candidate['id'] == target['id']:
                continue
            distance = math.hypot(candidate['x'] - target['x'], candidate['y'] - target['y'])
            if max_distance is None or distance <= max_distance:
                yield distance, candidate['id'], candidate
    # ID_IIP rozstrzyga równe odległości w sposób powtarzalny.
    selected = heapq.nsmallest(k, ranked(), key=lambda item: (item[0], item[1]))
    return [{**candidate, 'distance_m': distance} for distance, _, candidate in selected]


def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)


def run(args):
    from osgeo import ogr
    ogr.UseExceptions()
    if args.k < 1 or (args.max_distance is not None and args.max_distance <= 0):
        raise ValueError('k i maksymalna odległość muszą być dodatnie')
    if args.input.resolve() == args.output.resolve():
        raise ValueError('Wynik musi być inny niż plik wejściowy')
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f'{args.output}: użyj --overwrite lub innej ścieżki')
    source = ogr.Open(str(args.input), 0)
    if source is None:
        raise ValueError('Nie można otworzyć wejścia')
    layer = source.GetLayerByName(args.layer)
    if layer is None:
        raise ValueError(f'Brak warstwy: {args.layer}')
    required = {'ID_IIP', 'TERYT_GMI', 'NR_KOMISJI', 'STATUS', 'KOMISJE_STALE'}
    fields = {f.GetName() for f in layer.schema}
    if not required <= fields:
        raise ValueError(f'Brak pól: {required - fields}')
    if any(f.startswith('SAS_') for f in fields):
        raise ValueError('Wejście zawiera już wynik analizy sąsiedztwa; użyj pierwotnego pliku')
    srs = layer.GetSpatialRef()
    if srs is None or not srs.IsProjected() or abs(srs.GetLinearUnits() - 1) > 1e-9:
        raise ValueError('Analiza wymaga projektowanego układu współrzędnych w metrach')
    candidates, targets, seen = defaultdict(list), [], set()
    for feature in layer:
        data = dict(feature.items())
        identifier = data['ID_IIP']
        if not identifier or identifier in seen:
            raise ValueError(f'Brak lub powtórzenie ID_IIP: {identifier}')
        seen.add(identifier)
        geometry = feature.GetGeometryRef()
        valid = geometry is not None and not geometry.IsEmpty() and ogr.GT_Flatten(geometry.GetGeometryType()) == ogr.wkbPoint
        x, y = (geometry.GetX(), geometry.GetY()) if valid else (None, None)
        valid = valid and math.isfinite(x) and math.isfinite(y)
        record = dict(id=identifier, teryt=str(data['TERYT_GMI'] or '').strip(),
                      x=x, y=y, valid_geometry=valid, commission=data['NR_KOMISJI'],
                      street=data.get('NAZWA_ULC'), number=data.get('NUMER_PORZ'), data=data)
        if valid and record['teryt'] and data['STATUS'] == 'PRZYPISANY' and data['NR_KOMISJI'] is not None:
            committees = str(data['KOMISJE_STALE'] or '').split('|')
            if committees != [str(data['NR_KOMISJI'])]:
                raise ValueError(f'Niespójne przypisanie punktu referencyjnego: {identifier}')
            candidates[record['teryt']].append(record)
        elif data['STATUS'] == 'BRAK_PRZYPISANIA' and data['NR_KOMISJI'] is None:
            targets.append(record)
    decisions, audit = {}, []
    for target in targets:
        neighbors = []
        if args.teryt and target['teryt'] != args.teryt:
            winner, status, counts = None, 'POZA_WYBRANA_GMINA', Counter()
        elif not target['valid_geometry']:
            winner, status, counts = None, 'BRAK_GEOMETRII', Counter()
        elif not target['teryt']:
            winner, status, counts = None, 'BRAK_TERYT', Counter()
        else:
            neighbors = nearest(target, candidates[target['teryt']], args.k, args.max_distance)
            winner, status, counts = vote(neighbors, args.k)
            if not neighbors:
                status = 'BRAK_SASIADOW'
        serialized = json.dumps([dict(ID_IIP=n['id'], NR_KOMISJI=n['commission'],
                                     ODLEGLOSC_M=round(n['distance_m'], 3),
                                     NAZWA_ULC=n['street'], NUMER_PORZ=n['number'])
                                 for n in neighbors], ensure_ascii=False)
        votes = json.dumps(dict(sorted(counts.items())), ensure_ascii=False)
        max_votes = max(counts.values(), default=0)
        update = dict(NR_KOMISJI_PRZED=target['commission'], STATUS_PRZED=target['data']['STATUS'],
                      SAS_METODA='KNN_GLOSOWANIE', SAS_STATUS=status,
                      SAS_K=len(neighbors), SAS_GLOSY=max_votes,
                      SAS_UDZIAL=max_votes / len(neighbors) if neighbors else None,
                      SAS_DMIN=min((n['distance_m'] for n in neighbors), default=None),
                      SAS_DMAX=max((n['distance_m'] for n in neighbors), default=None),
                      SAS_WYNIK_GLOSOW=votes, SAS_SASIEDZI=serialized)
        if winner is not None:
            update.update(NR_KOMISJI=winner, KOMISJE_STALE=str(winner), STATUS='PRZYPISANY_SASIEDZTWO')
        decisions[target['id']] = update
        audit.append(dict(ID_IIP=target['id'], TERYT_GMI=target['teryt'],
                          NAZWA_ULC=target['street'], NUMER_PORZ=target['number'],
                          NR_KOMISJI_NOWA=winner, **{f: v for f, v in update.items() if f.startswith('SAS_')}))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    driver = ogr.GetDriverByName('GPKG')
    if args.output.exists():
        driver.DeleteDataSource(str(args.output))
    output = driver.CreateDataSource(str(args.output))
    target_layer = output.CopyLayer(layer, 'adresy_komisje_sasiedztwo', ['SPATIAL_INDEX=YES'])
    if target_layer is None:
        raise RuntimeError('Nie udało się skopiować warstwy')
    additions = dict(NR_KOMISJI_PRZED=ogr.OFTInteger, STATUS_PRZED=ogr.OFTString,
                     SAS_METODA=ogr.OFTString, SAS_STATUS=ogr.OFTString,
                     SAS_K=ogr.OFTInteger, SAS_GLOSY=ogr.OFTInteger,
                     SAS_UDZIAL=ogr.OFTReal, SAS_DMIN=ogr.OFTReal, SAS_DMAX=ogr.OFTReal,
                     SAS_WYNIK_GLOSOW=ogr.OFTString, SAS_SASIEDZI=ogr.OFTString)
    for name, field_type in additions.items():
        target_layer.CreateField(ogr.FieldDefn(name, field_type))
    updates = []
    for feature in target_layer:
        decision = decisions.get(feature['ID_IIP'])
        if decision:
            updates.append((feature.GetFID(), decision))
    output.StartTransaction()
    for fid, decision in updates:
        feature = target_layer.GetFeature(fid)
        for name, value in decision.items():
            if value is not None:
                feature.SetField(name, value)
        target_layer.SetFeature(feature)
    output.CommitTransaction()
    output = None
    # Kontrola zapisanej warstwy, wszystkich geometrii i niezależnych przypisań.
    saved = ogr.Open(str(args.output), 0)
    saved_layer = saved.GetLayer(0)
    assert saved_layer.GetFeatureCount() == layer.GetFeatureCount()
    assert saved_layer.GetSpatialRef().IsSame(srs)
    originals = {f['ID_IIP']: f.Clone() for f in layer}
    for feature in saved_layer:
        original = originals[feature['ID_IIP']]
        geometry, old_geometry = feature.GetGeometryRef(), original.GetGeometryRef()
        assert (geometry is None and old_geometry is None) or (geometry is not None and old_geometry is not None and geometry.ExportToWkb() == old_geometry.ExportToWkb())
        decision = decisions.get(feature['ID_IIP'], {})
        for name in fields:
            assert feature[name] == decision.get(name, original[name]), f'{feature["ID_IIP"]}: {name}'
    report_path = args.output.with_name(args.output.stem + '_raport.csv')
    audit_fields = ['ID_IIP', 'TERYT_GMI', 'NAZWA_ULC', 'NUMER_PORZ', 'NR_KOMISJI_NOWA'] + [n for n in additions if n.startswith('SAS_')]
    write_csv(report_path, audit_fields, audit)
    all_fields = [f.GetName() for f in saved_layer.schema]
    write_csv(args.output.with_suffix('.csv'), all_fields, (dict(f.items()) for f in saved_layer))
    summary = dict(k=args.k, max_odleglosc_m=args.max_distance, teryt=args.teryt,
                   punkty=layer.GetFeatureCount(), analizowane=len(targets),
                   decyzje=dict(Counter(r['SAS_STATUS'] for r in audit)),
                   punkty_referencyjne={k: len(v) for k, v in candidates.items()},
                   wejscie=str(args.input.resolve()), wynik=str(args.output.resolve()))
    args.output.with_name(args.output.stem + '_podsumowanie.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=BASE / 'wyniki_PRG_Geoportal/02_przypisanie/adresy_komisje_PRG.gpkg')
    parser.add_argument('--layer', default='adresy_komisje_PRG')
    parser.add_argument('--output', type=Path, default=BASE / 'wyniki_PRG_Geoportal/04_sasiedztwo/adresy_komisje_sasiedztwo.gpkg')
    parser.add_argument('--k', type=int, default=5)
    parser.add_argument('--max-distance', type=float, help='Maksymalna odległość sąsiada w metrach; domyślnie bez limitu')
    parser.add_argument('--teryt', help='Opcjonalnie ogranicz analizę do jednej gminy, np. 0663011')
    parser.add_argument('--overwrite', action='store_true')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
