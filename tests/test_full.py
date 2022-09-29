"""
    Tests that start with a sheet and do a full layout
"""
import textwrap
import unittest
from collections import defaultdict, namedtuple

import common
from common import Rect
from layout import sheet_to_content, sheet_to_pdf_document
from layout.content import PlacedGroupContent
from structure import operations


def read_sample(name: str) -> str:
    with open(f'tests/samples/{name}.rst', 'rt') as f:
        return f.read()


_PARENS = ((' <', '> '), (' [', '] '), '()', '{}')
_SYMBOL = {'PlacedRectContent': '▢', 'PlacedRunContent': '¶'}

CS = namedtuple('cs', 'count width bottom')


def column_structure(section: PlacedGroupContent) -> list[CS]:
    info = defaultdict(lambda: CS(0, 0, 0))
    for s in section.group:
        r= round(s.bounds)
        t = info[r.left]
        info[r.left] = CS(t.count + 1, max(t.width, r.width), max(t.bottom, r.bottom))
    return [v for _, v in sorted(info.items())]


def as_str(items: list[CS]) -> str:
    return ' '.join(f'(n={c.count}, h={c.bottom})' for c in items)


class TestFullLayout(unittest.TestCase):

    def test_one_column(self):
        txt = read_sample('one column')
        sheet = operations.text_to_sheet(txt)
        content, _ = sheet_to_content(sheet, images={})
        self.assertEqual('(n=8, h=737)', as_str(column_structure(content[0])))

    def test_columns_should_balance(self):
        txt = read_sample('columns should balance')
        sheet = operations.text_to_sheet(txt)
        content, _ = sheet_to_content(sheet, images={})

        structure = column_structure(content[0])
        stdev = common.variance([v.bottom for v in structure]) ** 0.5

        self.assertEqual(0, content.quality.clipped)
        self.assertEqual(0, content.quality.bad_breaks)
        self.assertTrue(stdev < 20, f"Std dev was {stdev}")

    def test_more_columns_than_content(self):
        txt = textwrap.dedent(
            """
            .. section:: columns=5
            
            ABC
            
            DEF
            """
        )
        sheet = operations.text_to_sheet(txt)
        content, _ = sheet_to_content(sheet, images={})
        structure = column_structure(content[0])
        self.assertEqual(5, len(structure))

    def test_table_sizes(self):
        txt = textwrap.dedent(
            """
                - *Rocketeer* | A politically well-connected Rocketeer
                - *Trouble*   | Who could resist a perfect patisserie?
                - *Swordplay* | Floats like a butterfly
                - *Family*    | A religious noble house with a tradition of brewing
                - *General*   | My portly figure complements my strong constitution
                - *General*   | In love with Laurent's sister
            """)

        sheet = operations.text_to_sheet(txt)
        content, _ = sheet_to_content(sheet, images={})
        inner = content[0][0][1]
        structure = column_structure(inner)
        self.assertEqual(6, structure[0].count)
        self.assertEqual(6, structure[1].count)
        self.assertEqual(structure[0].bottom, structure[1].bottom)
        self.assertTrue(structure[1].width > 1.5 * structure[0].width)
