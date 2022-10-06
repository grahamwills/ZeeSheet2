import unittest

import layout.quality as quality
from common import Extent, Rect, Point
from generate.pdf import TextSegment, CheckboxSegment
from layout import PlacedImageContent, PlacedRectContent, PlacedRunContent, PlacedGroupContent
from structure import ImageDetail
from structure.style import Style

POINT = Point(2, 3)
EXTENT = Extent(1, 1)
STYLE = Style('foo')
BOUNDS = Rect(2, 3, 3, 4)

IMAGE = ImageDetail(2, None, 100, 200)
SEGMENTS = [TextSegment('hello', 2, 3, 12, None), CheckboxSegment(True, 15, 3, 10, None)]

IM_DESIRED = Extent(100, 200)


# noinspection PyTypeChecker
class TestQuality(unittest.TestCase):

    def test_str_for_decoration(self):
        q = quality.for_decoration('box')
        self.assertEqual('⟨box: NONE⟩', str(q))

    def test_names_for_placed_items(self):
        image = PlacedImageContent(IMAGE, IM_DESIRED, 'normal', 'c', Rect(0, 0, 100, 200))
        rect = PlacedRectContent(BOUNDS, STYLE, quality=None)
        run = PlacedRunContent(SEGMENTS, STYLE, EXTENT, quality=None, location=POINT)

        q = quality.for_decoration(image)
        self.assertEqual('⟨Image#2: NONE⟩', str(q))
        q = quality.for_decoration(rect)
        self.assertEqual('⟨Rect(2, 3, 3, 4): NONE⟩', str(q))
        q = quality.for_decoration(run)
        self.assertEqual('⟨hello☒: NONE⟩', str(q))
        q = quality.for_decoration(PlacedGroupContent([image, image], EXTENT, location=POINT, quality=None))
        self.assertEqual('⟨Group(2)-Image: NONE⟩', str(q))
        q = quality.for_decoration(PlacedGroupContent([], EXTENT, location=POINT, quality=None))
        self.assertEqual('⟨Group(0): NONE⟩', str(q))
        q = quality.for_decoration(PlacedGroupContent([run, image, rect], EXTENT, location=POINT, quality=None))
        self.assertEqual('⟨Group(3)-Image•Rect•Run: NONE⟩', str(q))

    def test_str_for_general(self):
        q = quality.for_image('name', 'normal', IM_DESIRED, Rect(0, 80, 0, 100), Rect(0, 100, 0, 200))
        self.assertEqual('⟨name: IMAGE(1), excess=20, image_shrink=2⟩', str(q))
        q = quality.for_wrapping('name', 1, 4, 5)
        self.assertEqual('⟨name: WRAPPING(1), excess=1, breaks=4•5⟩', str(q))
        q = quality.for_wrapping('name', 1, 0, 0)
        self.assertEqual('⟨name: WRAPPING(1), excess=1⟩', str(q))

    def test_str_for_groups(self):
        a = quality.for_wrapping('name', 1, 4, 1)
        b = quality.for_wrapping('name', 31, 0, 5)
        c = quality.for_decoration('box')
        q = quality.for_table('name', [[a, b, c], [a, None, c]], 7)

        # Three non-decorative items
        # Total desired width is 700 of which 124+154 is used
        # Bad Breaks are 2x4 (from a)
        # Good Breaks are 2x1 (from a) plus 5 (from c)
        self.assertEqual('⟨name: TABLE(3), excess=1, unplaced=7, breaks=8•7⟩', str(q))

        # With no unplaced
        q = quality.for_table('name', [[a, b, c], [a, None, c]], 0)
        self.assertEqual('⟨name: TABLE(3), excess=1, breaks=8•7⟩', str(q))

    def test_str_for_columns(self):
        a = quality.for_wrapping('name', 1, 4, 1)
        b = quality.for_wrapping('name', 31, 0, 5)
        c = quality.for_decoration('box')
        q = quality.for_columns('name', [20, 90], [[a, b, c, c], [a, None, c]], 7)

        # Max height is 90, standard deviation = 35
        self.assertEqual('⟨name: COLUMNS(3), excess=1, unplaced=7, breaks=8•7, ∆height=70⟩', str(q))

    def test_compatibility(self):
        a = quality.for_wrapping('name', 1, 4, 1)
        b = quality.for_wrapping('foo', 1, 3, 4)
        c = quality.for_decoration('box')
        d = quality.for_table('name', [[a, b, c], [a, None, b]], 7)
        e = quality.for_table('name', [[a, b, c], [b, None, None]], 8)

        # Does not raise
        a.better(None)
        a.better(b)
        a.better(b)
        d.better(e)

        # Bad types
        self.assertRaises(quality.IncompatibleLayoutQualities, lambda: a.better(c))
        self.assertRaises(quality.IncompatibleLayoutQualities, lambda: a.better(d))


class TestQualityComparisonForNonGroups(unittest.TestCase):

    def test_perfect_and_near_perfect(self):
        a = quality.for_wrapping('perfect', 0, 0, 0)
        self.assertEqual(0, a.minor_score())
        a = quality.for_wrapping('near perfect', 1, 0, 0)
        self.assertTrue(5 > a.minor_score() > 0)
        a = quality.for_wrapping('near perfect', 0, 1, 0)
        self.assertTrue(100 > a.minor_score() > 5)

    def test_bad_versus_good_breaks(self):
        a = quality.for_wrapping('a', 6, 0, 6)
        b = quality.for_wrapping('a', 6, 1, 0)
        c = quality.for_wrapping('a', 6, 0, 20)

        self.assertTrue(a.better(b))
        self.assertTrue(b.better(c))

        self.assertFalse(b.better(a))
        self.assertFalse(c.better(b))

    def test_breaks_versus_excess_space(self):
        no_break_5_pixels = quality.for_wrapping('t', 5, 0, 0)
        one_break_0_pixels = quality.for_wrapping('t', 0, 0, 1)
        no_break_20_pixels = quality.for_wrapping('t', 20, 0, 0)

        self.assertTrue(no_break_5_pixels.better(one_break_0_pixels))
        self.assertTrue(one_break_0_pixels.better(no_break_20_pixels))

    def test_images(self):
        a = quality.for_image('name', 'normal', Extent(100, 200), Rect(0, 100, 0, 100), Rect(0, 1000, 0, 2000))
        b = quality.for_image('name', 'normal', Extent(200, 200), Rect(0, 100, 0, 200), Rect(0, 1000, 0, 2000))
        d1 = quality.for_image('name', 'normal', IM_DESIRED, Rect(0, 100, 0, 200), Rect(0, 220, 0, 200))
        d2 = quality.for_image('name', 'normal', IM_DESIRED, Rect(0, 100, 0, 200), Rect(0, 200, 0, 200))
        self.assertEqual(a.minor_score(), b.minor_score())
        self.assertTrue(d2.better(d1))

    def test_decoration(self):
        self.assertEqual(0, quality.for_decoration('a').minor_score())


class TestQualityComparisonForGroups(unittest.TestCase):

    def test_adding_decoration_changes_nothing(self):
        a = quality.for_wrapping('a', 1, 4, 1)
        b = quality.for_wrapping('b', 31, 0, 5)
        c = quality.for_decoration('decor')

        cols1 = quality.for_table('g', [[a, b, a], [b, b, b]], 3)
        cols2 = quality.for_table('g', [[a, c, b, a], [b, b, b, c]], 3)
        self.assertAlmostEqual(cols1.minor_score(), cols2.minor_score())

        cols1 = quality.for_columns('g', [50, 75], [[a, b, a], [b, b, b]], 3)
        cols2 = quality.for_columns('g', [50, 75], [[a, c, b, a], [b, b, b, c]], 3)
        self.assertAlmostEqual(cols1.minor_score(), cols2.minor_score())

    def test_aggregation(self):
        a = quality.for_wrapping('a', 1, 4, 1)
        b = quality.for_wrapping('b', 31, 0, 5)
        c = quality.for_decoration('decor')
        d = quality.for_image('name', 'normal', Extent(200, 200), Rect(0, 100, 0, 200), Rect(0, 100, 0, 200))
        e = quality.for_image('name', 'normal', Extent(300, 200), Rect(0, 100, 0, 200), Rect(0, 100, 0, 200))

        q = quality.for_table('g', [[a, b, a, c], [a, d, c, e]], 3)
        self.assertEqual(1, q.excess_ss)
        self.assertAlmostEqual(3, q.image_shrinkage, places=2)
        self.assertEqual(12, q.bad_breaks)
        self.assertEqual(8, q.good_breaks)
        self.assertEqual(3, q.unplaced)
        self.assertEqual(None, q.height_dev)

        q = quality.for_columns('g', [50, 70], [[a, b, a, c], [a, d, c, e]], 3)
        self.assertEqual(1, q.excess_ss)
        self.assertAlmostEqual(3, q.image_shrinkage, places=2)
        self.assertEqual(12, q.bad_breaks)
        self.assertEqual(8, q.good_breaks)
        self.assertEqual(3, q.unplaced)
        self.assertEqual(20.0, q.height_dev)

    def test_aggregation_of_aggregations(self):
        a = quality.for_wrapping('a', 1, 7, 1)
        b = quality.for_wrapping('b', 31, 0, 5)
        c = quality.for_decoration('decor')
        d = quality.for_image('name', 'normal', IM_DESIRED, Rect(0, 50, 0, 100), Rect(0, 100, 0, 200))
        e = quality.for_image('name', 'normal', IM_DESIRED, Rect(0, 100, 0, 100), Rect(0, 100, 0, 200))

        t1 = quality.for_table('g', [[a, b], [a, c]], 3)
        t2 = quality.for_table('g', [[d, e], [b, b]], 7)

        q = quality.for_columns('g', [50, 70], [[t1, t1], [t1, t2]], 3)
        self.assertEqual(4, q.excess_ss)
        self.assertAlmostEqual(4.0, q.image_shrinkage, places=2)
        self.assertEqual(6 * 7, q.bad_breaks)
        self.assertEqual(6 * 1 + 5 * 5, q.good_breaks)
        self.assertEqual(3, q.unplaced)
        self.assertEqual(3 * 3 + 7, q.unplaced_descendants)
        self.assertEqual(20.0, q.height_dev)

    def test_image_versus_wrapping(self):
        perfect_text = quality.for_wrapping('a', 0, 0, 0)
        no_break_10_excess = quality.for_wrapping('a', 10, 0, 0)
        no_break_20_excess = quality.for_wrapping('a', 20, 0, 0)
        bad_break_no_excess = quality.for_wrapping('a', 0, 1, 0)

        perfect_image = quality.for_image('name', 'normal', IM_DESIRED, Rect(0, 100, 0, 200), Rect(0, 100, 0, 200))
        slightly_shrunk_image = quality.for_image('name', 'normal', IM_DESIRED, Rect(0, 90, 0, 200),
                                                  Rect(0, 90, 0, 200), )
        half_image = quality.for_image('name', 'normal', IM_DESIRED, Rect(0, 50, 0, 200), Rect(0, 50, 0, 200))

        # Just checking that perfect really is
        self.assertEqual(0, quality.for_table('g', [[perfect_image], [perfect_text]], 3).minor_score())

        a = quality.for_table('g', [[perfect_image], [no_break_10_excess]], 3)
        b = quality.for_table('g', [[slightly_shrunk_image], [perfect_text]], 3)
        c = quality.for_table('g', [[slightly_shrunk_image], [no_break_20_excess]], 3)
        d = quality.for_table('g', [[perfect_image], [bad_break_no_excess]], 3)
        e = quality.for_table('g', [[half_image], [perfect_text]], 3)
        f = quality.for_table('g', [[bad_break_no_excess], [bad_break_no_excess]], 3)

        self.assertTrue(a.better(b))
        self.assertTrue(b.better(c))
        self.assertTrue(b.better(d))
        self.assertTrue(c.better(d))
        self.assertTrue(d.better(e))
        self.assertTrue(e.better(f))

    def test_column_sizes_versus_wrapping(self):
        none = quality.for_wrapping('a', 10, 0, 0)
        one = quality.for_wrapping('a', 10, 0, 1)
        ten = quality.for_wrapping('a', 10, 0, 10)

        no_breaks_5_height_difference = quality.for_columns('t', [100, 105], [[none], [none, none]], 0)
        no_breaks_20_height_difference = quality.for_columns('t', [120, 100], [[none], [none, none]], 0)
        one_break_0_height_difference = quality.for_columns('t', [105, 105], [[none], [none, one]], 0)

        self.assertTrue(no_breaks_5_height_difference.better(one_break_0_height_difference))
        self.assertTrue(one_break_0_height_difference.better(no_breaks_20_height_difference))
