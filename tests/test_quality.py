import unittest

import layout.quality as quality
from common import Extent, Point
from generate.pdf import TextSegment, CheckboxSegment
from layout import PlacedImageContent, PlacedRectContent, PlacedRunContent, PlacedGroupContent
from structure import ImageDetail
from structure.style import Style


# noinspection PyTypeChecker
class TestQuality(unittest.TestCase):
    POINT = Point(2, 3)
    EXTENT = Extent(1, 1)
    STYLE = Style('foo')

    IMAGE = ImageDetail(2, None, 100, 200)

    SEGMENTS = [TextSegment('hello', POINT, None), CheckboxSegment(True, POINT, None)]

    def test_str_for_decoration(self):
        q = quality.for_decoration('box')
        self.assertEqual('⟨box: NONE⟩', str(q))

    def test_names_for_placed_items(self):
        image = PlacedImageContent(self.EXTENT, self.POINT, None, None, self.IMAGE)
        rect = PlacedRectContent(self.EXTENT, self.POINT, None, None, self.STYLE)
        run = PlacedRunContent(self.EXTENT, self.POINT, None, None, self.SEGMENTS, self.STYLE)

        q = quality.for_decoration(image)
        self.assertEqual('⟨Image#2: NONE⟩', str(q))
        q = quality.for_decoration(rect)
        self.assertEqual('⟨Rect(2, 3, 3, 4): NONE⟩', str(q))
        q = quality.for_decoration(run)
        self.assertEqual('⟨hello☒: NONE⟩', str(q))
        q = quality.for_decoration(PlacedGroupContent(self.EXTENT, self.POINT, None, None, [image, image], 123))
        self.assertEqual('⟨Group(2)-Image: NONE⟩', str(q))
        q = quality.for_decoration(PlacedGroupContent(self.EXTENT, self.POINT, None, None, [], 123))
        self.assertEqual('⟨Group(0): NONE⟩', str(q))
        q = quality.for_decoration(PlacedGroupContent(self.EXTENT, self.POINT, None, None, [run, image, rect], 123))
        self.assertEqual('⟨Group(3)-Image•Rect•Run: NONE⟩', str(q))

    def test_str_for_general(self):
        q = quality.for_image('name', 123, 124, 1000, 3)
        self.assertEqual('⟨name: IMAGE(1), width=124•123, image_shrink=332.3, height=3⟩', str(q))
        q = quality.for_wrapping('name', 123, 124, 4, 5, 300)
        self.assertEqual('⟨name: WRAPPING(1), width=124•123, breaks=4•5, height=300⟩', str(q))
        q = quality.for_wrapping('name', 123, 124, 0, 0, 300)
        self.assertEqual('⟨name: WRAPPING(1), width=124•123, height=300⟩', str(q))

    def test_str_for_groups(self):
        a = quality.for_wrapping('name', 123, 124, 4, 1, 100)
        b = quality.for_wrapping('name', 123, 154, 0, 5, 130)
        c = quality.for_decoration('box')
        q = quality.for_table('name', [300, 400], [[a, b, c], [a, None, c]], 7)

        # Three non-decorative items
        # Total desired width is 700 of which 124+154 is used
        # Bad Breaks are 2x4 (from a)
        # Good Breaks are 2x1 (from a) plus 5 (from c)
        self.assertEqual('⟨name: TABLE(3), width=278•700, unplaced=7, breaks=8•7⟩', str(q))

        # With no unplaced
        q = quality.for_table('name', [300, 400], [[a, b, c], [a, None, c]], 0)
        self.assertEqual('⟨name: TABLE(3), width=278•700, breaks=8•7⟩', str(q))

    def test_str_for_columns(self):
        a = quality.for_wrapping('name', 123, 124, 4, 1, 100)
        b = quality.for_wrapping('name', 123, 154, 0, 5, 130)
        c = quality.for_decoration('box')
        q = quality.for_columns('name', [300, 400], [20, 90], [[a, b, c, c], [a, None, c]], 7)

        # Max height is 90, standard deviation = 35
        self.assertEqual('⟨name: COLUMNS(3), width=278•700, unplaced=7, breaks=8•7, height=90~35⟩', str(q))
