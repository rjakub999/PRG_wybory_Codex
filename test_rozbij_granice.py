"""Testy semantyki parsera: python -m unittest test_rozbij_granice.py."""
import unittest
from rozbij_granice import StreetIndex, resolve, split_description, prg_layer_name


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.index = StreetIndex([{'NAZWA_ULC': n, 'NAZWA_MSC': 'Lublin'} for n in
                                  ['3 Maja', 'Dolna 3 Maja', 'Sadowa', 'Sądowa',
                                   'aleje Racławickie', 'Dra Kazimierza Jaczewskiego',
                                   'Krańcowa', 'Aleja Kraśnicka']])

    def test_numeric_street_names(self):
        self.assertEqual(resolve('ul. 3 Maja (parzyste)', self.index)[0], '3 Maja (parzyste)')
        self.assertEqual(resolve('ul. Dolna 3 Maja 2 - 8', self.index)[0], 'Dolna 3 Maja 2 - 8')

    def test_distinct_polish_names(self):
        for name in ['Sądowa', 'Sadowa']:
            self.assertEqual(resolve('ul. ' + name, self.index)[0], name)

    def test_aliases_and_restrictions(self):
        self.assertEqual(resolve('al. Racławickie 23', self.index)[0], 'aleje Racławickie 23')
        self.assertEqual(resolve('Kazimierza Jaczewskiego 8', self.index)[0], 'Dra Kazimierza Jaczewskiego 8')
        self.assertEqual(resolve('ul. Krańcowa od 107 do końca (nieparzyste)', self.index)[0],
                         'Krańcowa od 107 do końca (nieparzyste)')

    def test_commas(self):
        self.assertEqual(split_description('ULICA: Krańcowa 1, 3, 5, 3 Maja 2'),
                         ['Krańcowa 1, 3, 5', '3 Maja 2'])
        self.assertEqual(split_description('ul. Krańcowa (1, 3), ul. Sądowa'),
                         ['ul. Krańcowa (1, 3)', 'ul. Sądowa'])

    def test_no_guessed_names(self):
        self.assertEqual(resolve('ul. Krancowwa 5', self.index)[:2],
                         ('ul. Krancowwa 5', 'BRAK_W_PRG'))

    def test_geoportal_layer_names(self):
        names = ['PRG_PunktyAdresowe_066301_eksport', 'PRG_Ulice_066301_eksport']
        self.assertEqual(prg_layer_name(names, 'points'), names[0])
        self.assertEqual(prg_layer_name(names, 'streets'), names[1])
        with self.assertRaises(ValueError):
            prg_layer_name(names + ['PRG_PunktyAdresowe_inne'], 'points')


if __name__ == '__main__':
    unittest.main()
