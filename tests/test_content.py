import unittest

from layout.content import Error, PlacedContent, Content, PlacedGroupContent, GroupContent
from common.geom import Extent, Point, Rect


class ContentTest(unittest.TestCase):

    def test_error(self):
        e1 = Error(3.0, 4.0, 5.125)
        self.assertEqual('Error(3.0, 4.0 • 5.12)', str(e1))
        e2 = Error(5, 6, 7)
        self.assertEqual(Error(8.0, 10.0, 12.125), Error.sum(e1, e2))

    def test_group_from_items(self):
        p1 = PlacedContent(Content(), Extent(90, 100), Point(0, 0), Error(1, 2, 3))
        p2 = PlacedContent(Content(), Extent(120, 110), Point(0, 100), Error(1, 2, 3))
        p3 = PlacedGroupContent.from_items([p1, p2], Extent(120, 210), 1000)
        self.assertEqual(GroupContent([Content(), Content()]), p3.content)
        self.assertEqual(Point(0, 0), p3.location)
        self.assertEqual(Rect(0, 120, 0, 210), p3.bounds)
        self.assertEqual(Extent(120, 210), p3.extent)
        self.assertEqual(Error(2, 4, 1006), p3.error)
