from copy import copy
from typing import Dict, Union, Tuple, Optional, List, Iterable

import layout.placement as placement
import structure.style
from common import Extent, Rect, Spacing
from generate.fonts import FontLibrary
from generate.pdf import PDF
from layout.content import PlacedContent, PlacedGroupContent
from layout.packing import ColumnPacker
from structure import Sheet, style, StructureUnit
from structure.style import Style

FONT_LIB = FontLibrary()


def make_pdf(sheet: Sheet) -> bytes:
    content, pdf = build_content(sheet)
    content.draw(pdf)
    return pdf.output()


def build_content(sheet) -> Tuple[PlacedGroupContent, PDF]:
    # Use inheritance to make the values all defined
    complete_styles = make_complete_styles(sheet.styles)
    # Change 'auto' to be actual values
    for s in complete_styles.values():
        style.Defaults.set_auto_values(s)
    pdf = PDF((int(sheet.options.width), int(sheet.options.height)), FONT_LIB,
              styles=complete_styles, debug=sheet.options.debug)
    content = build_sheet(sheet, pdf)
    return content, pdf


class SectionPacker(ColumnPacker):

    def __init__(self, bounds: Rect, items: List[type(StructureUnit)], column_count: int, pdf, granularity: int = 20):
        self.items = items
        self.pdf = pdf
        super().__init__(bounds, len(items), column_count, granularity=granularity)

    def place_item(self, item_index: Union[int, Tuple[int, int]], extent: Extent) -> Optional[PlacedContent]:
        return placement.place_block(self.items[item_index], extent, self.pdf)

    def margins_of_item(self, item_index: Union[int, Tuple[int, int]]) -> Optional[Spacing]:
        style_name = self.items[item_index].options.style
        return self.pdf.styles[style_name].box.margin


class SheetPacker(SectionPacker):

    def place_item(self, item_index: Union[int, Tuple[int, int]], extent: Extent) -> Optional[PlacedContent]:
        section = self.items[item_index]
        section_style = self.pdf.styles[section.options.style]
        bounds = Rect(0, extent.width, 0, extent.height)
        content_bounds = section_style.box.inset_from_margin_within_padding(bounds)

        # Make the content
        sp = SectionPacker(content_bounds, section.children, section.options.columns, self.pdf, granularity=25)
        content = sp.place_in_columns()

        # Make the frame
        frame_bounds = section_style.box.outset_to_border(content.bounds)
        frame = placement.make_frame(frame_bounds, section_style)
        if frame:
            content = PlacedGroupContent.from_items([frame, content])

        return content


def build_sheet(sheet: Sheet, pdf: PDF) -> PlacedGroupContent:
    extent = Extent(sheet.options.width, sheet.options.height)
    sheet_style = pdf.styles[sheet.options.style]
    page = Rect(0, extent.width, 0, extent.height)
    content_bounds = sheet_style.box.inset_within_padding(page)

    # Make the content
    sp = SheetPacker(content_bounds, sheet.children, sheet.options.columns, pdf)
    content = sp.place_in_columns()

    # Make the frame
    frame_bounds = sheet_style.box.outset_to_border(content.bounds)
    frame = placement.make_frame(frame_bounds, sheet_style)
    if frame:
        content = PlacedGroupContent.from_items([frame, content])

    return content


def make_complete_styles(source: Dict[str, Style]) -> Dict[str, Style]:
    base = source.copy()
    for s in [style.Defaults.default, style.Defaults.title,
              style.Defaults.block, style.Defaults.section, style.Defaults.sheet]:
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


def to_complete(s: Style, base: Dict[str, Style]) -> Style:
    result = Style(s.name)
    for ancestor in ancestors_descending(base, s):
        structure.style.set_using_definition(result, ancestor.to_definition())
    return result


def ancestors_descending(base: Dict[str, Style], s: Style) -> Iterable[Style]:
    parent_style_name = s.parent
    if parent_style_name is None and s.name != 'default' and s.name != '#default':
        parent_style_name = 'default'
    if parent_style_name:
        yield from ancestors_descending(base, base[parent_style_name])
    yield s
