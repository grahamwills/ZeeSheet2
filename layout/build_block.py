from __future__ import annotations

import warnings
from copy import copy
from functools import lru_cache
from typing import Tuple, Optional, Union

import common
import layout.quality
from common import Extent, Point, Spacing, Rect
from common import configured_logger
from drawing import PDF
from structure import Block, style
from structure import BlockOptions, Run, Item
from . import build_run
from .content import PlacedContent, PlacedGroupContent, PlacedRectContent, make_image, make_frame, make_frame_box
from .packer import ColumnPacker
from .special_blocks import AttributeTableBuilder

LOGGER = configured_logger(__name__)

MIN_BLOCK_DIMENSION = 8
NO_SPACING = Spacing(0, 0, 0, 0)


def make_title(block: Block, inner: Rect, quality: str, extra_space: float, pdf: PDF) -> Tuple[
    Optional[PlacedContent], Spacing]:
    if not block.title or block.options.title == 'none':
        return None, NO_SPACING

    if block.options.title != 'simple':
        # warnings.warn(f"Border style '{block.options.title}' is not yet supported, treating as 'simple'")
        pass

    title_style = pdf.style(block.options.title_style, 'default-title')

    title_bounds = title_style.box.inset_within_padding(inner)
    placed = place_block_title(block, title_bounds, quality, pdf)
    placed.location = title_bounds.top_left

    r1 = title_style.box.inset_within_margin(inner)
    r2 = title_style.box.outset_to_border(placed.bounds)
    plaque_rect = Rect(r1.left, r1.right, r2.top, r2.bottom)
    plaque_rect_to_draw = plaque_rect

    if title_style.box.has_border():
        # Need to reduce the plaque to draw INSIDE the border
        plaque_rect_to_draw = plaque_rect - Spacing.balanced(title_style.box.width / 2)

    # When we have a border effect, we need to expand the plaque to make sure it is behind it all.
    # But not below, since the simple plaque is on the top
    if extra_space:
        plaque_rect_to_draw = plaque_rect_to_draw + Spacing(extra_space, extra_space, extra_space, 0)

    plaque_quality = layout.quality.for_decoration()
    plaque = PlacedRectContent(plaque_rect_to_draw, title_style, plaque_quality)
    title_extent = plaque_rect.extent + title_style.box.margin
    spacing = Spacing(0, 0, title_extent.height, 0)

    group_quality = placed.quality  # The plaque makes no difference, so the group quality is the same as the title
    return PlacedGroupContent.from_items([plaque, placed], group_quality, title_extent), spacing


def locate_title(title: PlacedContent, outer: Rect, content_extent: Extent, pdf: PDF) -> None:
    """ Defines the title location and returns the bounds of everything including the title"""

    # Currently we only do simple -- at the top
    if title:
        title.location = Point(0, 0)


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

    # Create the title. Pass in the extra padding space needed with extra to ensure we cover the clip area
    title, title_spacing = make_title(block, outer, quality, extra_space * 2, pdf)

    if not block.children and not image:
        if not title:
            warnings.warn('Block defined without title, image or content')
            return None
        else:
            return title

    # Reduce space for the items to account for the title.
    # Inset for padding and border
    item_bounds = outer - title_spacing
    if block.children:
        placed_children = place_block_children(block, item_bounds, quality, pdf)
    else:
        # The image is the only content in the block -- always put it at the top
        opt = block.options
        item_bounds = item_bounds.pad(extra_space)
        placed_children = make_image(image, item_bounds, opt.image_mode, opt.image_width, opt.image_height,
                                     opt.image_anchor, block.options.image_brightness, block.options.image_contrast,
                                     force_to_top=True)

    locate_title(title, outer, placed_children.bounds, pdf)

    # Frame everything
    total_height = placed_children.bounds.bottom
    if title:
        total_height = max(total_height, title.bounds.bottom)
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
    items = [i for i in (frame, placed_children, title) if i]

    block_extent = Extent(size.width, total_height)
    cell_qualities = [i.quality for i in items]
    block_quality = layout.quality.for_columns([total_height], [cell_qualities], 0)
    result = PlacedGroupContent.from_items(items, block_quality, extent=block_extent)
    result.clip_item = frame.items[0] if isinstance(frame, PlacedGroupContent) else frame
    if not result.clip_item:
        # I am not sure why this is needed
        modified_bounds = frame_bounds - Spacing(0, 0, 0, extra_space)
        result.clip_item = PlacedRectContent(modified_bounds, main_style, layout.quality.for_decoration())

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


def place_block_title(block: Block, bounds: Rect, quality: str, pdf: PDF) -> Optional[PlacedGroupContent]:
    debug_name = common.name_of(block)
    k = len(block.title.children)
    packer = BlockTablePacker(debug_name, bounds, [block.title], k, block.options.title_style, quality, pdf)
    return packer.place_table(equal=block.options.equal)


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
