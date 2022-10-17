from __future__ import annotations

import warnings
from functools import lru_cache
from typing import Tuple, Optional, Union

import common
import layout.quality
from common import Extent, Spacing, Rect
from common import configured_logger
from drawing import PDF
from structure import Block, style
from structure import BlockOptions, Run, Item
from . import build_run
from .build_title import TitleBuilder
from .content import PlacedContent, PlacedGroupContent, PlacedRectContent, make_image, make_frame, make_frame_box
from .packer import ColumnPacker
from .special_blocks import AttributeTableBuilder

LOGGER = configured_logger(__name__)

MIN_BLOCK_DIMENSION = 8
NO_SPACING = Spacing(0, 0, 0, 0)


class BlockTitleBuilder(TitleBuilder):
    def __init__(self, block: Block, pdf: PDF, bleed_space: float, layout_quality: str):
        super().__init__(block, bleed_space, pdf)
        self.layout_quality = layout_quality

    def place_block_title(self, bounds: Rect) -> PlacedGroupContent:
        block = self.block
        debug_name = common.name_of(block)
        k = len(block.title.children)
        packer = BlockTablePacker(debug_name, bounds, [block.title], k,
                                  block.options.title_style, self.layout_quality, self.pdf)
        return packer.place_table(equal=block.options.equal)


def place_block(block: Block, size: Extent, quality: str, pdf: PDF) -> Optional[PlacedContent]:
    """ Margins have already been inset when we get into here"""

    main_style = pdf.style(block.options.style, 'default-block')
    effect = main_style.get_effect()
    container = Rect(0, size.width, 0, size.height)

    if block.options.method == 'attributes':
        builder = AttributeTableBuilder(block, size, pdf)
        return builder.build()

    image = pdf.get_image(block.options.image)

    # Inset for just the border; everything lives inside the border
    if main_style.box.has_border():
        outer = container - Spacing.balanced(main_style.box.width)
    else:
        outer = container

    # We may need extra space around the frame for the effect to flow into
    extra_space = effect.padding()
    if extra_space > 0:
        # Half the padding lies inside the frame
        outer = outer.pad(-extra_space / 2)

    titler = BlockTitleBuilder(block, pdf, extra_space * 2, quality)
    titler.build_for(outer)

    if not block.children and not image:
        if not titler.title:
            warnings.warn('Block defined without title, image or content')
            return None
        else:
            return titler.title

    # Reduce space for the items to account for the title.
    # Inset for padding and border
    item_bounds = outer - titler.spacing
    if block.children:
        placed_children = place_block_children(block, item_bounds, quality, pdf)
    else:
        # The image is the only content in the block -- always put it at the top
        opt = block.options
        item_bounds = item_bounds.pad(extra_space)
        placed_children = make_image(image, item_bounds, opt.image_mode, opt.image_width, opt.image_height,
                                     opt.image_anchor, block.options.image_brightness, block.options.image_contrast,
                                     force_to_top=True)

    titler.locate_title()

    # Frame everything
    total_height = placed_children.bounds.bottom
    if titler.title_inside_clip:
        total_height = max(total_height, titler.title.bounds.bottom)
    if main_style.box.has_border():
        total_height += main_style.box.width
    total_height += extra_space / 2
    frame_bounds = Rect(0, size.width, 0, total_height)

    if block.children:
        frame = make_frame(frame_bounds, main_style, block.options, pdf)
    else:
        # We are showing just an image, which is our children, so do not add it here also
        frame = make_frame_box(frame_bounds, main_style)

    # Make the valid items
    items = []
    if frame:
        items.append(frame)
    if placed_children:
        items.append(placed_children)
    if titler.title_inside_clip:
        items.append(titler.title)

    block_extent = Extent(size.width, total_height)
    cell_qualities = [i.quality for i in items]
    block_quality = layout.quality.for_columns([total_height], [cell_qualities], 0)
    result = PlacedGroupContent.from_items(items, block_quality, extent=block_extent)
    result.clip_item = frame.items[0] if isinstance(frame, PlacedGroupContent) else frame
    if not result.clip_item:
        # I am not sure why this additional spacing is needed
        modified_bounds = frame_bounds - Spacing(0, 0, 0, extra_space)
        result.clip_item = PlacedRectContent(modified_bounds, main_style, layout.quality.for_decoration())
    if titler.title and not titler.title_inside_clip:
        result = PlacedGroupContent.from_items([result, titler.title], block_quality, extent=block_extent)

    # Mark as hidden if our style indicated it was to be hidden
    if main_style.name == style.StyleDefaults.hidden.name:
        result.hidden = True

    return result


@lru_cache
def place_block_children(block: Block, item_bounds: Rect, quality: str, pdf) -> Optional[PlacedGroupContent]:
    if block.children:
        debug_name = common.name_of(block)
        packer = BlockTablePacker(debug_name, item_bounds, block.children,
                                  block.column_count(), block.options.style, quality, pdf)
        return packer.place_table(equal=block.options.equal)
    else:
        return None


class BlockTablePacker(ColumnPacker):
    item_map: dict[Tuple[int, int], Run]
    span_map: dict[Tuple[int, int], int]

    def __init__(self, debug_name: str, bounds: Rect, items: list[Item], k: int, style_name: str, quality: str,
                 pdf: PDF):
        max_width_combos = self.QUALITY_TO_COMBOS[quality.lower()]

        column_count = max(len(item.children) for item in items)
        self.pdf = pdf
        self.content_style = pdf.style(style_name)
        super().__init__(debug_name, bounds, len(items), column_count, max_width_combos)
        self.alignments = '.CR'

        # Set defautl alignments
        self.alignments = ['center'] * self.k
        self.alignments[-1] = 'right'
        self.alignments[0] = 'left'

        # Set maps for cells and spans
        self.item_map = {}
        self.span_map = {}
        for r, row in enumerate(items):
            for c, item in enumerate(row):
                self.item_map[(r, c)] = item
                if item == row[-1]:
                    # Last item fills to the end
                    self.span_map[(r, c)] = k - c
                else:
                    self.span_map[(r, c)] = 1

    def margins_of_item(self, idx) -> Spacing:
        # All block items share common margins
        return self.content_style.box.padding

    def place_item(self, idx: Tuple[int, int], extent: Extent) -> PlacedContent:
        item = self.item_map[idx]
        align = self.alignments[idx[1]]
        return build_run.place_run(item, extent, self.content_style, self.pdf, align)

    def span_of_item(self, idx: Union[int, Tuple[int, int]]) -> int:
        try:
            return self.span_map[idx]
        except KeyError:
            # Does not exist
            return 0


def tiny_block() -> Block:
    """ Makes a small block to be added to a section when there are too few of them """
    options = BlockOptions(title='none', style=style.StyleDefaults.hidden.name)
    item = Item([build_run.tiny_run()])
    return Block(Item(), [item], options)
