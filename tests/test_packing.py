import math
import unittest
from dataclasses import dataclass

from common.geom import Spacing, Extent, Rect, Point
from generate.pdf import PDF
from layout import packing
from layout.content import PlacedContent, Error
from layout.packing import ColumnSpan
from rst.structure import StructureComponent

NO_SPACING = Spacing(0, 0, 0, 0)


@dataclass
class TestContent(StructureComponent):
    area: int


def place_test_content_with_wrapping(content: StructureComponent, e: Extent, _:PDF) -> PlacedContent:
    height = math.ceil(content.area / e.width)
    error = Error(0, 0, 0, 0)
    return PlacedContent('test', Extent(e.width, height), Point(0,0), error)


class PackingTest(unittest.TestCase):

    def test_divide_space_simple(self):
        packer = packing.Packer('test',[], None, NO_SPACING, NO_SPACING)
        cols = packer.divide_width(100, 3)
        self.assertEqual([ColumnSpan(0, 0, 33), ColumnSpan(1, 33, 67), ColumnSpan(2, 67, 100)], cols)

    def test_divide_space_complex(self):
        packer = packing.Packer('test',[], None, margin=Spacing.balanced(5), padding=Spacing(1, 10, 5, 5))
        cols = packer.divide_width(100, 3)
        self.assertEqual([ColumnSpan(0, 5, 27), ColumnSpan(1, 37, 58), ColumnSpan(2, 68, 90)], cols)

    def test_no_padding_margins(self):
        items = [TestContent(i) for i in (500, 1000, 200)]
        packer = packing.Packer('test',items, place_test_content_with_wrapping, NO_SPACING, NO_SPACING)
        group = packer.into_columns(100)
        self.assertEqual(Rect(0, 100, 0, 5), group.group[0].bounds)
        self.assertEqual(Rect(0, 100, 5, 15), group.group[1].bounds)
        self.assertEqual(Rect(0, 100, 15, 17), group.group[2].bounds)
        self.assertEqual(Rect(0, 100, 0, 17), group.bounds)

    def test_margins_no_padding(self):
        items = [TestContent(i) for i in (500, 1000, 200)]
        margins = Spacing(3, 47, 13, 17)
        packer = packing.Packer('test',items, place_test_content_with_wrapping, margins, NO_SPACING)
        group = packer.into_columns(100)
        self.assertEqual(Rect(3, 53, 13, 23), group.group[0].bounds)
        self.assertEqual(Rect(3, 53, 23, 43), group.group[1].bounds)
        self.assertEqual(Rect(3, 53, 43, 47), group.group[2].bounds)
        self.assertEqual(Rect(0, 100, 0, 64), group.bounds)

    def test_padding_no_margin(self):
        items = [TestContent(i) for i in (500, 1000, 200)]
        padding = Spacing(3, 47, 13, 17)
        packer = packing.Packer('test',items, place_test_content_with_wrapping, NO_SPACING, padding)
        group = packer.into_columns(60)
        self.assertEqual(Rect(3, 13, 13, 63), group.group[0].bounds)
        self.assertEqual(Rect(3, 13, 80, 180), group.group[1].bounds)
        self.assertEqual(Rect(3, 13, 197, 217), group.group[2].bounds)
        self.assertEqual(Rect(0, 60, 0, 217), group.bounds)

    def test_padding_margins_and_padding(self):
        items = [TestContent(i) for i in (500, 1000, 200)]
        margins = Spacing(10, 20, 30, 40)
        padding = Spacing(1, 2, 3, 4)
        packer = packing.Packer('test',items, place_test_content_with_wrapping, margins, padding)
        group = packer.into_columns(100)
        self.assertEqual(Rect(10, 80, 30, 38), group.group[0].bounds)
        self.assertEqual(Rect(10, 80, 42, 57), group.group[1].bounds)
        self.assertEqual(Rect(10, 80, 61, 64), group.group[2].bounds)
        self.assertEqual(Rect(0, 100, 0, 104), group.bounds)

    def test_three_columns(self):
        items = [TestContent(i) for i in (1500, 1000, 200, 500, 500, 500, 500)]
        margins = Spacing.balanced(10)
        padding = Spacing.balanced(2)
        packer = packing.Packer('test',items, place_test_content_with_wrapping, margins, padding)
        group = packer.into_columns(204, ncol=3)

        bds = [g.bounds for g in group.group]

        # Columns should place items into columns 0 -> {0}, 1 -> {1,2,3}, 3 -> {4,5,6}
        # Each column should have width = 60
        self.assertEqual(10, bds[0].left)
        self.assertEqual(70, bds[0].right)

        self.assertEqual(72, bds[1].left)
        self.assertEqual(132, bds[1].right)
        self.assertEqual(72, bds[2].left)
        self.assertEqual(132, bds[2].right)
        self.assertEqual(72, bds[3].left)
        self.assertEqual(132, bds[3].right)

        self.assertEqual(134, bds[4].left)
        self.assertEqual(194, bds[4].right)
        self.assertEqual(134, bds[5].left)
        self.assertEqual(194, bds[5].right)
        self.assertEqual(134, bds[6].left)
        self.assertEqual(194, bds[6].right)

        # self.assertEqual(Rect(0, 204, 0, 64), group.bounds)
