from __future__ import annotations

from collections import Counter, defaultdict
from copy import copy
from typing import Dict

from docutils import parsers, core, utils

import common
from generate.pdf import PDF
from layout import PlacedGroupContent
from layout.build_sheet import FONT_LIB, sheet_to_pages, to_complete
from structure import visitors, Sheet, ImageDetail, Prettify, prepare_for_visit, Style, StyleDefaults, style

LOGGER = common.configured_logger(__name__)


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
            LOGGER.info('Building sheet')
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

            LOGGER.info('Completing styles and creating pdf writer')

            resolver = StyleResolver(sheet)
            styles = resolver.run()

            # Define default inheritance and use inheritance to make the values all defined

            page_size = (int(sheet.options.width), int(sheet.options.height))
            self._pdf = PDF(page_size, FONT_LIB, styles=styles, images=self.images, debug=sheet.options.debug)
        return self._pdf

    def pages(self) -> list[PlacedGroupContent]:
        LOGGER.info('Building document pages')
        if not self._pages:
            self._pages = sheet_to_pages(self.sheet(), self.pdf())
        return self._pages

    def page(self, n: int) -> PlacedGroupContent:
        return self.pages()[n]

    def data(self) -> bytes:
        if not self._data:
            pages = self.pages()
            pdf = self.pdf()
            LOGGER.info('Drawing pages into pdf document')
            for page in pages:
                page.draw(pdf)
                pdf.showPage()
            self._data = pdf.output()
        return self._data

    def prettified(self, width: int = 100) -> str:
        return Prettify(self.sheet(), width).run()


class StyleResolver:
    def __init__(self, sheet: Sheet):
        self.sheet = sheet
        self.styles = {s.name: copy(s) for s in sheet.styles.values()}

    def run(self) -> dict[str, Style]:
        default_parent = self.default_parents()

        for style in self.styles.values():
            style.parent = style.parent or default_parent[style.name]
        self.make_unique_styles_per_block()
        self.styles = self.make_complete_styles()

        pairs = self.title_body_pairs()
        for s in self.styles.values():
            target = default_parent[s.name]
            pair = None
            pair_name = pairs[s.name]
            if pair_name:
                pair = self.styles[pair_name]
            StyleDefaults.set_auto_values(s, target=target, pair=pair)
        return self.styles

    # Create a mapping of all the usages
    def default_parents(self) -> dict[str, str]:
        result = defaultdict(Counter)
        result[self.sheet.options.style].update(['default-sheet'])
        for section in self.sheet.children:
            result[section.options.style].update(['default-section'])
            result[section.options.title_style].update(['default-title'])
            for block in section.children:
                if block.options.image and not block.children:
                    result[block.options.style].update(['default-image'])
                else:
                    result[block.options.style].update(['default-block'])
                result[block.options.title_style].update(['default-title'])

        # Convert to dictionary using most common usage, and put into a default dict
        map = {k: v.most_common(1)[0][0] for k, v in result.items()}
        return defaultdict(lambda: 'default', map)

    def make_complete_styles(self, ) -> Dict[str, Style]:
        base = self.styles.copy()
        for s in [style.StyleDefaults.default, style.StyleDefaults.title, style.StyleDefaults.block,
                  style.StyleDefaults.section,
                  style.StyleDefaults.sheet, style.StyleDefaults.hidden, style.StyleDefaults.image]:
            if s.name in base:
                # This style has been redefined, so we need to juggle names
                # and make the redefined version inherit from the default with a modified name
                base['#' + s.name] = s
                redefinition = copy(base[s.name])
                redefinition.parent = '#' + s.name
                base[s.name] = redefinition
            else:
                base[s.name] = s

        results = {}
        for k, v in base.items():
            results[k] = to_complete(v, base)
        return results

    def title_body_pairs(self) -> dict[str, str]:
        # Create a mapping of all the usages
        pairs = defaultdict(lambda: None)
        for section in self.sheet.children:
            for block in section.children:
                opt = block.options
                if opt.style and opt.title_style:
                    pairs[opt.style] = opt.title_style
                    pairs[opt.title_style] = opt.style
        return pairs

    def make_unique_styles_per_block(self):
        idx = 0
        # Create a mapping of all the usages
        sheet = self.sheet
        for section in sheet.children:
            for block in section.children:
                idx += 1
                style = Style(name=f"_block_{idx}", parent=block.options.style)
                self.styles[style.name] = style
                block.options.style = style.name
                style = Style(name=f"_title_{idx}", parent=block.options.title_style)
                self.styles[style.name] = style
                block.options.title_style = style.name
