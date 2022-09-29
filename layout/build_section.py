from typing import Union, Tuple, Optional, List

from common import Extent, Rect, Spacing
from generate.pdf import PDF
from layout import build_block
from layout.content import PlacedContent, PlacedGroupContent, make_frame, PlacedImageContent
from layout.packer import ColumnPacker
from structure import StructureUnit, Section


def place_section(section: Section, extent: Extent, pdf: PDF) -> Optional[PlacedContent]:
    section_style = pdf.styles[section.options.style]
    bounds = Rect(0, extent.width, 0, extent.height)
    content_bounds = section_style.box.inset_from_margin_within_padding(bounds)

    # Ensure that we have enough children for the column requested
    blocks = section.children
    while len(blocks) < section.options.columns:
        blocks = blocks + [build_block.tiny_block()]

    sp = SectionPacker(content_bounds, blocks, section.options.columns, pdf, granularity=25)
    content = sp.place_in_columns()

    shrink_images_if_suitable(content)

    # Make the frame
    frame_bounds = section_style.box.outset_to_border(content.bounds)
    frame = make_frame(frame_bounds, section_style)
    if frame:
        # Frame adds nothing, so just use content's quality
        content = PlacedGroupContent.from_items([frame, content], content.quality)

    return content


def shrink_images_if_suitable(content: PlacedGroupContent):
    """ If images have flexible sizes, reduce them to match heights if that helps """
    shrinkable_images = []
    lowest_other = content.bounds.top
    for placed in content.items:
        if isinstance(placed, PlacedImageContent) and placed.mode in {'fill', 'stretch'}:
            shrinkable_images.append(placed)
        else:
            lowest_other = max(lowest_other, placed.bounds.bottom)

    # We only care about shrinkable images that are too big
    shrinkable_images = [s for s in shrinkable_images if s.bounds.bottom > lowest_other]
    if not shrinkable_images:
        return

    # Shrink items, calculating the amount we have shrunk by and shrink the total extent by that
    min_dy = 9e99
    for s in shrinkable_images:
        dy = s.shrink_to_fit(bottom=lowest_other)
        min_dy = min(dy, min_dy)
    content.extent = content.extent - Extent(0, min_dy)


class SectionPacker(ColumnPacker):

    def __init__(self, bounds: Rect, items: List[type(StructureUnit)], column_count: int, pdf, granularity: int = 20):
        self.items = items
        self.pdf = pdf
        super().__init__(bounds, len(items), column_count, granularity=granularity)

    def place_item(self, item_index: Union[int, Tuple[int, int]], extent: Extent) -> Optional[PlacedContent]:
        return build_block.place_block(self.items[item_index], extent, self.pdf)

    def margins_of_item(self, item_index: Union[int, Tuple[int, int]]) -> Optional[Spacing]:
        style_name = self.items[item_index].options.style
        return self.pdf.styles[style_name].box.margin
