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

    # def test_divide_space_simple(self):
    #     packer = packing.Packer([], None, NO_SPACING)
    #     cols = [round(c) for c in packer.divide_width(100, 3)]
    #     self.assertEqual([ColumnSpan(0, 0, 33), ColumnSpan(1, 33, 67), ColumnSpan(2, 67, 100)], cols)
    #
    # def test_divide_space_complex(self):
    #     packer = packing.Packer([], None, margins=Spacing.balanced(5))
    #     cols = [round(c) for c in packer.divide_width(100, 3)]
    #     self.assertEqual([ColumnSpan(0, 5, 32), ColumnSpan(1, 37, 63), ColumnSpan(2, 68, 95)], cols)
    #
    # def test_no_padding_margins(self):
    #     items = [TestContent(i) for i in (500, 1000, 200)]
    #     packer = packing.Packer(items, place_test_content_with_wrapping, NO_SPACING)
    #     group = packer.into_columns(100, 1)
    #     self.assertEqual(Rect(0, 100, 0, 5), round(group.group[0].bounds))
    #     self.assertEqual(Rect(0, 100, 5, 15), round(group.group[1].bounds))
    #     self.assertEqual(Rect(0, 100, 15, 17), round(group.group[2].bounds))
    #     self.assertEqual(Rect(0, 100, 0, 17), round(group.bounds))
    #
    # def test_margins(self):
    #     items = [TestContent(i) for i in (500, 1000, 200)]
    #     margins = Spacing(3, 47, 13, 17)
    #     packer = packing.Packer(items, place_test_content_with_wrapping, margins)
    #     group = packer.into_columns(100, 1)
    #     self.assertEqual(Rect(3, 53, 13, 23), round(group.group[0].bounds))
    #     self.assertEqual(Rect(3, 53, 40, 60), round(group.group[1].bounds))
    #     self.assertEqual(Rect(3, 53, 77, 81), round(group.group[2].bounds))
    #     self.assertEqual(Rect(0, 100, 0, 98), round(group.bounds))
    #
    # def test_three_columns_equal(self):
    #     items = [TestContent(i) for i in (1500, 1000, 200, 500, 500, 500, 500)]
    #     margins = Spacing.balanced(10)
    #     packer = packing.Packer(items, place_test_content_with_wrapping, margins)
    #     group = packer.into_columns(220, ncol=3, equal=True)
    #
    #     bds = [round(g.bounds) for g in group.group]
    #
    #     # Columns should place items into columns 0 -> {0}, 1 -> {1,2,3}, 3 -> {4,5,6}
    #     # Each column should have width = 60
    #     self.assertEqual(10, bds[0].left)
    #     self.assertEqual(70, bds[0].right)
    #
    #     self.assertEqual(80, bds[1].left)
    #     self.assertEqual(140, bds[1].right)
    #     self.assertEqual(80, bds[2].left)
    #     self.assertEqual(140, bds[2].right)
    #     self.assertEqual(80, bds[3].left)
    #     self.assertEqual(140, bds[3].right)
    #
    #     self.assertEqual(150, bds[4].left)
    #     self.assertEqual(210, bds[4].right)
    #     self.assertEqual(150, bds[5].left)
    #     self.assertEqual(210, bds[5].right)
    #     self.assertEqual(150, bds[6].left)
    #     self.assertEqual(210, bds[6].right)
    #
    #     # self.assertEqual(Rect(0, 204, 0, 64), group.bounds)

    def test_combinations(self):
        cp = TestPacker(Rect(0, 400, 0, 500), item_count=8, column_count=3, granularity=50)
        cc = ' '.join(str(c) for c in cp.column_count_possibilities())
        cw = ' '.join(str([int(v) for v in c]) for c in cp.column_width_possibilities())
        self.assertEqual('[2, 3, 3] [3, 2, 3] [3, 3, 2] [2, 2, 4] [2, 4, 2] [4, 2, 2] [1, 3, 4] [3, 1, 4] '
                         '[3, 4, 1] [4, 3, 1] [1, 4, 3] [4, 1, 3] [1, 2, 5] [1, 5, 2] [2, 1, 5] [2, 5, 1] '
                         '[5, 1, 2] [5, 2, 1] [1, 1, 6] [1, 6, 1] [6, 1, 1]', cc)
        self.assertEqual('[100, 150, 150] [150, 100, 150] [150, 150, 100] [100, 100, 200] [100, 200, 100] '
                         '[200, 100, 100] [50, 150, 200] [150, 50, 200] [150, 200, 50] [200, 150, 50] [50, 200, 150] '
                         '[200, 50, 150] [50, 100, 250] [50, 250, 100] [100, 50, 250] [100, 250, 50] [250, 50, 100] '
                         '[250, 100, 50] [50, 50, 300] [50, 300, 50] [300, 50, 50]', cw)
