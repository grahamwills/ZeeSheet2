import unittest

from common import Extent, Point, Rect
from generate.fonts import FontLibrary
from generate.pdf import PDF
from layout import ExtentTooSmallError
from layout.build_block import place_block
from layout.build_run import place_run
from layout.build_sheet import make_complete_styles
from structure import Element, Run, Block, Item, Sheet
from structure.style import Style, FontStyle


def _make_item(txt: str) -> Item:
    item = Item([Run([Element(txt, None)])])
    item.tidy(['test'])
    return item


STYLE = Style('test', font=FontStyle('Helvetica', 14, 'regular'))


class TestRunPlacement(unittest.TestCase):
    E1 = Element('hello to this ')
    E2 = Element('brave new')
    E2A = Element('brave new', 'strong')
    E3 = Element(' world')
    EX = Element('supercalifragilisticexpialidocious')
    pdf = PDF((1000, 1000), font_lib=FontLibrary(), styles={})

    def test_split_with_checkboxes(self):
        e = Element('X', 'checkbox')
        run = Run([e] * 13)
        placed = place_run(run, Extent(30, 200), STYLE, self.pdf)
        self.assertEqual(13, len(placed.segments))
        self.assertEqual("excess=16, breaks=0•6", placed.quality.str_parts())

    def test_single_plenty_of_space(self):
        run = Run([self.E1])
        placed = place_run(run, Extent(100, 100), STYLE, self.pdf)
        self.assertEqual(1, len(placed.segments))
        s1 = placed.segments[0]
        self.assertEqual('hello to this ', s1.text)
        self.assertEqual(0, s1.x)
        self.assertEqual(0, s1.y)
        self.assertEqual("excess=25", placed.quality.str_parts())

    def test_multiple_plenty_of_space(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(200, 100), STYLE, self.pdf)
        self.assertEqual(3, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str((round(s.x), round(s.y))) for s in placed.segments)
        self.assertEqual('hello to this |brave new| world', texts)
        self.assertEqual('(0, 0)|(75, 0)|(139, 0)', locs)
        self.assertEqual("excess=23", placed.quality.str_parts())

    def test_run_aligned_right(self):
        run = Run([self.E1, self.E2, self.E3])
        style = Style('test', font=FontStyle('Helvetica', 14, 'regular')).set('align', 'right')
        placed = place_run(run, Extent(300, 100), style, self.pdf)
        self.assertEqual(3, len(placed.segments))
        locs = '|'.join(str((round(s.x), round(s.y))) for s in placed.segments)
        self.assertEqual('(123, 0)|(198, 0)|(263, 0)', locs)

    def test_bold_font(self):
        run = Run([self.E1, self.E2A, self.E3])
        placed = place_run(run, Extent(200, 100), STYLE, self.pdf)
        self.assertEqual(3, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str((round(s.x), round(s.y))) for s in placed.segments)
        self.assertEqual('hello to this |brave new| world', texts)
        self.assertEqual('(0, 0)|(75, 0)|(143, 0)', locs)
        self.assertEqual("excess=19", placed.quality.str_parts())

    def test_wrapping_1(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(120, 100), STYLE, self.pdf)
        self.assertEqual(4, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str((round(s.x), round(s.y))) for s in placed.segments)
        self.assertEqual('hello to this |brave|new| world', texts)
        self.assertEqual('(0, 0)|(75, 0)|(0, 16)|(26, 16)', locs)
        self.assertEqual("excess=57, breaks=0•1", placed.quality.str_parts())

    def test_wrapping_2(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(50, 100), STYLE, self.pdf)
        self.assertEqual(5, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str((round(s.x), round(s.y))) for s in placed.segments)
        self.assertEqual('hello to|this |brave|new|world', texts)
        self.assertEqual('(0, 0)|(0, 16)|(0, 31)|(0, 47)|(0, 62)', locs)
        self.assertEqual("excess=17, breaks=0•4", placed.quality.str_parts())

    def test_need_bad_break(self):
        run = Run([self.EX])
        placed = place_run(run, Extent(45, 100), STYLE, self.pdf)
        self.assertEqual(5, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str((round(s.x), round(s.y))) for s in placed.segments)
        self.assertEqual('superc|alifragi|listicex|pialido|cious', texts)
        self.assertEqual('(0, 0)|(0, 16)|(0, 31)|(0, 47)|(0, 62)', locs)
        self.assertEqual("excess=12, breaks=4•0", placed.quality.str_parts())

    def test_breaks_again(self):
        run = Run([self.E1, self.E2, self.E3])
        placed = place_run(run, Extent(50, 80), STYLE, self.pdf)
        self.assertEqual(5, len(placed.segments))
        texts = '|'.join(s.text for s in placed.segments)
        locs = '|'.join(str((round(s.x), round(s.y))) for s in placed.segments)
        self.assertEqual('hello to|this |brave|new|world', texts)
        self.assertEqual('(0, 0)|(0, 16)|(0, 31)|(0, 47)|(0, 62)', locs)
        self.assertEqual("excess=17, breaks=0•4", placed.quality.str_parts())

    def test_not_enough_space_no_matter_what_we_try(self):
        run = Run([self.E1, self.EX, self.E3])
        self.assertRaises(ExtentTooSmallError, lambda: place_run(run, Extent(80, 60), STYLE, self.pdf))

    def test_split_item_into_cells(self):
        item = _make_item('a | b         \t| c | d ')
        item.tidy(['test'])
        self.assertEqual(4, len(item.children))
        self.assertEqual('a', item.children[0].to_rst())
        self.assertEqual('b', item.children[1].to_rst())
        self.assertEqual('c', item.children[2].to_rst())
        self.assertEqual('d', item.children[3].to_rst())


class TestBlockPlacement(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.title = Item([Run([Element('A simple title')])])
        styles = Sheet().styles
        styles['default-block'] = Style('default-block').set('padding', '0').set('border', 'none')
        styles = make_complete_styles(styles)

        cls.pdf = PDF((1000, 1000), FontLibrary(), styles=styles)

    def test_empty_block(self):
        # Title by itself
        block = Block(self.title, [])
        placed = place_block(block, Extent(200, 100), 'medium', self.pdf)
        group = placed.children()
        self.assertEqual(2, len(group))
        self.assertEqual(Point(1, 1), group[1].location)

    def test_table(self):
        # Title with 5 cells defined by 3 items
        items = [
            _make_item('hello|this is me'),
            _make_item('goodbye     | thanks'),
            _make_item('for all the fish')
        ]
        block = Block(self.title, items)
        placed = place_block(block, Extent(300, 100), 'medium', self.pdf)
        group = placed.children()
        self.assertEqual(3, len(group))

        # Background
        self.assertEqual(Rect(0, 300, 0, 57), round(group[0].bounds))

        # Main content
        self.assertEqual(Rect(0, 300, 18, 57), round(group[1].bounds))

        # Title content
        self.assertEqual(Rect(0, 300, 0, 18), round(group[2].bounds))

        # Contents on the grid
        self.assertEqual(Point(0, 0), round(placed.child(1).child(0).location))
        self.assertEqual(Point(150, 0), round(placed.child(1).child(1).location))
        self.assertEqual(Point(0, 13), round(placed.child(1).child(2).location))
        self.assertEqual(Point(150, 13), round(placed.child(1).child(3).location))
        self.assertEqual(Point(0, 27), round(placed.child(1).child(4).location))
