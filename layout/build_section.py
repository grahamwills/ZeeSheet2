from typing import Union, Tuple, Optional, List

import common
from common import Extent, Rect, Spacing
from generate.pdf import PDF
from layout import build_block
from layout.content import PlacedContent, PlacedGroupContent, make_frame, PlacedImageContent
from layout.packer import ColumnPacker, ColumnFit
from structure import StructureUnit, Section

LOGGER = common.configured_logger(__name__)


def place_section(section: Section, extent: Extent, pdf: PDF) -> PlacedGroupContent:
    section_style = pdf.style(section.options.style, 'default-section')
    bounds = Rect(0, extent.width, 0, extent.height)
    content_bounds = section_style.box.inset_from_margin_within_padding(bounds)

    # Ensure that we have enough children for the column requested
    blocks = section.children
    while len(blocks) < section.options.columns:
        blocks = blocks + [build_block.tiny_block()]

    sp = SectionPacker(content_bounds, blocks, section.options.columns, pdf, granularity=25)
    content = sp.place_in_columns()

    # Make the frame
    frame_bounds = section_style.box.outset_to_border(content.bounds)
    frame = make_frame(frame_bounds, section_style, section.options, pdf)
    if frame:
        # Frame adds nothing, so just use content's quality
        content = PlacedGroupContent.from_items([frame, content], content.quality)

    return content


class SectionPacker(ColumnPacker):

    def __init__(self, bounds: Rect, items: List[type(StructureUnit)], column_count: int, pdf, granularity: int = 20):
        self.items = items
        self.pdf = pdf
        super().__init__(bounds, len(items), column_count, granularity=granularity)

    def place_item(self, item_index: Union[int, Tuple[int, int]], extent: Extent) -> Optional[PlacedContent]:
        return build_block.place_block(self.items[item_index], extent, self.pdf)

    def margins_of_item(self, item_index: Union[int, Tuple[int, int]]) -> Optional[Spacing]:
        style_name = self.items[item_index].options.style
        return self.pdf.style(style_name, 'default-block').box.margin

    def post_placement_modifications(self, columns: list[ColumnFit]) -> list[ColumnFit]:
        """ If images have flexible sizes, reduce them to match heights if that helps """
        shrinkable_images = []
        lowest_other = -9e99
        for fit in columns:
            if fit.items:
                # We need only consider the last one - -the lowest in the column
                placed = fit.items[-1]
                if isinstance(placed, PlacedImageContent) and placed.mode in {'fill', 'stretch'}:
                    shrinkable_images.append((placed, fit))
                else:
                    lowest_other = max(lowest_other, placed.bounds.bottom)

        if shrinkable_images and lowest_other > 0:
            # We only care about shrinkable images that are too big
            for s, fit in shrinkable_images:
                if s.bounds.bottom > lowest_other:
                    fit.height -= s.shrink_to_fit(bottom=lowest_other)

        return columns

    def report(self, widths: List[float], counts: List[int], placed: PlacedGroupContent, final: bool = False):
        q = placed.quality
        text = 'Best Placement' if final else 'Trial Placement'
        LOGGER.debug(f"{text}: "
                     f"counts=[{common.to_str(counts, 0)}]: "
                     f"widths=[{common.to_str(widths, 0)}], "
                     f"quality={q.unplaced}|{q.unplaced_descendants}"
                     f"|{common.to_str(q.clipped, 1)}|{common.to_str(q.minor_score())}")
