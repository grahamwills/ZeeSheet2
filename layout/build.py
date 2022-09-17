from copy import copy
from typing import Dict, Union

import layout.placement as placement
import structure.style
from common import Extent, Rect
from generate.fonts import FontLibrary
from generate.pdf import PDF
from layout.content import PlacedContent, PlacedGroupContent
from layout.packing import Packer
from structure import Sheet, Section, Block, style
from structure.style import Style

FONT_LIB = FontLibrary()


def make_pdf(sheet: Sheet) -> bytes:
    complete_styles = make_complete_styles(sheet.styles)
    pdf = PDF((int(sheet.options.width), int(sheet.options.height)), FONT_LIB,
              styles=complete_styles, debug=sheet.options.debug)
    content = create_sheet(sheet, pdf)
    content.draw(pdf)
    return pdf.output()


def create_block(block: Block, extent: Extent, pdf: PDF) -> PlacedContent:
    return placement.place_block(block, extent, pdf)


def create_section(section: Section, extent: Extent, pdf: PDF) -> PlacedContent:
    section_style = pdf.styles[section.options.style]
    bounds = Rect(0, extent.width, 0, extent.height)
    content_bounds = section_style.box.inset_from_margin_within_padding(bounds)
    child_margins = get_child_margins(pdf, section)

    packer = Packer(section.children, create_block, child_margins, pdf)
    content = packer.into_columns(content_bounds.width)
    content.location = content_bounds.top_left

    # Make the frame
    frame_bounds = section_style.box.outset_to_border(content.bounds)
    frame = placement.make_frame(frame_bounds, section_style)
    if frame:
        content = PlacedGroupContent.from_items([frame, content])
    return content


def create_sheet(sheet: Sheet, pdf: PDF):
    extent = Extent(sheet.options.width, sheet.options.height)
    sheet_style = pdf.styles[sheet.options.style]
    page = Rect(0, extent.width, 0, extent.height)
    sheet_bounds = sheet_style.box.inset_within_margin(page)
    content_bounds = sheet_style.box.inset_within_padding(page)
    child_margins = get_child_margins(pdf, sheet)

    packer = Packer(sheet.children, create_section, child_margins, pdf)
    content = packer.into_columns(content_bounds.width)
    content.location = content_bounds.top_left

    frame = placement.make_frame(sheet_bounds, sheet_style)
    if frame:
        content = PlacedGroupContent.from_items([frame, content], sheet_bounds)
    return content


def get_child_margins(pdf, component: Union[Sheet, Section]):
    if not component.children:
        raise RuntimeError('No content was defined')
    child_style_name = component.children[0].options.style
    child_style = pdf.styles[child_style_name]
    return child_style.box.margin


def _all_lineage_definitions(base, style):
    chained_defs = []
    while style is not None:
        chained_defs.append(style.to_definition())
        parent_style_name = style.parent
        if parent_style_name is None and style.name != 'default' and style.name != '#default':
            parent_style_name = 'default'
        style = base[parent_style_name] if parent_style_name else None
    return chained_defs


def _to_complete(style: Style, base: Dict[str, Style]) -> Style:
    chained_defs = _all_lineage_definitions(base, style)

    # Reverse order so the higher up ones get overridden
    result = Style(style.name)
    for defs in chained_defs[::-1]:
        structure.style.set_using_definition(result, defs)
    return result


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
        results[k] = _to_complete(v, base)
    return results
