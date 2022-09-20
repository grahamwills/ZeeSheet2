import unittest

from common import Extent, Point, Rect
from generate.fonts import FontLibrary
from generate.pdf import PDF
from layout.build import make_complete_styles
from layout.content import Error
from layout.placement import place_run, split_for_wrap, place_block
from structure import Element, Run, Block, Item, Sheet
from structure.style import Style, FontStyle


def _make_item(txt: str) -> Item:
    item = Item([Run([Element(txt, None)])])
    item.tidy()
    return item


STYLE = Style('test', font=FontStyle('Helvetica', 14, 'regular'))


class TestRunPlacement(unittest.TestCase):
    E1 = Element('hello to this ')
    E2 = Element('brave new')
    E2A = Element('brave new', 'strong')
    E3 = Element(' world')
    EX = Element('supercalifragilisticexpialidocious')
    pdf = PDF((1000, 1000), font_lib=FontLibrary(), styles=None)

    def test_split_line(self):
        font = self.pdf.font_lib.get_font('Helvetica', 14, False, False)
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
        font = self.pdf.font_lib.get_font('Helvetica', 14, False, False)
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

    def test_split_with_checkboxes(self):
        e = Element('X', 'checkbox')
        run = Run([e] * 13)
        placed = place_run(run, Extent(30, 100), STYLE, self.pdf)
        self.assertEqual(12, len(placed.segments))
        self.assertEqual(Error(221, 0, 0, 2), round(placed.error))

    def test_single_plenty_of_space(self):
        run = Run([self.E1])
        placed = place_run(run, Extent(100, 100), STYLE, self.pdf)
        self.assertEqual(1, len(placed.segments))
        s1 = placed.segments[0]
        self.assertEqual('hello to this ', s1.text)
        self.assertEqual(Point(0, 0), s1.offset)
        self.assertEqual(Error(0, 0, 0, 640), round(placed.error))

    def test_multiple_plenty_of_space(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(200, 100), STYLE, self.pdf)
        self.assertEqual(3, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to this |brave new| world', texts)
        self.assertEqual('(0, 0)|(75, 0)|(139, 0)', locs)
        self.assertEqual(Error(0, 0, 0, 546), round(placed.error))

    def test_run_aligned_right(self):
        run = Run([self.E1, self.E2, self.E3])
        style = Style('test', font=FontStyle('Helvetica', 14, 'regular')).set('align', 'right')
        placed = place_run(run, Extent(300, 100), style, self.pdf)
        self.assertEqual(3, len(placed.segments))
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('(123, 0)|(198, 0)|(263, 0)', locs)

    def test_bold_font(self):
        run = Run([self.E1, self.E2A, self.E3])
        placed = place_run(run, Extent(200, 100), STYLE, self.pdf)
        self.assertEqual(3, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to this |brave new| world', texts)
        self.assertEqual('(0, 0)|(75, 0)|(143, 0)', locs)
        self.assertEqual(Error(0, 0, 0, 380), round(placed.error))

    def test_wrapping_1(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(120, 100), STYLE, self.pdf)
        self.assertEqual(4, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to this |brave|new| world', texts)
        self.assertEqual('(0, 0)|(75, 0)|(0, 16)|(26, 16)', locs)
        self.assertEqual(Error(0, 0, 1, 3247), round(placed.error))

    def test_wrapping_2(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(50, 100), STYLE, self.pdf)
        self.assertEqual(5, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to|this |brave|new| world', texts)
        self.assertEqual('(0, 0)|(0, 16)|(0, 31)|(0, 47)|(0, 62)', locs)
        self.assertEqual(Error(0, 0, 4, 160), round(placed.error))

    def test_need_bad_break(self):
        run = Run([self.EX])
        placed = place_run(run, Extent(45, 100), STYLE, self.pdf)
        self.assertEqual(5, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('superc|alifragil|isticex|pialido|cious', texts)
        self.assertEqual('(0, 0)|(0, 16)|(0, 31)|(0, 47)|(0, 62)', locs)
        self.assertEqual(Error(0, 4, 0, 152), round(placed.error))

    def test_need_bad_breaks_to_fit_vertically(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(50, 65), STYLE, self.pdf)
        self.assertEqual(5, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to|this |bra|ve new|world', texts)
        self.assertEqual('(0, 0)|(0, 16)|(26, 16)|(0, 31)|(0, 47)', locs)
        self.assertEqual(Error(0, 1, 2, 274), round(placed.error))

    def test_not_enough_space_no_matter_what_we_try(self):
        run = Run([self.E1, self.EX, self.E3])
        placed = place_run(run, Extent(80, 60), STYLE, self.pdf)
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str(round(s.offset)) for s in placed.segments)
        self.assertEqual('hello to this |supercalifra|gilisticexpiali', texts)
        self.assertEqual('(0, 0)|(0, 16)|(0, 31)', locs)
        self.assertEqual(Error(1330, 2, 1, 5), round(placed.error))

    def test_split_item_into_cells(self):
        item = _make_item('a | b         \t| c | d ')
        item.tidy()
        self.assertEqual(4, len(item.children))
        self.assertEqual('a', item.children[0].to_rst())
        self.assertEqual('b', item.children[1].to_rst())
        self.assertEqual('c', item.children[2].to_rst())
        self.assertEqual('d', item.children[3].to_rst())


class TestBlockPlacement(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.title = Run([Element('A simple title')])
        styles = Sheet().styles
        styles['default-block'] = Style('default-block').set('padding', '0').set('border', 'none')
        styles = make_complete_styles(styles)

        cls.pdf = PDF((1000, 1000), FontLibrary(), styles=styles)

    def test_empty_block(self):
        # Title by itself
        block = Block(self.title, [])
        placed = place_block(block, Extent(200, 100), self.pdf)
        group = placed.group
        self.assertEqual(2, len(group))
        self.assertEqual(Point(3, 3), group[1].location)

    def test_table(self):
        # Title with 5 cells defined by 3 items
        items = [
            _make_item('hello|this is me'),
            _make_item('goodbye     | thanks'),
            _make_item('for all the fish')
        ]
        block = Block(self.title, items)
        placed = place_block(block, Extent(300, 100), self.pdf)
        group = placed.group
        self.assertEqual(3, len(group))

        # Background
        self.assertEqual(Rect(0, 300, 0, 61), round(group[0].bounds))

        # Main content
        self.assertEqual(Rect(0, 300, 22, 61), round(group[1].bounds))

        # Title content
        self.assertEqual(Rect(0, 300, 0, 22), round(group[2].bounds))

        # Contents on the grid
        self.assertEqual(Point(0, 0), round(placed.group[1].group[0].location))
        self.assertEqual(Point(80, 0), round(placed.group[1].group[1].location))
        self.assertEqual(Point(0, 13), round(placed.group[1].group[2].location))
        self.assertEqual(Point(80, 13), round(placed.group[1].group[3].location))
        self.assertEqual(Point(0, 27), round(placed.group[1].group[4].location))
