"""
    Tests that start witha  sheet and do a full layout
"""
import unittest
from collections import defaultdict

from layout import build_content
from layout.content import PlacedContent, PlacedGroupContent
from structure import operations


def read_sample(name: str) -> str:
    with open(f'tests/samples/{name}.rst', 'rt') as f:
        return f.read()


_PARENS = ( (' <', '> '), (' [', '] '), '()', '{}')
_SYMBOL = {'PlacedRectContent': '▢', 'PlacedRunContent': '¶'}


def column_structure(section:PlacedGroupContent) -> str:
    info = defaultdict(lambda:(0,0))
    for s in section.group:
        r = round(s.bounds)
        t = info[r.left]
        info[r.left] = (t[0]+1, max(t[1], r.bottom))
    return ' '.join(f'(n={c}, h={l})' for (_,(c,l)) in sorted(info.items()))




class TestFullLayout(unittest.TestCase):

    def test_one_column(self):
        txt = read_sample('one column')
        sheet = operations.text_to_sheet(txt)
        content, _ = build_content(sheet)
        self.assertEqual('(n=8, h=651)', column_structure(content[0]))


    def test_columns_should_balance(self):
        txt = read_sample('columns should balance')
        sheet = operations.text_to_sheet(txt)
        content, _ = build_content(sheet)
        self.assertEqual('(n=2, h=461) (n=5, h=449) (n=1, h=518)', column_structure(content[0]))
