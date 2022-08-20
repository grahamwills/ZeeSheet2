import unittest

from layout.content import Error, PlacedContent, Content, PlacedGroupContent, GroupContent
from layout.geom import Extent, Point, Rect


class ContentTest(unittest.TestCase):

    def test_error(self):
        e1 = Error(3.0, 4.0, 5.125)
        self.assertEqual('Error(3.0, 4.0 • 5.12)', str(e1))
        e2 = Error(5, 6, 7)
        self.assertEqual(Error(8.0, 10.0, 12.125), Error.sum(e1, e2))

    def test_group_from_items(self):
        outer = Extent(150, 500)
        p1 = PlacedContent(Content(), outer, Extent(90, 100), Error(1, 2, 3), Point(0, 0))
        p2 = PlacedContent(Content(), outer, Extent(120, 110), Error(1, 2, 3), Point(0, 100))
        p3 = PlacedGroupContent.from_items([p1, p2], outer, Extent(120, 210))
        self.assertEqual(GroupContent([Content(), Content()]), p3.content)
        self.assertEqual(outer, p3.requested)
        self.assertEqual(Point(0, 0), p3.location)
        self.assertEqual(Rect(0, 120, 0, 210), p3.bounds)
        self.assertEqual(Extent(120, 210), p3.actual)
        self.assertEqual(Error(2, 4, 6), p3.error)
