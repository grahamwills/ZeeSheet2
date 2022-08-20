import math
import unittest
from dataclasses import dataclass

from layout import packing
from layout.content import Content, PlacedContent, Error
from layout.geom import Spacing, Extent, Rect

NO_SPACING = Spacing(0, 0, 0, 0)


@dataclass
class TestContent(Content):
    area: int


def place_test_content_with_wrapping(content: Content, e: Extent) -> PlacedContent:
    height = math.ceil(content.area / e.width)
    error = Error(0, 0, 0)
    return PlacedContent(content, e, Extent(e.width, height), error)


class PackingTest(unittest.TestCase):

    def test_no_padding_margins(self):
        items = [TestContent(i) for i in (500, 1000, 200)]
        packer = packing.Packer(items, place_test_content_with_wrapping, NO_SPACING, NO_SPACING)
        group = packer.into_columns(100)
        self.assertEqual(Rect(0, 100, 0, 5), group.placed_group[0].bounds)
        self.assertEqual(Rect(0, 100, 5, 15), group.placed_group[1].bounds)
        self.assertEqual(Rect(0, 100, 15, 17), group.placed_group[2].bounds)
        self.assertEqual(Rect(0, 100, 0, 17), group.bounds)

    def test_margins_no_padding(self):
        items = [TestContent(i) for i in (500, 1000, 200)]
        margins = Spacing(3, 47, 13, 17)
        packer = packing.Packer(items, place_test_content_with_wrapping, margins, NO_SPACING)
        group = packer.into_columns(100)
        self.assertEqual(Rect(3, 53, 13, 23), group.placed_group[0].bounds)
        self.assertEqual(Rect(3, 53, 23, 43), group.placed_group[1].bounds)
        self.assertEqual(Rect(3, 53, 43, 47), group.placed_group[2].bounds)
        self.assertEqual(Rect(0, 100, 0, 64), group.bounds)

    def test_padding_no_margin(self):
        items = [TestContent(i) for i in (500, 1000, 200)]
        padding = Spacing(3, 47, 13, 17)
        packer = packing.Packer(items, place_test_content_with_wrapping, NO_SPACING, padding)
        group = packer.into_columns(60)
        self.assertEqual(Rect(3, 13, 13, 63), group.placed_group[0].bounds)
        self.assertEqual(Rect(3, 13, 80, 180), group.placed_group[1].bounds)
        self.assertEqual(Rect(3, 13, 197, 217), group.placed_group[2].bounds)
        self.assertEqual(Rect(0, 60, 0, 217), group.bounds)

    def test_padding_margins_and_padding(self):
        items = [TestContent(i) for i in (500, 1000, 200)]
        margins = Spacing(10, 20, 30, 40)
        padding = Spacing(1, 2, 3, 4)
        packer = packing.Packer(items, place_test_content_with_wrapping, margins, padding)
        group = packer.into_columns(100)
        self.assertEqual(Rect(10, 80, 30, 38), group.placed_group[0].bounds)
        self.assertEqual(Rect(10, 80, 42, 57), group.placed_group[1].bounds)
        self.assertEqual(Rect(10, 80, 61, 64), group.placed_group[2].bounds)
        self.assertEqual(Rect(0, 100, 0, 104), group.bounds)
