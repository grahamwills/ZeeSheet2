from copy import copy
from typing import Dict

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
    s = pdf.styles[section.options.style]
    packer = Packer(section, section.children, create_block, s.box.margin, pdf)
    return packer.into_columns(round(extent.width))


def create_sheet(sheet: Sheet, pdf: PDF):
    sheet_style = pdf.styles[sheet.options.style]

    page = Rect(0, sheet.options.width, 0, sheet.options.height)
    sheet_bounds = sheet_style.box.inset_within_margin(page)
    content_bounds = sheet_style.box.inset_within_padding(page)

    if not sheet.children:
        raise RuntimeError('No content was defined')

    child_style_name = sheet.children[0].options.style
    child_style = pdf.styles[child_style_name]
    child_margins = child_style.box.margin

    packer = Packer(sheet, sheet.children, create_section, child_margins, pdf)
    content = packer.into_columns(content_bounds.width)
    content.location = content_bounds.top_left

    frame = placement.make_frame(sheet, sheet_bounds, sheet_style.box)
    if frame:
        content = PlacedGroupContent.from_items(sheet, [frame, content], sheet_bounds, 0)
    return content


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
