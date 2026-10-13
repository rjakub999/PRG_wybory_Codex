import unittest
from przypisz_adresy_PRG import parse_restriction, split_rule, check_feature_type, expand_cells
from rozbij_granice import StreetIndex


class AddressTests(unittest.TestCase):
    def test_parity_and_letter_boundaries(self):
        rule = parse_restriction('1 - 41 (nieparzyste)')
        self.assertTrue(rule.accepts('41A'))
        self.assertFalse(rule.accepts('42'))
        self.assertFalse(rule.accepts('43'))
        rule = parse_restriction('53 - 83B (nieparzyste)')
        self.assertTrue(rule.accepts('83B'))
        self.assertFalse(rule.accepts('83C'))

    def test_open_and_exact(self):
        self.assertFalse(parse_restriction('od 37A do końca (nieparzyste)').accepts('37'))
        self.assertTrue(parse_restriction('od 37A do końca (nieparzyste)').accepts('39'))
        self.assertFalse(parse_restriction('2').accepts('2A'))
        self.assertTrue(parse_restriction('2, 4A, 6').accepts('4a'))

    def test_complex_number_is_not_guessed(self):
        self.assertTrue(parse_restriction('').accepts('7/9/3'))
        with self.assertRaises(ValueError):
            parse_restriction('(nieparzyste)').accepts('7/9/3')

    def test_unknown_rule_fails_closed(self):
        for text in ['1 - 10 oprócz 5', 'od 10 do 2', '(nieparzyste, parzyste)']:
            with self.assertRaises(ValueError):
                parse_restriction(text)

    def test_street_with_digit(self):
        index = StreetIndex([{'NAZWA_ULC': '3 Maja', 'NAZWA_MSC': 'Lublin'}])
        name, rule = split_rule('3 Maja 11', index)
        self.assertEqual(name, '3 Maja')
        self.assertTrue(rule.accepts('11'))
        self.assertFalse(rule.accepts('3'))

    def test_square_is_not_street(self):
        with self.assertRaises(ValueError):
            check_feature_type('pl. Jana Kochanowskiego', 'Jana Kochanowskiego')
        check_feature_type('pl. Plac Litewski', 'Plac Litewski')

    def test_missing_parenthesis_recovery(self):
        from types import SimpleNamespace
        row = [SimpleNamespace(value='Królowej Jadwigi 1 - 23 (nieparzyste, ul. Królowej Jadwigi 2 - 10 (parzyste)')]
        cells = list(expand_cells(row, [('Granica_01', 1)]))
        self.assertEqual(len(cells), 2)
        self.assertTrue(cells[0][1].endswith('(nieparzyste)'))
        self.assertTrue(cells[0][2])


if __name__ == '__main__':
    unittest.main()
