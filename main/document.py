from __future__ import annotations

import datetime
import warnings
from collections import Counter, defaultdict
from copy import copy
from typing import Dict, Generator

from docutils import parsers, core, utils

import common
import structure
from common import prettify_username
from drawing import PDF
from layout import PlacedGroupContent, ExtentTooSmallError
from layout.build_sheet import FONT_LIB, sheet_to_pages
from structure import visitors, Sheet, ImageDetail, Prettify, prepare_for_visit, Style, StyleDefaults, style, Block

LOGGER = common.configured_logger(__name__)


def standard_info(username: str, now=None) -> dict[str, str]:
    now = now or datetime.datetime.now()
    return {
        'player': prettify_username(username),
        'date': now.strftime('%B %-d, %Y'),
        'short_date': now.strftime('%Y-%m-%d'),
    }


class Document:
    """ The base document """

    source: str  # The raw source text
    images: Dict[str, ImageDetail]
    _sheet: Sheet or None  # Parsed structure
    _pages: list[PlacedGroupContent] or None  # Placed content by page
    _data: bytes or None  # PDF as bytes
    _pdf: PDF or None  # The pdf drawing component
    _input_vars: dict[str, str]

    def __init__(self, source: str, images: Dict[str, ImageDetail] = None, username='ZeeSheet User'):
        self.source = source
        self.images = images or {}
        self._sheet = None
        self._pages = None
        self._data = None
        self._pdf = None
        self._input_vars = standard_info(username)

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

            # Run scripts and collect variables to pass to the main visitor
            script_visitor = visitors.ScriptBuilder(document, self._input_vars)
            document.walkabout(script_visitor)
            variables = script_visitor.calculator.variables()

            main_visitor = visitors.StructureBuilder(document, variables)
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
            self._pdf = PDF(page_size, FONT_LIB, styles=styles, images=self.images,
                            debug=sheet.options.debug, quality=sheet.options.quality)
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
            try:
                pages = self.pages()
            except ExtentTooSmallError as ex:
                LOGGER.error(str(ex))
                raise
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
        self.usages = defaultdict(Counter)
        self.idx = 0
        self.undefined = set()

    def run(self) -> dict[str, Style]:
        # Match styles up to their most common usages in the sheet (blocks, titles, images, etc.)
        self.collect_usages()

        if len(self.undefined) == 1:
            warnings.warn(f"Style {list(self.undefined)[0]}. Using a default instead of it")
        if len(self.undefined) > 1:
            warnings.warn(f"Styles {', '.join(self.undefined)}. Using defaults instead of them")

        # Set the parents to the most common usage, if the parent has not been defined
        for style in self.styles.values():
            style.parent = style.parent or self.default_parent(style.name)

        # Because the automatic setting of colors modifies styles, we must make sure that every
        # block and block title have a unique style, parented off the shared one
        # These styles are added to the total list of styles and are properly parented by construction
        for section in self.sheet.children:
            for block in section.children:
                self.replace_style(block, 'style')
                self.replace_style(block, 'title_style')

        # Add styles for default, default-title, etc.
        self.add_default_styles()

        # Fill in all missing style options using the hierarchy
        for k, v in list(self.styles.items()):
            self.styles[k] = self.to_complete(v)

        # For colors marked as 'auto', set those values, using title/block pairs as a hint
        pairs = self.make_paired_styles()
        for s in self.styles.values():
            target = self.default_parent(s.name)
            pair = pairs[s.name]
            StyleDefaults.set_auto_values(s, target=target, pair=pair)

        return self.styles

    # Create a mapping of all the usages
    def collect_usages(self):
        self._validate_and_update_usages(self.sheet.options, 'style', 'default-sheet')
        for section in self.sheet.children:
            self._validate_and_update_usages(section.options, 'style', 'default-section')
            for block in section.children:
                default = Block.default_options(block.options.method)
                if block.options.image and not block.children:
                    self._validate_and_update_usages(block.options, 'style', 'default-image')
                else:
                    self._validate_and_update_usages(block.options, 'style', default.style)
                self._validate_and_update_usages(block.options, 'title_style', default.title_style)

    def _validate_and_update_usages(self, owner, attribute, default):
        style = getattr(owner, attribute)
        self.usages[style].update([default])
        # if style not in self.styles:
        #     setattr(owner, attribute, default)
        #     self.undefined.add(style)

    def default_parent(self, style_name):
        if style_name in self.usages:
            # Return the most common item
            v = self.usages[style_name]
            return v.most_common(1)[0][0]
        else:
            return 'default'

    def ancestors_descending(self, s: Style) -> Generator[Style, None, None]:
        # Do not try and follow up the tree from the root!
        if s.parent != style.StyleDefaults.default.parent:
            try:
                parent = self.styles[s.parent]
            except KeyError:
                warnings.warn(
                    f"Style '{s.name}' is defined as inheriting from a parent that has not been defined ({s.parent}). "
                    f"Using 'default' as the parent instead")
                parent = self.styles['default']
            yield from self.ancestors_descending(parent)
        yield s

    def to_complete(self, s: Style) -> Style:
        result = Style(s.name)
        for ancestor in self.ancestors_descending(s):
            structure.style.set_using_definition(result, ancestor.to_definition())
        return result

    def replace_style(self, block: Block, attribute: str):
        self.idx += 1
        style_name = getattr(block.options, attribute)
        if style_name:
            style = Style(name=f"_{common.name_of(block)}_{attribute}", parent=style_name)
            setattr(block.options, attribute, style.name)
            # Store the style and its usage (which is the same as the style it was derived from)
            self.styles[style.name] = style
            self.usages[style.name] = self.usages[style_name]

    def add_default_styles(self):
        for style in StyleDefaults.ALL:
            try:
                existing = self.styles[style.name]
                # This style has been redefined, so we need to juggle names
                # and make the redefined version inherit from the default with a modified name
                redefinition = copy(existing)
                self.styles['#' + style.name] = style
                redefinition.parent = '#' + style.name
                self.styles[style.name] = redefinition
            except KeyError:
                # Has not been defined - simply add it in
                self.styles[style.name] = style

    # noinspection PyTypeChecker
    def make_paired_styles(self) -> dict[str, Style]:
        # Bidirectional pairs of styles that are used together
        pairs = defaultdict(lambda: None)
        for block in self.sheet.blocks():
            opt = block.options
            if opt.style and opt.title_style:
                pairs[opt.style] = self.styles[opt.title_style]
                pairs[opt.title_style] = self.styles[opt.style]
        return pairs
