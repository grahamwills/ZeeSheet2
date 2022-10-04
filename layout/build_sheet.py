import warnings
from copy import copy
from typing import Dict, Union, Tuple, Optional, Iterable

import structure.style
from common import Extent, Rect
from generate.fonts import FontLibrary
from generate.pdf import PDF
from layout import build_section
from layout.build_section import SectionPacker
from layout.content import PlacedContent, PlacedGroupContent, make_frame
from structure import Sheet, style
from structure.style import Style

FONT_LIB = FontLibrary()


class SheetPacker(SectionPacker):

    def place_item(self, item_index: Union[int, Tuple[int, int]], extent: Extent) -> Optional[PlacedContent]:
        section = self.items[item_index]
        return build_section.place_section(section, extent, self.pdf)


def sheet_to_pages(sheet: Sheet, pdf: PDF) -> list[PlacedGroupContent]:
    sections = sheet.children
    results = []
    last_unplaced = (-1,-1)
    while sections:
        content = create_page(sheet, sections, pdf)
        results.append(content)
        unplaced_sections = content.quality.unplaced
        unplaced_blocks = content.quality.unplaced_descendants

        # Guard against filure to place anything
        unplaced = (unplaced_sections, unplaced_blocks)
        if unplaced == last_unplaced:
            raise RuntimeError('Could not palce an item even with an empty page')
        last_unplaced = unplaced
        sections_for_next_page = []
        if unplaced_blocks:
            # Need to include blocks from the last section that were not placed
            last_section = copy(sections[-unplaced_sections-1])
            last_section.children = last_section.children[-unplaced_blocks:]
            sections_for_next_page.append(last_section)
        if unplaced_sections:
            sections_for_next_page += sections[-unplaced_sections:]

        sections = sections_for_next_page

    return results


def create_page(sheet, sections, pdf):
    extent = Extent(sheet.options.width, sheet.options.height)
    sheet_style = pdf.style(sheet.options.style, 'default-sheet')
    page = Rect(0, extent.width, 0, extent.height)
    content_bounds = sheet_style.box.inset_within_padding(page)
    # Make the content
    sp = SheetPacker(content_bounds, sections, sheet.options.columns, pdf)
    content = sp.place_in_columns()
    content.extent = extent
    # Make the frame
    frame_bounds = sheet_style.box.inset_within_margin(page)
    frame = make_frame(frame_bounds, sheet_style, sheet.options, pdf)
    if frame:
        # Just copy the quality of the content
        content = PlacedGroupContent.from_items([frame, content], content.quality)
    return content


def make_complete_styles(source: Dict[str, Style]) -> Dict[str, Style]:
    base = source.copy()
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
        try:
            parent = base[parent_style_name]
        except KeyError:
            # Check inheritance parents exist
            warnings.warn(f"Style '{s.name} is defined as inheriting from a parent that does not exist ({s.parent}. "
                          f"Using 'default' as the parent instead")
            parent = base['default']
        yield from ancestors_descending(base, parent)
    yield s
