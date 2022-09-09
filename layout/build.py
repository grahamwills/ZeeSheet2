from copy import copy
from typing import Dict

import structure.style
from common import Extent
from generate.pdf import PDF
from layout.content import PlacedContent
from layout.packing import Packer
from layout.placement import place_block
from structure import Sheet, Section, Block, style
from structure.style import Style


def make_pdf(sheet: Sheet) -> bytes:
    complete_styles = make_complete_styles(sheet.styles)
    pdf = PDF((int(sheet.options.width), int(sheet.options.height)), styles=complete_styles, debug=sheet.options.debug)
    content = create_sheet(sheet, pdf)
    content.draw(pdf)
    return pdf.output()


def create_block(block: Block, extent: Extent, pdf: PDF) -> PlacedContent:
    return place_block(block, extent, pdf)


def create_section(section: Section, extent: Extent, pdf: PDF) -> PlacedContent:
    s = pdf.styles[section.options.style]
    packer = Packer(section, section.children, create_block, s.box.margin, s.box.padding, pdf)
    return packer.into_columns(round(extent.width))


def create_sheet(sheet: Sheet, pdf: PDF):
    s = pdf.styles[sheet.options.style]
    packer = Packer(sheet, sheet.children, create_section, s.box.margin, s.box.padding, pdf)
    content = packer.into_columns(sheet.options.width)
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
