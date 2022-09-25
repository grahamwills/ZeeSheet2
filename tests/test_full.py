"""
    Tests that start witha  sheet and do a full layout
"""
import unittest

from layout import build_content
from structure import operations


def read_sample(name: str) -> str:
    with open(f'tests/samples/{name}.rst', 'rt') as f:
        return f.read()


class TestFullLayout(unittest.TestCase):

    def test_columns_should_balance(self):
        txt = read_sample('columns should balance')
        sheet = operations.text_to_sheet(txt)
        content, _ = build_content(sheet)
        print(content)
