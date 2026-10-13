import unittest
from przypisz_sasiedztwo_PRG import nearest, vote


class NeighborhoodTests(unittest.TestCase):
    def test_three_against_two(self):
        winner, status, _ = vote([{'commission': n} for n in [10, 20, 10, 20, 10]], 5)
        self.assertEqual((winner, status), (10, 'PRZYPISANO'))

    def test_plurality_is_enough(self):
        self.assertEqual(vote([{'commission': n} for n in [10, 10, 20, 30, 40]], 5)[0], 10)

    def test_tie_remains_unassigned(self):
        self.assertEqual(vote([{'commission': n} for n in [10, 10, 20, 20, 30]], 5)[:2], (None, 'REMIS'))

    def test_insufficient_neighbors(self):
        self.assertEqual(vote([{'commission': 10}] * 4, 5)[:2], (None, 'ZA_MALO_SASIADOW'))

    def test_distances_and_limit(self):
        target = dict(id='a', x=0, y=0)
        candidates = [dict(id='c', x=3, y=4, commission=2), dict(id='b', x=0, y=2, commission=1)]
        neighbors = nearest(target, candidates, 5, 3)
        self.assertEqual([n['id'] for n in neighbors], ['b'])
        self.assertEqual(neighbors[0]['distance_m'], 2)

    def test_equal_distances_deterministic(self):
        target = dict(id='a', x=0, y=0)
        candidates = [dict(id='c', x=1, y=0), dict(id='b', x=-1, y=0)]
        self.assertEqual(nearest(target, candidates, 1)[0]['id'], 'b')


if __name__ == '__main__':
    unittest.main()
