import unittest
import warnings

import main
from structure import description
from structure.model import Element, text_to_elements
from . import util


class BasicBlocks(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.items = util.test_data()

    def setUp(self) -> None:
        # Throw errors for warnings as we shoudl not see them in general
        warnings.simplefilter('error', Warning)

    def tearDown(self) -> None:
        warnings.simplefilter('default', Warning)

    def test_empty(self):
        source = self.items['Empty'][0]
        sheet = main.Document(source).sheet()
        self.assertEqual('', description(sheet))

    def test_one_line(self):
        source = self.items['One Line'][0]
        sheet = main.Document(source).sheet()
        self.assertEqual("❮[hello] ~❯", description(sheet))

    def test_two_lines(self):
        source = self.items['Two Lines'][0]
        sheet = main.Document(source).sheet()
        self.assertEqual("❮[hello world] ~❯", description(sheet))

    def test_two_blocks(self):
        source = self.items['Two Blocks'][0]
        sheet = main.Document(source).sheet()
        self.assertEqual("❮[one header] ~❯ ❮[and another] ~❯", description(sheet))

    def test_blocks_with_items_as_bullets(self):
        source = self.items['Bullets'][0]
        sheet = main.Document(source).sheet()
        self.assertEqual("❮[name] ~ [first] [second]❯ ❮[address] ~ [street] [city] [country]❯", description(sheet))

    def test_blocks_with_items_as_definitions(self):
        source = self.items['Definitions'][0]
        sheet = main.Document(source).sheet()
        self.assertEqual("❮[name] ~ [first] [second]❯ ❮[address] ~ [street] [city] [country]❯", description(sheet))

    def test_section_titled(self):
        warnings.simplefilter('default', Warning)
        source = self.items['Sections'][0]
        sheet = main.Document(source).sheet()
        self.assertEqual("❮[item] ~ [a] [b]❯ --- ❮[another] ~❯ ❮[yet another] ~❯", description(sheet))

    def test_bold_and_italic(self):
        source = self.items['Bold and Italic'][0]
        sheet = main.Document(source).sheet()
        self.assertEqual("❮[title with «italic⊣emp» text] ~ [item with «bold⊣str» text]❯",
                         description(sheet))

    def test_wrapping_text(self):
        source = self.items['Wrapping Test'][0]
        sheet = main.Document(source).sheet()
        expected = "❮[«title⊣emp» which is a very long piece of accompanying text that we should " \
                   "absolutely wrap of a block (remember the text is a very long piece of accompanying " \
                   "text that we should absolutely wrap)] ~ [item with «bold⊣str» text and a very long " \
                   "piece of accompanying text that we should absolutely wrap]❯"
        self.assertEqual(expected, description(sheet))

    def test_literals(self):
        source = self.items['Literals'][0]
        sheet = main.Document(source).sheet()
        expected = "❮[abcdefg] ~ [«Literal *text* with italics inside⊣lit»] [A much longer text that has " \
                   "«bold⊣str» text outside, «but then **more bold** text inside the literal part of line⊣lit»]❯"
        self.assertEqual(expected, description(sheet))

    def test_styles_simple(self):
        source = self.items['Simple Styles'][0]
        sheet = main.Document(source).sheet()
        self.assertEqual(2, len(sheet.styles))
        self.assertIn('a', sheet.styles)
        self.assertIn('b', sheet.styles)
        self.assertEqual(sheet.styles['a'].font.family, 'Courier')
        self.assertEqual(sheet.styles['b'].parent, 'a')

    def test_runs_in_item(self):
        source = self.items['Runs In Item'][0]
        sheet = main.Document(source).sheet()
        expected = "❮[title] ~ [apple ⬩ part a ⬩ part b ⬩ part c]❯"
        self.assertEqual(expected, description(sheet))

    def test_checkboxes(self):
        elements = text_to_elements('[ ] [X] [O]', None, {})
        expected = [Element(' ', 'checkbox'), Element(' '),
                    Element('X', 'checkbox'), Element(' '),
                    Element(' ', 'checkbox')]
        self.assertEqual(expected, elements)
