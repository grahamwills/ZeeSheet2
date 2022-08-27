from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from common import Spacing, Extent
from generate.pdf import PDF
from layout.content import PlacedContent
from layout.packing import Packer
from layout.placement import place_block
from structure import Sheet, Section, Block


def make_pdf(sheet:Sheet, owner:User) -> str:
    file_name = f"sheets/{owner.username}-sheet.pdf"
    pdf = PDF(sheet.page_size)
    content = create_content(sheet, pdf)
    content.draw(pdf)
    bytes = pdf.output()
    path = default_storage.save(file_name, ContentFile(bytes))
    return path[7:] # remove the 'sheets/'


def create_block(block: Block, extent: Extent, pdf: PDF) -> PlacedContent:
    content = place_block(block, extent, pdf)
    return content


def create_section(section: Section, extent: Extent, pdf: PDF) -> PlacedContent:
    margin = Spacing.balanced(10)
    padding = Spacing.balanced(10)

    packer = Packer(section, section.children, create_block, margin, padding, pdf)
    content = packer.into_columns(round(extent.width))
    return content


def create_content(sheet:Sheet, pdf: PDF):

    margin = Spacing.balanced(5)
    padding = Spacing.balanced(2)

    packer = Packer('Sheet', sheet.children, create_section, margin, padding, pdf)
    content = packer.into_columns(sheet.page_size[0])
    return content



