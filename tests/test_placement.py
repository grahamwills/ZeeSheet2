import unittest

from common.geom import Extent, Point, Rect
from generate.pdf import PDF, FontInfo
from layout.content import Error
from layout.placement import place_run, split_for_wrap, place_block
from rst.structure import Element, Run, Block, Item


class TestRunPlacement(unittest.TestCase):
    E1 = Element('hello to this ', None)
    E2 = Element('brave new', None)
    E2A = Element('brave new', 'strong')
    E3 = Element(' world', None)
    EX = Element('supercalifragilisticexpialidocious', None)
    pdf = PDF((1000, 1000))

    def test_split_line(self):
        font = FontInfo('Helvetica', 14, False, False)
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
        font = FontInfo('Helvetica', 14, False, False)
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

    def test_bold_font(self):
        run = Run([self.E1, self.E2A, self.E3])
        placed = place_run(run, Extent(200, 100), self.pdf)
        self.assertEqual(3, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to this |brave new| world', texts)
        self.assertEqual('(0, 0)|(75, 0)|(143, 0)', locs)
        self.assertEqual(Rect(0, 181, 0, 16), round(placed.bounds))
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

    def test_not_enough_space_no_matter_what_we_try(self):
        run = Run([self.E1, self.EX, self.E3])
        placed = place_run(run, Extent(80, 60), self.pdf)
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to this |supercalifra|gilisticexpiali', texts)
        self.assertEqual('(0, 0)|(0, 16)|(0, 31)', locs)
        self.assertEqual(Rect(0, 78, 0, 47), round(placed.bounds))
        self.assertEqual(Error(1330, 2, 1, 132), round(placed.error))


def _makeItem(txt: str) -> Item:
    item = Item([Run([Element(txt, None)])])
    item.tidy()
    return item


class TestBlockPlacement(unittest.TestCase):
    title = Run([Element('A simple title', None)])
    pdf = PDF((1000, 1000))

    def test_simple_block(self):
        # Title with line below
        block = Block(self.title, [_makeItem('hello world')])
        placed = place_block(block, Extent(200, 100), self.pdf)
        group = placed.group
        self.assertEqual(2, len(group))
        self.assertEqual(Point(0, 0), group[0].location)
        self.assertEqual(Point(0, 16), round(group[1].location))

    def test_table(self):
        # Title with 5 cells defined by 3 items
        items = [
            _makeItem('hello|this is me'),
            _makeItem('goodbye     | thanks'),
            _makeItem('for all the fish')
        ]
        block = Block(self.title, items)
        placed = place_block(block, Extent(300, 100), self.pdf)
        group = placed.group
        self.assertEqual(6, len(group))

        hello_len = self.pdf.font.width('hello')

        # Title
        self.assertEqual(Point(0, 0), group[0].location)

        # Contents on the grid
        self.assertEqual(Point(0, 16), round(placed.group[1].location))
        self.assertEqual(Point(150, 16), round(placed.group[2].location))
        self.assertEqual(Point(0, 31), round(placed.group[3].location))
        self.assertEqual(Point(150, 31), round(placed.group[4].location))
        self.assertEqual(Point(0, 47), round(placed.group[5].location))
