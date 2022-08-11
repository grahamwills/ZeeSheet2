import unittest
from math import pi as π

from layout.geom import Margins, Point


class GeomTests(unittest.TestCase):

    def test_margins(self):
        m = Margins(5, 10, 11, 12)
        self.assertEqual(m, Margins(5, 10, 11, 12))
        self.assertNotEqual(m, Margins(5, 11, 11, 12))
        self.assertEqual(15, m.horizontal)
        self.assertEqual(23, m.vertical)
        self.assertEqual(Margins.balanced(7), Margins(7, 7, 7, 7))

    def test_point_reps(self):
        a = Point(0, 0)
        b = Point(3.0, 4.5)

        self.assertEqual(str(a), '(0,0)')
        self.assertEqual(str(b), '(3.0,4.5)')
        self.assertEqual(repr(a), 'Point(x=0, y=0)')
        self.assertEqual(repr(b), 'Point(x=3.0, y=4.5)')

        self.assertEqual(hash(a), hash(Point(0, 0)))
        self.assertEqual(hash(b), hash(Point(3, 4.5)))

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
