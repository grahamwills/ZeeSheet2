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

def prettify(text:str)-> Tuple[str, List[str]]:

    with warnings.catch_warnings(record=True) as warns:
        warnings.simplefilter("always")
        doc = _parse_rst(text)

        main_visitor = visitors.StructureBuilder(doc)
        doc.walkabout(main_visitor)

        errors = []
        for w in warns:
            if not str(w.message).startswith('unclosed file'):
                message = f"At line {w.lineno}: {w.message}"
                errors.append(message)

        return text, errors
