from textwrap import dedent
from unittest import TestCase

from converters.dnd4e import read_dnd4e, read_rules_elements
from main import Document


def read_sample(name: str) -> str:
    with open(f'tests/samples/{name}.rst', 'rt') as f:
        return f.read()


class TestCommon(TestCase):

    def setUp(self):
        self.rules = read_rules_elements()

    def test_rules_reading(self):
        self.assertEqual(37568, len(self.rules))

    def test_nine(self):
        data = read_dnd4e('tests/samples/Nine-3.dnd4e', self.rules)
        rst = data.to_rst()
        print(rst)
        doc = Document(rst)
        d = doc.data()
        with open('nine_test.pdf', 'wb') as f:
            f.write(d)

