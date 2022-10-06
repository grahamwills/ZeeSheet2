import unittest

from common import Spacing, Rect, items_in_bins_counts, items_in_bins_combinations
from layout.packer import ColumnPacker


class PackingUtilitiesTest(unittest.TestCase):

    def test_bin_counts(self):
        self.assertEqual(6, items_in_bins_counts(5, 3))
        self.assertEqual(171, items_in_bins_counts(20, 3))
        self.assertEqual(82251, items_in_bins_counts(40, 5))
        self.assertEqual(3764376, items_in_bins_counts(100, 5))

    def test_items_into_buckets_combinations_small(self):
        a = ' '.join(str(c) for c in items_in_bins_combinations(5, 2))
        self.assertEqual('[2, 3] [3, 2] [1, 4] [4, 1]', a)
        b = ' '.join(str(c) for c in items_in_bins_combinations(5, 3))
        self.assertEqual('[1, 2, 2] [2, 1, 2] [2, 2, 1] [1, 1, 3] [1, 3, 1] [3, 1, 1]', b)
        c = ' '.join(str(c) for c in items_in_bins_combinations(6, 3))
        self.assertEqual('[2, 2, 2] [1, 2, 3] [1, 3, 2] [2, 1, 3] [2, 3, 1] '
                         '[3, 1, 2] [3, 2, 1] [1, 1, 4] [1, 4, 1] [4, 1, 1]', c)
        d = ' '.join(str(c) for c in items_in_bins_combinations(8, 3))
        self.assertEqual('[2, 3, 3] [3, 2, 3] [3, 3, 2] [2, 2, 4] [2, 4, 2] [4, 2, 2] [1, 3, 4] '
                         '[3, 1, 4] [3, 4, 1] [4, 3, 1] [1, 4, 3] [4, 1, 3] [1, 2, 5] [1, 5, 2] '
                         '[2, 1, 5] [2, 5, 1] [5, 1, 2] [5, 2, 1] [1, 1, 6] [1, 6, 1] [6, 1, 1]', d)
        e = ' '.join(str(c) for c in items_in_bins_combinations(9, 3))
        self.assertEqual('[3, 3, 3] [2, 3, 4] [2, 4, 3] [3, 2, 4] [3, 4, 2] [4, 2, 3] [4, 3, 2] '
                         '[1, 4, 4] [2, 2, 5] [2, 5, 2] [4, 1, 4] [4, 4, 1] [5, 2, 2] [1, 3, 5] '
                         '[1, 5, 3] [3, 1, 5] [3, 5, 1] [5, 1, 3] [5, 3, 1] [1, 2, 6] [1, 6, 2] '
                         '[2, 1, 6] [2, 6, 1] [6, 1, 2] [6, 2, 1] [1, 1, 7] [1, 7, 1] [7, 1, 1]', e)

    def test_items_in_bins_combinations_with_limits(self):
        a = ' '.join(str(c) for c in items_in_bins_combinations(5, 2, limit=2))
        self.assertEqual('[2, 3] [3, 2]', a)
        d = ' '.join(str(c) for c in items_in_bins_combinations(8, 3, limit=5))
        self.assertEqual('[2, 2, 4] [2, 4, 2] [4, 2, 2]', d)
        e = ' '.join(str(c) for c in items_in_bins_combinations(9, 3, limit=5))
        self.assertEqual('[4, 3, 2] [2, 2, 5] [2, 5, 2]', e)

        big = items_in_bins_combinations(103, 10, limit=1000)
        self.assertEqual(145, len(big))
        self.assertTrue(all(sum(x) == 103 for x in big))


class TestPacker(ColumnPacker):

    def margins_of_item(self, item_index: int) -> Spacing:
        return Spacing.balanced(10)


class PackingTest(unittest.TestCase):


    def test_combinations(self):
        cp = TestPacker('test', Rect(0, 400, 0, 500), item_count=8, column_count=3, granularity=50, max_width_combos=100)
        cc = ' '.join(str(c) for c in cp.column_count_possibilities())
        cw = ' '.join(str([int(v) for v in c]) for c in cp.column_width_possibilities())
        self.assertEqual('[2, 3, 3] [3, 2, 3] [3, 3, 2] [2, 2, 4] [2, 4, 2] [4, 2, 2] [1, 3, 4] [3, 1, 4] '
                         '[3, 4, 1] [4, 3, 1] [1, 4, 3] [4, 1, 3] [1, 2, 5] [1, 5, 2] [2, 1, 5] [2, 5, 1] '
                         '[5, 1, 2] [5, 2, 1] [1, 1, 6] [1, 6, 1] [6, 1, 1]', cc)
        self.assertEqual('[100, 150, 150] [150, 100, 150] [150, 150, 100] [100, 100, 200] [100, 200, 100] '
                         '[200, 100, 100] [50, 150, 200] [150, 50, 200] [150, 200, 50] [200, 150, 50] [50, 200, 150] '
                         '[200, 50, 150] [50, 100, 250] [50, 250, 100] [100, 50, 250] [100, 250, 50] [250, 50, 100] '
                         '[250, 100, 50] [50, 50, 300] [50, 300, 50] [300, 50, 50]', cw)
