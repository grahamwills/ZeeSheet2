from copy import copy
from typing import Union, Optional

import common
from common import Extent, Rect
from drawing import FontLibrary
from drawing import PDF
from layout import build_section
from layout.build_section import SectionPacker
from layout.content import PlacedContent, PlacedGroupContent, make_frame
from structure import Sheet

FONT_LIB = FontLibrary()


class SheetPacker(SectionPacker):

    def place_item(self, item_index: Union[int, tuple[int, int]], extent: Extent) -> Optional[PlacedContent]:
        if isinstance(item_index, tuple):
            # This should be a simple table -- only one row
            assert item_index[0] == 0
            item_index = item_index[1]
        section = self.items[item_index]
        return build_section.place_section(section, extent, self.pdf)


def sheet_to_pages(sheet: Sheet, pdf: PDF) -> list[PlacedGroupContent]:
    sections = sheet.children
    results = []
    last_unplaced = (-1, -1)
    while sections:
        content = create_page(sheet, sections, pdf)
        results.append(content)
        unplaced_sections = content.quality.unplaced
        unplaced_blocks = content.quality.unplaced_descendants

        # Guard against failure to place anything
        unplaced = (unplaced_sections, unplaced_blocks)
        if unplaced == last_unplaced:
            raise RuntimeError('Could not place an item even with an empty page')
        last_unplaced = unplaced
        sections_for_next_page = []
        if unplaced_blocks:
            # Need to include blocks from the last section that were not placed
            last_section = copy(sections[-unplaced_sections - 1])
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
    sp = SheetPacker(common.name_of(sheet), content_bounds, sections, sheet.options.columns, pdf)
    content = sp.place_in_columns()
    content.extent = extent
    # Make the frame
    frame_bounds = sheet_style.box.inset_within_margin(page)
    frame = make_frame(frame_bounds, sheet_style, sheet.options, pdf)
    if frame:
        # Just copy the quality of the content
        content = PlacedGroupContent.from_items([frame, content], content.quality)
    return content
