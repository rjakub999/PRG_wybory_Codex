"""Rozwiń Granica_XX do istniejących punktów PRG i przypisz komisje.

Wymaga GDAL (osgeo.ogr), openpyxl i rozbij_granice.py obok tego pliku.
Domyślnie tworzy CSV do złączenia po ID_IIP oraz warstwę GeoPackage.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from rozbij_granice import BASE, StreetIndex, key, read_prg, resolve, split_description


def number(value):
    match = re.fullmatch(r'(\d+)([^\W\d_]*)', str(value).strip(), re.UNICODE)
    if not match:
        raise ValueError(f'Numer złożony lub niepoprawny: {value}')
    return int(match[1]), match[2].upper()


@dataclass
class Restriction:
    parity: int | None
    intervals: list
    exact: set

    def accepts(self, value):
        # Cała ulica obejmuje również numery złożone w PRG.
        if self.parity is None and not self.intervals and not self.exact:
            return True
        num, letter = number(value)
        if self.parity is not None and num % 2 != self.parity:
            return False
        if not self.intervals and not self.exact:
            return True
        if (num, letter) in self.exact:
            return True
        for lower, upper in self.intervals:
            # Goły koniec 41 obejmuje też 41A; koniec 41B ogranicza litery.
            above = lower is None or num > lower[0] or (num == lower[0] and letter >= lower[1])
            below = upper is None or num < upper[0] or (num == upper[0] and (not upper[1] or letter <= upper[1]))
            if above and below:
                return True
        return False


def parse_restriction(suffix):
    suffix = suffix.strip().casefold().replace('–', '-').replace('—', '-')
    parity = None
    tags = re.findall(r'\(([^()]*)\)', suffix)
    for tag in tags:
        if tag.strip() not in ('parzyste', 'nieparzyste'):
            raise ValueError(f'Nieobsługiwany nawias: {tag}')
        current = 0 if tag.strip() == 'parzyste' else 1
        if parity is not None and parity != current:
            raise ValueError('Sprzeczna parzystość')
        parity = current
    suffix = re.sub(r'\([^()]*\)', '', suffix).strip()
    if not suffix:
        return Restriction(parity, [], set())
    atom = r'\d+[^\W\d_]*'
    intervals, exact = [], set()
    for part in re.split(r'\s*[,;]\s*', suffix):
        open_range = re.fullmatch(fr'od\s+({atom})\s+do\s+końca', part)
        closed = re.fullmatch(fr'(?:od\s+)?({atom})\s*(?:-|do)\s*({atom})', part)
        if open_range:
            intervals.append((number(open_range[1]), None))
        elif closed:
            lower, upper = number(closed[1]), number(closed[2])
            if lower > upper:
                raise ValueError('Odwrócony zakres numerów')
            intervals.append((lower, upper))
        elif re.fullmatch(atom, part):
            exact.add(number(part))
        else:
            raise ValueError(f'Nieobsługiwane ograniczenie: {part}')
    return Restriction(parity, intervals, exact)


def split_rule(fragment, index):
    text, status, _ = resolve(fragment, index)
    if status != 'PRG':
        raise ValueError(f'Nazwa ulicy: {status}')
    names = [name for name in index.names if text == name or text.startswith(name + ' ')]
    name = max(names, key=len)
    return name, parse_restriction(text[len(name):])


def expand_cells(row, boundaries):
    for column, colnum in sorted(boundaries, key=lambda item: int(item[0][8:])):
        original = row[colnum-1].value
        if not original:
            continue
        fragments = re.split(r',\s*(?=ul\.\s)', str(original), flags=re.I)
        for fragment in fragments:
            repaired = len(fragments) > 1
            if re.search(r'\((?:nieparzyste|parzyste)\s*$', fragment, re.I):
                fragment += ')'
                repaired = True
            yield column, fragment, ('NAPRAWA_SEPARATORA_LUB_NAWIASU; oryginał: ' + str(original)) if repaired else ''


def check_feature_type(original, name):
    if re.match(r'^(?:pl\.|plac\b|skwer\b)', original.strip(), re.I) and not re.match(r'^(?:pl\.|plac\b|skwer\b)', name, re.I):
        raise ValueError('Opis źródłowy oznacza plac/skwer, a nazwa PRG ulicę: ' + original)


def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)


def run(args):
    import openpyxl
    from osgeo import ogr
    ogr.UseExceptions()
    output_path = args.output_dir / 'adresy_komisje_PRG.gpkg'
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(f'{output_path}: użyj --overwrite, aby zastąpić wynik')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    index = StreetIndex(read_prg(args.gdb))
    source = ogr.Open(str(args.gdb), 0)
    layer = source.GetLayerByName('PRG_PunktyAdresowe_Lublin')
    if layer is None:
        raise ValueError('Brak warstwy PRG_PunktyAdresowe_Lublin')
    required = {'ID_IIP', 'NAZWA_ULC', 'NUMER_PORZ', 'NAZWA_MSC'}
    if not required <= {f.GetName() for f in layer.schema}:
        raise ValueError('Brak wymaganych pól w punktach PRG')
    points, by_street, identifiers = [], defaultdict(list), set()
    for feature in layer:
        data = dict(feature.items())
        identifier = data['ID_IIP']
        if not identifier or identifier in identifiers:
            raise ValueError(f'Puste lub powtórzone ID_IIP: {identifier}')
        identifiers.add(identifier)
        geometry = feature.GetGeometryRef()
        point = {'data': data, 'geometry': geometry.Clone() if geometry else None,
                 'regular': set(), 'special': set(), 'rules': set(), 'warnings': set()}
        points.append(point)
        if key(data['NAZWA_MSC']) == 'lublin':
            # Zachowaj polskie znaki: Sadowa i Sądowa muszą być odrębne.
            by_street[str(data['NAZWA_ULC'] or '').strip().casefold()].append(point)
    workbook = openpyxl.load_workbook(args.input, read_only=True, data_only=True)
    audit = []
    processed_sheets = 0
    for sheet in workbook:
        headers = {str(c.value).strip(): c.column for c in sheet[1] if c.value is not None}
        boundaries = [(h, c) for h, c in headers.items() if re.fullmatch(r'Granica_\d+', h)]
        if not boundaries:
            continue
        processed_sheets += 1
        if not {'Numer', 'Gmina', 'Typ obwodu'} <= headers.keys():
            raise ValueError(f'{sheet.title}: brak Numer, Gmina lub Typ obwodu')
        for row in sheet.iter_rows(min_row=2, values_only=False):
            rownum = row[0].row
            get = lambda h: row[headers[h]-1].value
            municipality, committee, kind = get('Gmina'), get('Numer'), get('Typ obwodu')
            if committee is None or not str(committee).isdigit():
                raise ValueError(f'{sheet.title}, wiersz {rownum}: niepoprawny numer komisji')
            committee = int(committee)
            originals = split_description(get('Opis granic')) if 'Opis granic' in headers else []
            for column, fragment, repair_note in expand_cells(row, boundaries):
                record = dict(ARKUSZ=sheet.title, WIERSZ=rownum, KOLUMNA=column,
                              NR_KOMISJI=committee, TYP_OBWODU=kind, GRANICA=fragment,
                              STATUS='', LICZBA_PUNKTOW=0, UWAGI=repair_note)
                audit.append(record)
                if key(municipality) not in ('m lublin', 'lublin'):
                    record['STATUS'] = 'POZA_LUBLINEM'
                    continue
                if not kind:
                    raise ValueError(f'Wiersz {rownum}: pusty Typ obwodu')
                try:
                    name, restriction = split_rule(str(fragment), index)
                    ordinal = int(column[8:]) - 1
                    original = originals[ordinal] if ordinal < len(originals) else ''
                    # Pierwszy wynik mógł usunąć oznaczenie placu przy nazwie
                    # patrona. Nie wolno z tego przypisać całej ulicy patrona.
                    check_feature_type(original, name)
                except ValueError as exc:
                    record.update(STATUS='DO_WERYFIKACJI', UWAGI=str(exc))
                    continue
                for point in by_street[name.casefold()]:
                    try:
                        accepted = restriction.accepts(point['data']['NUMER_PORZ'])
                    except ValueError:
                        point['warnings'].add('NUMER_ZLOZONY_DO_WERYFIKACJI')
                        continue
                    if accepted:
                        point['regular' if key(kind) == 'staly' else 'special'].add(committee)
                        point['rules'].add(f'{sheet.title}:{rownum}:{column}')
                        record['LICZBA_PUNKTOW'] += 1
                record['STATUS'] = 'OK' if record['LICZBA_PUNKTOW'] else 'BRAK_PUNKTOW'
    workbook.close()
    if not processed_sheets:
        raise ValueError('Brak kolumn Granica_XX w skoroszycie')
    result = []
    for point in points:
        data, regular, special = point['data'], sorted(point['regular']), sorted(point['special'])
        status = 'PRZYPISANY' if len(regular) == 1 else ('KONFLIKT' if regular else 'BRAK_PRZYPISANIA')
        point['result'] = dict(ID_IIP=data['ID_IIP'], NAZWA_MSC=data['NAZWA_MSC'],
                              NAZWA_ULC=data['NAZWA_ULC'], NUMER_PORZ=data['NUMER_PORZ'],
                              NR_KOMISJI=regular[0] if len(regular) == 1 else None,
                              KOMISJE_STALE='|'.join(map(str, regular)),
                              KOMISJE_ODREBNE='|'.join(map(str, special)), STATUS=status,
                              UWAGI='|'.join(sorted(point['warnings'])),
                              REGULY='|'.join(sorted(point['rules'])))
        result.append(point['result'])
    fields = list(result[0]) if result else []
    if not result:
        raise ValueError('Warstwa PRG nie zawiera punktów')
    write_csv(args.output_dir / 'adresy_komisje_PRG.csv', fields, result)
    write_csv(args.output_dir / 'adresy_do_weryfikacji.csv', fields,
              [r for r in result if r['STATUS'] != 'PRZYPISANY' or r['UWAGI']])
    write_csv(args.output_dir / 'raport_regul.csv', list(audit[0]) if audit else [], audit)
    if output_path.exists():
        if not args.overwrite:
            raise FileExistsError(f'{output_path}: użyj --overwrite, aby zastąpić wynik')
        ogr.GetDriverByName('GPKG').DeleteDataSource(str(output_path))
    output = ogr.GetDriverByName('GPKG').CreateDataSource(str(output_path))
    target = output.CreateLayer('adresy_komisje_PRG', layer.GetSpatialRef(), layer.GetGeomType())
    for field in layer.schema:
        target.CreateField(field)
    extra = [f for f in fields if f not in {f.GetName() for f in layer.schema}]
    for field in extra:
        target.CreateField(ogr.FieldDefn(field, ogr.OFTInteger if field == 'NR_KOMISJI' else ogr.OFTString))
    output.StartTransaction()
    for point in points:
        feature = ogr.Feature(target.GetLayerDefn())
        for field, value in {**point['data'], **point['result']}.items():
            if value is not None:
                feature.SetField(field, value)
        if point['geometry']:
            feature.SetGeometry(point['geometry'])
        target.CreateFeature(feature)
    output.CommitTransaction()
    output = None
    summary = {'punkty_PRG': len(points), 'statusy_adresow': dict(Counter(r['STATUS'] for r in result)),
               'punkty_z_komisjami_odrebnymi': sum(bool(p['special']) for p in points),
               'statusy_regul': dict(Counter(r['STATUS'] for r in audit)),
               'punkty_z_uwagami': sum(bool(r['UWAGI']) for r in result),
               'wejscie': str(args.input.resolve()), 'geobaza': str(args.gdb.resolve())}
    (args.output_dir / 'podsumowanie.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=BASE / 'obwody_glosowania_Lublin_granice.xlsx')
    parser.add_argument('--gdb', type=Path, default=BASE / 'Obwody_PRG_ArcGIS.gdb')
    parser.add_argument('--output-dir', type=Path, default=BASE / 'wyniki_adresy_PRG')
    parser.add_argument('--overwrite', action='store_true', help='Zastąp istniejący GeoPackage wynikowy')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
