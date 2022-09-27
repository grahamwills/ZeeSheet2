from __future__ import annotations

import warnings
from copy import copy
from functools import lru_cache
from typing import Tuple, Optional

from common import Extent, Point, Spacing, Rect
from common import configured_logger
from generate.pdf import PDF
from structure import Block, style
from structure.model import ContainerOptions, Run, Item
from . import build_run, content
from .content import PlacedContent, PlacedGroupContent, ItemDoesNotExistError, PlacedRectContent, make_image
from .packer import ColumnPacker

LOGGER = configured_logger(__name__)

MIN_BLOCK_DIMENSION = 8
NO_SPACING = Spacing(0, 0, 0, 0)


def make_title(block: Block, inner: Rect, pdf: PDF) -> Tuple[Optional[PlacedContent], Spacing]:
    if not block.title or block.options.title == 'none':
        return None, NO_SPACING

    if block.options.title != 'simple':
        # warnings.warn(f"Border style '{block.options.title}' is not yet supported, treating as 'simple'")
        pass

    title_style = pdf.styles[block.options.title_style]

    title_bounds = title_style.box.inset_within_padding(inner)
    placed = copy(build_run.place_run(block.title, title_bounds.extent, title_style, pdf))
    placed.location = title_bounds.top_left

    r1 = title_style.box.inset_within_margin(inner)
    r2 = title_style.box.outset_to_border(placed.bounds)
    plaque_rect = Rect(r1.left, r1.right, r2.top, r2.bottom)
    plaque_rect_to_draw = plaque_rect

    if title_style.box.has_border():
        # Need to reduce the plaque to draw INSIDE the border
        plaque_rect_to_draw = plaque_rect - Spacing.balanced(title_style.box.width / 2)

    plaque = PlacedRectContent(plaque_rect_to_draw.extent, plaque_rect_to_draw.top_left, None, title_style)
    title_extent = plaque_rect.extent + title_style.box.margin
    spacing = Spacing(0, 0, title_extent.height, 0)

    return PlacedGroupContent.from_items([plaque, placed], title_extent), spacing


def locate_title(title: PlacedContent, outer: Rect, content_extent: Extent, pdf: PDF) -> None:
    """ Defines the title location and returns the bounds of everything including the title"""

    # Currently we only do simple -- at the top
    if title:
        title.location = Point(0, 0)


def place_block(block: Block, size: Extent, pdf: PDF) -> Optional[PlacedContent]:
    """ Margins have already been inset when we get into here"""

    main_style = pdf.styles[block.options.style]
    container = Rect(0, size.width, 0, size.height)

    image = pdf.get_image(block.options.image)

    # Inset for just the border; everything lives inside the border
    if main_style.box.has_border():
        outer = container - Spacing.balanced(main_style.box.width)
    else:
        outer = container

    # Create the title and insets to allow room for it
    title, title_spacing = make_title(block, outer, pdf)

    if not block.children and not image:
        if not title:
            warnings.warn('Block defined without title, image or content. It will be ignored.')
            raise ItemDoesNotExistError()
        else:
            return title

    # Reduce space for the items to account for the title.
    # Inset for padding and border
    item_bounds = outer - title_spacing
    if block.children:
        placed_children = place_block_children(block, item_bounds, pdf)
    else:
        # The image is the only content in the block
        opt = block.options
        placed_children = make_image(image, item_bounds, opt.image_mode, opt.image_width, opt.image_height,
                                     opt.image_anchor)

    locate_title(title, outer, placed_children.bounds, pdf)

    # Frame everything
    total_height = placed_children.bounds.bottom
    if title:
        total_height = max(total_height, title.bounds.bottom)
    if main_style.box.has_border():
        total_height += main_style.box.width
    frame_bounds = Rect(0, size.width, 0, total_height)
    frame = content.make_frame(frame_bounds, main_style)

    # Make the valid items
    items = [i for i in (frame, placed_children, title) if i]
    if len(items) == 1:
        return items[0]

    block_extent = Extent(size.width, total_height)
    return PlacedGroupContent.from_items(items, extent=block_extent)


@lru_cache
def place_block_children(block: Block, item_bounds: Rect, pdf) -> Optional[PlacedGroupContent]:
    if block.children:
        packer = BlockColumnPacker(item_bounds, block, pdf)
        return packer.place_table()
    else:
        return None


class BlockColumnPacker(ColumnPacker):
    def __init__(self, bounds: Rect, block: Block, pdf: PDF):
        column_count = max(len(item.children) for item in block.children)
        self.items = block.children
        self.pdf = pdf
        self.content_style = pdf.styles[block.options.style]
        super().__init__(bounds, len(block.children), column_count)

    def margins_of_item(self, idx) -> Spacing:
        # All block items share common margins
        return self.content_style.box.padding

    def place_item(self, idx: Tuple[int, int], extent: Extent) -> PlacedContent:
        items = self.items[idx[0]]
        if idx[1] < len(items.children):
            return copy(build_run.place_run(items[idx[1]], extent, self.content_style, self.pdf))
        else:
            raise ItemDoesNotExistError()


def tiny_block() -> Block:
    """ Makes a small block to be added to a section when there are too few of them """
    options = ContainerOptions('none', style.Defaults.hidden.name)
    item = Item([build_run.tiny_run()])
    return Block(Run(), [item], options)
