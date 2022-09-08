from typing import Dict

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

import structure.style
from common import Spacing, Extent
from generate.pdf import PDF
from layout.content import PlacedContent
from layout.packing import Packer
from layout.placement import place_block
from structure import Sheet, Section, Block, style
from structure.style import Style


def make_pdf(sheet: Sheet, owner: User) -> str:
    file_name = f"sheets/{owner.username}-sheet.pdf"
    complete_styles = make_complete_styles(sheet.styles)
    pdf = PDF((int(sheet.options.width), int(sheet.options.height)), styles=complete_styles, debug=sheet.options.debug)
    content = create_sheet(sheet, pdf)
    content.draw(pdf)
    bytes = pdf.output()
    path = default_storage.save(file_name, ContentFile(bytes))
    return path[7:]  # remove the 'sheets/'


def create_block(block: Block, extent: Extent, pdf: PDF) -> PlacedContent:
    content = place_block(block, extent, pdf)
    return content


def create_section(section: Section, extent: Extent, pdf: PDF) -> PlacedContent:
    margin = Spacing.balanced(10)
    padding = Spacing.balanced(10)

    packer = Packer(section, section.children, create_block, margin, padding, pdf)
    content = packer.into_columns(round(extent.width))
    return content


def create_sheet(sheet: Sheet, pdf: PDF):
    style = pdf.styles[sheet.options.style]
    packer = Packer('Sheet', sheet.children, create_section, style.box.margin, style.box.padding, pdf)
    content = packer.into_columns(sheet.options.width)
    return content


def _all_lineage_definitions(base, style):
    chained_defs = []
    while style is not None:
        chained_defs.append(style.to_definition())
        style = base[style.parent] if style.parent else None
    return chained_defs


def _to_complete(style: Style, base: Dict[str, Style]) -> Style:
    chained_defs = _all_lineage_definitions(base, style)

    # Reverse order so the higher up ones get overridden
    result = Style(style.name)
    for defs in chained_defs[::-1]:
        structure.style.set_using_definition(result, defs)
    return result


# TODO: Test this
def make_complete_styles(source: Dict[str, Style]) -> Dict[str, Style]:
    base = source.copy()
    for s in [style.Defaults.default, style.Defaults.title,
              style.Defaults.block, style.Defaults.section, style.Defaults.sheet]:
        base[s.name] = s
    results = {}
    for k, v in base.items():
        results[k] = _to_complete(v, base)
    return results
