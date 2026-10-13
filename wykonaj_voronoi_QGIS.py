"""Voronoi i agregacja pól TERYT_GMI, NR_KOMISJI w QGIS Processing."""
import json
import argparse
import os
import sys
from pathlib import Path

from qgis.core import (QgsApplication, QgsVectorLayer, QgsVectorFileWriter,
                       QgsProcessingFeedback, QgsProject)

BASE = Path(__file__).resolve().parent
QgsApplication.setPrefixPath(os.environ['QGIS_PREFIX_PATH'], True)
app = QgsApplication([], False)
app.initQgis()
sys.path.insert(0, str(Path(QgsApplication.prefixPath()) / 'python' / 'plugins'))
import processing
from qgis.analysis import QgsNativeAlgorithms
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, default=BASE / 'wyniki_PRG_Geoportal/02_przypisanie/adresy_komisje_PRG.gpkg')
parser.add_argument('--layer', default='adresy_komisje_PRG')
parser.add_argument('--output', type=Path, default=BASE / 'wyniki_PRG_Geoportal/03_voronoi/voronoi_komisje_PRG.gpkg')
args = parser.parse_args()
input_path, output_path = args.input, args.output
output_path.parent.mkdir(parents=True, exist_ok=True)
if output_path.exists():
    raise FileExistsError(f'Wynik już istnieje: {output_path}')
points = QgsVectorLayer(str(input_path) + '|layername=' + args.layer, 'Adresy PRG', 'ogr')
if not points.isValid():
    raise ValueError('Nie można odczytać punktów wejściowych')
feedback = QgsProcessingFeedback()
feedback.reportError = lambda message, fatalError=False: print('QGIS:', message, flush=True)
print(f'Voronoi: {points.featureCount()} punktów, {points.crs().authid()}', flush=True)
voronoi = processing.run('native:voronoipolygons', {
    'INPUT': points, 'BUFFER': 0, 'TOLERANCE': 0,
    'COPY_ATTRIBUTES': True, 'OUTPUT': 'memory:'}, feedback=feedback)['OUTPUT']
print(f'Voronoi: {voronoi.featureCount()} poligonów', flush=True)
aggregated = processing.run('native:dissolve', {
    'INPUT': voronoi, 'FIELD': ['TERYT_GMI', 'NR_KOMISJI'],
    'SEPARATE_DISJOINT': False, 'OUTPUT': 'memory:'}, feedback=feedback)['OUTPUT']
print(f'Agregacja: {aggregated.featureCount()} obiektów', flush=True)
for i, (layer, name) in enumerate([(voronoi, 'voronoi_adresy'), (aggregated, 'komisje_agregowane')]):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = 'GPKG'
    options.layerName = name
    options.actionOnExistingFile = (QgsVectorFileWriter.CreateOrOverwriteFile if i == 0
                                    else QgsVectorFileWriter.CreateOrOverwriteLayer)
    result = QgsVectorFileWriter.writeAsVectorFormatV3(layer, str(output_path),
                                                      QgsProject.instance().transformContext(), options)
    if result[0] != QgsVectorFileWriter.NoError:
        raise RuntimeError(str(result))
    saved = QgsVectorLayer(str(output_path) + '|layername=' + name, name, 'ogr')
    if not saved.isValid() or saved.featureCount() != layer.featureCount():
        raise ValueError(f'Błąd zapisanej warstwy {name}')
    invalid = sum(not f.geometry().isGeosValid() for f in saved.getFeatures())
    if invalid:
        raise ValueError(f'{name}: niepoprawne geometrie: {invalid}')
groups = {(f['TERYT_GMI'], f['NR_KOMISJI']) for f in voronoi.getFeatures()}
assert aggregated.featureCount() == len(groups), 'Liczba grup niezgodna z agregacją'
area_before = sum(f.geometry().area() for f in voronoi.getFeatures())
area_after = sum(f.geometry().area() for f in aggregated.getFeatures())
assert abs(area_before - area_after) <= max(0.01, area_before * 1e-8), 'Zmiana sumy powierzchni'
summary = dict(punkty=points.featureCount(), poligony_voronoi=voronoi.featureCount(),
               grupy_agregacji=aggregated.featureCount(), crs=points.crs().authid(),
               pola_agregacji=['TERYT_GMI', 'NR_KOMISJI'], buffer=0, tolerance=0,
               powierzchnia_voronoi_m2=area_before, powierzchnia_agregacji_m2=area_after)
(output_path.parent / 'podsumowanie_voronoi.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
print(str(output_path), flush=True)
app.exitQgis()
