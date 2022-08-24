import unittest

from common.geom import Extent, Point, Rect
from generate.pdf import PDF, FontInfo
from layout.content import Error
from layout.placement import place_run, split_for_wrap
from rst.structure import Element, Run


class TestRunPlacement(unittest.TestCase):
    E1 = Element('hello to this ', None)
    E2 = Element('brave new', 'strong')
    E3 = Element(' world', None)
    EX = Element('supercalifragilisticexpialidocious', None)
    pdf = PDF((1000, 1000))

    def test_split_line(self):
        font = FontInfo('Helvetica', 14)
        head, w, tail, bad = split_for_wrap('hello everyone in the room ', 40, font)
        self.assertEqual('hello', head)
        self.assertEqual('everyone in the room ', tail)
        self.assertEqual(font.width('hello'), w)

        head, w, tail, bad = split_for_wrap('hello everyone in the room ', 100, font)
        self.assertEqual('hello everyone', head)
        self.assertEqual('in the room ', tail)
        self.assertEqual(font.width('hello everyone'), w)

        head, w, tail, bad = split_for_wrap('hello everyone in the room ', 120, font)
        self.assertEqual('hello everyone in', head)
        self.assertEqual('the room ', tail)
        self.assertEqual(font.width('hello everyone in'), w)

    def test_split_line_allowing_bad_breaks(self):
        font = FontInfo('Helvetica', 14)
        head, w, tail, bad = split_for_wrap('hello everyone in the room ', 40, font, True)
        self.assertEqual('hello', head)
        self.assertEqual(False, bad)
        self.assertEqual('everyone in the room ', tail)
        self.assertEqual(font.width('hello'), w)

        head, w, tail, bad = split_for_wrap('hello everyone in the room ', 100, font, True)
        self.assertEqual('hello everyone i', head)
        self.assertEqual('n the room ', tail)
        self.assertEqual(True, bad)
        self.assertEqual(font.width('hello everyone i'), w)

        head, w, tail, bad = split_for_wrap('hello everyone in the room ', 120, font, True)
        self.assertEqual('hello everyone in t', head)
        self.assertEqual('he room ', tail)
        self.assertEqual(True, bad)
        self.assertEqual(font.width('hello everyone in t'), w)

    def test_single_plenty_of_space(self):
        run = Run([self.E1])
        placed = place_run(run, Extent(200, 100), self.pdf)
        self.assertEqual(1, len(placed.segments))
        s1 = placed.segments[0]
        self.assertEqual('hello to this ', s1.text)
        self.assertEqual(Point(0, 0), s1.offset)
        self.assertEqual(Rect(0, 75, 0, 16), round(placed.bounds))
        self.assertEqual(Error(0, 0, 0, 0), placed.error)

    def test_multiple_plenty_of_space(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(200, 100), self.pdf)
        self.assertEqual(3, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to this |brave new| world', texts)
        self.assertEqual('(0, 0)|(75, 0)|(139, 0)', locs)
        self.assertEqual(Rect(0, 177, 0, 16), round(placed.bounds))
        self.assertEqual(Error(0, 0, 0, 0), round(placed.error))

    def test_wrapping_1(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(120, 100), self.pdf)
        self.assertEqual(4, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to this |brave|new| world', texts)
        self.assertEqual('(0, 0)|(75, 0)|(0, 16)|(26, 16)', locs)
        self.assertEqual(Rect(0, 110, 0, 31), round(placed.bounds))
        self.assertEqual(Error(0, 0, 1, 726), round(placed.error))

    def test_wrapping_2(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(50, 100), self.pdf)
        self.assertEqual(5, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to|this |brave|new| world', texts)
        self.assertEqual('(0, 0)|(0, 16)|(0, 31)|(0, 47)|(0, 62)', locs)
        self.assertEqual(Rect(0, 45, 0, 78), round(placed.bounds))
        self.assertEqual(Error(0, 0, 4, 883), round(placed.error))

    def test_need_bad_break(self):
        run = Run([self.EX])
        placed = place_run(run, Extent(45, 100), self.pdf)
        self.assertEqual(5, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('superc|alifragil|isticex|pialido|cious', texts)
        self.assertEqual('(0, 0)|(0, 16)|(0, 31)|(0, 47)|(0, 62)', locs)
        self.assertEqual(Rect(0, 44, 0, 78), round(placed.bounds))
        self.assertEqual(Error(0, 4, 0, 362), round(placed.error))

    def test_need_bad_breaks_to_fit_vertically(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(50, 65), self.pdf)
        self.assertEqual(5, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to|this |bra|ve new|world', texts)
        self.assertEqual('(0, 0)|(0, 16)|(26, 16)|(0, 31)|(0, 47)', locs)
        self.assertEqual(Rect(0, 46, 0, 62), round(placed.bounds))
        self.assertEqual(Error(0, 1, 2, 230), round(placed.error))
