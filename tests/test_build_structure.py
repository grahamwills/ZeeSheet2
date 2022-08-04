import unittest

from rst.validate import build_structure
from . import util


class BasicBlocks(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.items = util.test_data()

    def test_empty(self):
        source = self.items['Empty'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        self.assertEqual('', sheet.structure_str())

    def test_one_line(self):
        source = self.items['One Line'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        self.assertEqual("❮hello ~❯", sheet.structure_str())

    def test_two_lines(self):
        source = self.items['Two Lines'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        self.assertEqual("❮hello world ~❯", sheet.structure_str())

    def test_two_blocks(self):
        source = self.items['Two Blocks'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        self.assertEqual("❮one header ~❯ ❮and another ~❯", sheet.structure_str())

    def test_blocks_with_items_as_bullets(self):
        source = self.items['Bullets'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        self.assertEqual("❮name ~ [first] [second]❯ ❮address ~ [street] [city] [country]❯", sheet.structure_str())

    def test_blocks_with_items_as_definitions(self):
        source = self.items['Definitions'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        self.assertEqual("❮name ~ [first] [second]❯ ❮address ~ [street] [city] [country]❯", sheet.structure_str())

    def test_sections(self):
        source = self.items['Sections'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        self.assertEqual("first section ~ ❮item ~ [a] [b]❯ --- second section ~ ❮another ~❯ ❮yet another ~❯",
                         sheet.structure_str())

    def test_bold_and_italic(self):
        source = self.items['Bold and Italic'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        self.assertEqual("❮title with «italic⊣emp» text ~ [item with «bold⊣str» text]❯",
                         sheet.structure_str())

    def test_wrapping_text(self):
        source = self.items['Wrapping Test'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        expected = "❮«title⊣emp» which is a very long piece of accompanying text that we should " \
                   "absolutely wrap of a block (remember the text is a very long piece of accompanying " \
                   "text that we should absolutely wrap) ~ [item with «bold⊣str» text and a very long " \
                   "piece of accompanying text that we should absolutely wrap]❯"
        self.assertEqual(expected, sheet.structure_str())

    def test_bad_underlining(self):
        source = self.items['Bad Underlining'][0]
        sheet = build_structure(source)
        self.assertEqual("Possible title underline, too short for the title. "
                         "Treating it as ordinary text because it's so short.", sheet.combined_issues())

    def test_very_bad_underlining(self):
        source = self.items['Very Bad Underlining'][0]
        sheet = build_structure(source)
        self.assertEqual("Unexpected section title or transition. "
                         "(within definition_list • definition_list_item • definition)", sheet.combined_issues())

    def test_literals(self):
        source = self.items['Literals'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        expected = "❮abcdefg ~ [«Literal *text* with italics inside⊣lit»] [A much longer text that has " \
                   "«bold⊣str» text outside, «but then **more bold** text inside the literal part of line⊣lit»]❯"
        self.assertEqual(expected, sheet.structure_str())

    def test_runs_in_item(self):
        source = self.items['Runs In Item'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        expected = "❮title ~ [apple ⬩ part a ⬩ part b ⬩ part c]❯"
        self.assertEqual(expected, sheet.structure_str())
