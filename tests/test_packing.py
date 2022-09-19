import math
import unittest
from dataclasses import dataclass

from common import Spacing, Extent, Rect, Point
from generate.pdf import PDF
from layout import packing
from layout.content import PlacedContent, Error
from layout.packing import ColumnSpan
from structure import StructureUnit

NO_SPACING = Spacing(0, 0, 0, 0)


@dataclass
class TestContent(StructureUnit):
    area: int


def place_test_content_with_wrapping(content: StructureUnit, e: Extent, _: PDF) -> PlacedContent:
    height = math.ceil(content.area / e.width)
    error = Error(0, 0, 0, 0)
    return PlacedContent(Extent(e.width, height), Point(0, 0), error)


class PackingTest(unittest.TestCase):

    def test_divide_space_simple(self):
        packer = packing.Packer([], None, NO_SPACING)
        cols = [round(c) for c in packer.divide_width(100, 3)]
        self.assertEqual([ColumnSpan(0, 0, 33), ColumnSpan(1, 33, 67), ColumnSpan(2, 67, 100)], cols)

    def test_divide_space_complex(self):
        packer = packing.Packer([], None, margins=Spacing.balanced(5))
        cols = [round(c) for c in packer.divide_width(100, 3)]
        self.assertEqual([ColumnSpan(0, 5, 32), ColumnSpan(1, 37, 63), ColumnSpan(2, 68, 95)], cols)

    def test_no_padding_margins(self):
        items = [TestContent(i) for i in (500, 1000, 200)]
        packer = packing.Packer(items, place_test_content_with_wrapping, NO_SPACING)
        group = packer.into_columns(100, 1)
        self.assertEqual(Rect(0, 100, 0, 5), round(group.group[0].bounds))
        self.assertEqual(Rect(0, 100, 5, 15), round(group.group[1].bounds))
        self.assertEqual(Rect(0, 100, 15, 17), round(group.group[2].bounds))
        self.assertEqual(Rect(0, 100, 0, 17), round(group.bounds))

    def test_margins(self):
        items = [TestContent(i) for i in (500, 1000, 200)]
        margins = Spacing(3, 47, 13, 17)
        packer = packing.Packer(items, place_test_content_with_wrapping, margins)
        group = packer.into_columns(100, 1)
        self.assertEqual(Rect(3, 53, 13, 23), round(group.group[0].bounds))
        self.assertEqual(Rect(3, 53, 40, 60), round(group.group[1].bounds))
        self.assertEqual(Rect(3, 53, 77, 81), round(group.group[2].bounds))
        self.assertEqual(Rect(0, 100, 0, 98), round(group.bounds))

    def test_three_columns_equal(self):
        items = [TestContent(i) for i in (1500, 1000, 200, 500, 500, 500, 500)]
        margins = Spacing.balanced(10)
        packer = packing.Packer(items, place_test_content_with_wrapping, margins)
        group = packer.into_columns(220, ncol=3, equal=True)

        bds = [round(g.bounds) for g in group.group]

        # Columns should place items into columns 0 -> {0}, 1 -> {1,2,3}, 3 -> {4,5,6}
        # Each column should have width = 60
        self.assertEqual(10, bds[0].left)
        self.assertEqual(70, bds[0].right)

        self.assertEqual(80, bds[1].left)
        self.assertEqual(140, bds[1].right)
        self.assertEqual(80, bds[2].left)
        self.assertEqual(140, bds[2].right)
        self.assertEqual(80, bds[3].left)
        self.assertEqual(140, bds[3].right)

        self.assertEqual(150, bds[4].left)
        self.assertEqual(210, bds[4].right)
        self.assertEqual(150, bds[5].left)
        self.assertEqual(210, bds[5].right)
        self.assertEqual(150, bds[6].left)
        self.assertEqual(210, bds[6].right)

        # self.assertEqual(Rect(0, 204, 0, 64), group.bounds)
