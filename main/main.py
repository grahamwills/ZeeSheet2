from typing import Dict

from docutils import parsers, core, utils

from generate.pdf import PDF
from layout.content import Pages
from layout.build_sheet import make_complete_styles, FONT_LIB, build_sheet

from structure import model, visitors, Sheet, ImageDetail, style
from structure.operations import Prettify


def text_to_sheet(text: str) -> model.Sheet:
    """Parses the text and builds the basic structure out of it"""
    parser = parsers.rst.Parser()
    # noinspection PyTypeChecker
    settings = core.Publisher(parser=parsers.rst.Parser).get_settings()
    settings.halt_level = 99
    document = utils.new_document(text, settings)
    parser.parse(text, document)
    main_visitor = visitors.StructureBuilder(document)
    document.walkabout(main_visitor)
    return main_visitor.get_sheet()


def prettify(sheet: Sheet, width: int = 100) -> str:
    return Prettify(sheet, width).run()


def sheet_to_pdf_document(sheet: Sheet, images: Dict[str, ImageDetail]) -> bytes:
    pages = sheet_to_content(sheet, images)
    pages[0].draw(pages.pdf)
    return pages.pdf.output()


def sheet_to_content(sheet: Sheet, images: Dict[str, ImageDetail]) -> Pages:
    # Use inheritance to make the values all defined
    complete_styles = make_complete_styles(sheet.styles)
    # Change 'auto' to be actual values
    for s in complete_styles.values():
        style.Defaults.set_auto_values(s)
    pdf = PDF((int(sheet.options.width), int(sheet.options.height)), FONT_LIB,
              styles=complete_styles, images=images, debug=sheet.options.debug)
    return build_sheet(sheet, pdf)
