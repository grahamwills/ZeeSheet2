import warnings
from typing import Tuple, List
from . import structure

from docutils import parsers, utils, core, nodes
from docutils.parsers import rst

from . import visitors

def _parse_rst(text: str) -> nodes.document:
    parser = parsers.rst.Parser()
    settings = core.Publisher(parser=parsers.rst.Parser).get_settings()
    document = utils.new_document(text, settings)
    parser.parse(text, document)
    return document

def build_structure(text:str) -> structure.Sheet:
    """Parses the text and builds the basic structure out of it"""
    document = _parse_rst(text)
    main_visitor = visitors.StructureBuilder(document)
    document.walkabout(main_visitor)
    return main_visitor.sheet

def prettify(text:str)-> str:
    sheet = build_structure(text)
    return sheet.to_text()
