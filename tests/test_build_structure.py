import unittest
from . import util
from rst.validate import build_structure
from textwrap import dedent

class BasicBlocks(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.items = util.test_data()

    def test_empty(self):
        source = self.items['Empty'][0]
        sheet = build_structure(source)
        self.assertEqual('',  sheet.combined_issues())
        self.assertEqual('<[ ]>', sheet.structure_str())

    def test_one_line(self):
        source = self.items['One Line'][0]
        sheet = build_structure(source)
        self.assertEqual('',  sheet.combined_issues())
        self.assertEqual("<[hello: ]>", sheet.structure_str())

    def test_two_lines(self):
        source = self.items['Two Lines'][0]
        sheet = build_structure(source)
        self.assertEqual('',  sheet.combined_issues())
        self.assertEqual("<[hello world: ]>", sheet.structure_str())

    def test_two_blocks(self):
        source = self.items['Two Blocks'][0]
        sheet = build_structure(source)
        self.assertEqual('',  sheet.combined_issues())
        self.assertEqual("<[one header: ] [and another: ]>", sheet.structure_str())

    def test_blocks_with_items_as_bullets(self):
        source = self.items['Bullets'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        self.assertEqual("<[name: first • second] [address: street • city • country]>", sheet.structure_str())

    def test_blocks_with_items_as_definitions(self):
        source = self.items['Definitions'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        self.assertEqual("<[name: first • second] [address: street • city • country]>", sheet.structure_str())

    def test_sections(self):
        source = self.items['Sections'][0]
        sheet = build_structure(source)
        self.assertEqual('', sheet.combined_issues())
        self.assertEqual("<first section: [item: a • b]> <second section: [another: ] [yet another: ]>", sheet.structure_str())
