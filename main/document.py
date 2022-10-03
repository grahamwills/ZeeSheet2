from __future__ import annotations

from typing import Dict

from docutils import parsers, core, utils

from generate.pdf import PDF
from layout import PlacedGroupContent
from layout.build_sheet import make_complete_styles, FONT_LIB, sheet_to_pages
from structure import visitors, Sheet, ImageDetail, Prettify, StyleDefaults, prepare_for_visit


class Document:
    """ The base document """

    source: str  # The raw source text
    images: Dict[str, ImageDetail]
    _sheet: Sheet or None  # Parsed structure
    _pages: list[PlacedGroupContent] or None  # Placed content by page
    _data: bytes or None  # PDF as bytes
    _pdf: PDF or None  # The pdf drawing component

    def __init__(self, source: str, images: Dict[str, ImageDetail] = None):
        self.source = source
        self.images = images or {}
        self._sheet = None
        self._pages = None
        self._data = None
        self._pdf = None

    # noinspection PyUnresolvedReferences
    def sheet(self):
        if not self._sheet:
            text = prepare_for_visit(self.source)
            parser = parsers.rst.Parser()
            settings = core.Publisher(parser=parsers.rst.Parser).get_settings()
            settings.halt_level = 99
            settings.report_level = 99
            document = utils.new_document(text, settings)
            parser.parse(text, document)
            main_visitor = visitors.StructureBuilder(document)
            document.walkabout(main_visitor)
            self._sheet = main_visitor.get_sheet()
        return self._sheet

    def pdf(self) -> PDF:
        if not self._pdf:
            sheet = self.sheet()
            # Use inheritance to make the values all defined
            complete_styles = make_complete_styles(sheet.styles)
            # Change 'auto' to be actual values
            for s in complete_styles.values():
                StyleDefaults.set_auto_values(s)
            page_size = (int(sheet.options.width), int(sheet.options.height))
            self._pdf = PDF(page_size, FONT_LIB, styles=complete_styles, images=self.images, debug=sheet.options.debug)
        return self._pdf

    def pages(self) -> list[PlacedGroupContent]:
        if not self._pages:
            self._pages = sheet_to_pages(self.sheet(), self.pdf())
        return self._pages

    def page(self, n: int) -> PlacedGroupContent:
        return self.pages()[n]

    def data(self) -> bytes:
        if not self._data:
            pages = self.pages()
            pdf = self.pdf()
            for page in pages:
                page.draw(pdf)
                pdf.showPage()
            self._data = pdf.output()
        return self._data

    def prettified(self, width: int = 100) -> str:
        return Prettify(self.sheet(), width).run()
