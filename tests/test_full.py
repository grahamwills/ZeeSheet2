"""
    Tests that start with a sheet and do a full layout
"""
import textwrap
import unittest
from collections import defaultdict, namedtuple

import common
from layout import sheet_to_content
from layout.content import PlacedGroupContent, PlacementError
from structure import operations


def read_sample(name: str) -> str:
    with open(f'tests/samples/{name}.rst', 'rt') as f:
        return f.read()


_PARENS = ((' <', '> '), (' [', '] '), '()', '{}')
_SYMBOL = {'PlacedRectContent': '▢', 'PlacedRunContent': '¶'}

CS = namedtuple('cs', 'count bottom')


def column_structure(section: PlacedGroupContent) -> list[CS]:
    info = defaultdict(lambda: CS(0, 0))
    for s in section.group:
        r = round(s.bounds)
        t = info[r.left]
        info[r.left] = CS(t.count + 1, max(t.bottom, r.bottom))
    return [v for _, v in sorted(info.items())]


def as_str(items: list[CS]) -> str:
    return ' '.join(f'(n={c.count}, h={c.bottom})' for c in items)


class TestFullLayout(unittest.TestCase):

    def test_one_column(self):
        txt = read_sample('one column')
        sheet = operations.text_to_sheet(txt)
        content, _ = sheet_to_content(sheet, images={})
        self.assertEqual('(n=8, h=651)', as_str(column_structure(content[0])))

    def test_columns_should_balance(self):
        txt = read_sample('columns should balance')
        sheet = operations.text_to_sheet(txt)
        content, _ = sheet_to_content(sheet, images={})

        structure = column_structure(content[0])
        stdev = common.variance([v.bottom for v in structure]) ** 0.5

        self.assertEqual(0, content.error.clipped)
        self.assertEqual(0, content.error.bad_breaks)
        self.assertTrue(stdev < 20)

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
        print(structure)
