import unittest
from math import pi as π

from common import Spacing, Point, Rect, Extent


class GeomTests(unittest.TestCase):

    def test_margins(self):
        m = Spacing(5, 10, 11, 12)
        self.assertEqual(m, Spacing(5, 10, 11, 12))
        self.assertNotEqual(m, Spacing(5, 11, 11, 12))
        self.assertEqual(15, m.horizontal)
        self.assertEqual(23, m.vertical)
        self.assertEqual(Spacing.balanced(7), Spacing(7, 7, 7, 7))

    def test_point_reps(self):
        a = Point(0, 0)
        b = Point(3.0, 4.5)

        self.assertEqual(str(a), '(0, 0)')
        self.assertEqual(str(b), '(3, 4.5)')
        self.assertEqual(repr(a), 'Point(x=0, y=0)')
        self.assertEqual(repr(b), 'Point(x=3.0, y=4.5)')

        self.assertEqual(hash(a), hash(Point(0, 0)))
        self.assertEqual(hash(b), hash(Point(3, 4.5)))

    def test_extent_reps(self):
        self.assertEqual('(1.1 ⨯ 10.0)', str(Extent(1.1234546, 9.98765)))
        self.assertEqual('(1 ⨯ -9)', str(Extent(1, -9)))

    def test_extent_addition(self):
        e = Extent(100, 200)
        self.assertEqual(Extent(103, 207), e + Extent(3, 7))
        self.assertEqual(Extent(130, 270), e + (30, 70))
        self.assertEqual(Extent(109, 211), e + Spacing(left=1, right=8, top=4, bottom=7))

    def test_extent_subtraction(self):
        e = Extent(100, 200)
        self.assertEqual(Extent(97, 193), e - Extent(3, 7))
        self.assertEqual(Extent(70, 130), e - (30, 70))
        self.assertEqual(Extent(91, 189), e - Spacing(left=1, right=8, top=4, bottom=7))

    def test_point_unary(self):
        assert -Point(3.0, -4.1) == Point(-3, 4.1)
        assert abs(Point(3.0, 4)) == 5
        assert Point(3.0, 4)
        assert not Point(0, 0)
        assert round(Point(3.4, 5.6)) == Point(3, 6)

    def test_point_and_value(self):
        assert Point(1, 3) * 7 == Point(7, 21)
        assert 5 * Point(1, 3) == Point(5, 15)
        assert Point(10, 22) / 10 == Point(1, 2.2)
        assert Point(10, 22) // 10 == Point(1, 2)

    def test_two_points(self):
        assert Point(1, 4) + Point(5, -7) == Point(6, -3)
        assert Point(1, 4) - Point(5, -7) == Point(-4, 11)

    def test_point_polar(self):
        p1 = Point.from_polar(-π / 2, 3)
        self.assertAlmostEqual(0, p1.x)
        self.assertAlmostEqual(-3, p1.y)
        assert Point(1, 1).to_polar() == (π / 4, 2 ** 0.5)

    def test_rect_basics(self):
        r = Rect(3, 13, 12, 32)
        self.assertEqual(10, r.width)
        self.assertEqual(20, r.height)
        self.assertEqual(200, r.area)
        self.assertEqual(60, r.perimeter)
        self.assertEqual(Extent(10, 20), r.extent)
        self.assertEqual(Point(8, 22), r.center)

    def test_rect_add_sub(self):
        r = Rect(3, 13, 12, 32)
        self.assertEqual(Rect(103, 113, 212, 232), r + Point(100, 200))
        self.assertEqual(Rect(2, 12, 10, 30), r - Point(1, 2))

        self.assertEqual(Rect(103, 113, 212, 232), r + (100, 200))
        self.assertEqual(Rect(2, 12, 10, 30), r - (1, 2))

        self.assertEqual(Rect(2, 15, 9, 36), r + Spacing(1, 2, 3, 4))
        self.assertEqual(Rect(4, 11, 15, 28), r - Spacing(1, 2, 3, 4))

    def test_rect_union(self):
        r1 = Rect(3, 13, 12, 32)
        r2 = Rect(6, 7, 15, 15)
        self.assertEqual(r1, Rect.union(r1, r2))
        r3 = Rect(1, 6, 15, 16)
        self.assertEqual(Rect(1, 13, 12, 32), Rect.union(r1, r2, r3))
