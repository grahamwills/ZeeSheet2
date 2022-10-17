from common import Rect, Spacing, Point
from drawing import PDF
from structure import Block
from . import quality
from .content import PlacedContent, PlacedRectContent, PlacedGroupContent

NO_SPACING = Spacing(0, 0, 0, 0)


class TitleBuilder:
    block: Block
    bleed_space: float
    pdf: PDF
    title: PlacedContent or None
    content_spacing: Spacing
    frame_spacing: Spacing
    title_inside_clip: bool

    def __init__(self, block: Block, bleed_space: float, pdf: PDF):
        self.block = block
        self.bleed_space = bleed_space  # Space to add to title to cover ragged borders
        self.pdf = pdf
        self.style = pdf.style(block.options.title_style, 'default-title')
        self.title_inside_clip = False
        self.content_spacing = NO_SPACING
        self.frame_spacing = NO_SPACING

    def build_for(self, bounds: Rect):
        block = self.block
        if not block.title or block.options.title == 'none':
            self.title = None
        elif block.options.title == 'inline':
            self.inline_title(bounds)
        elif block.options.title == 'banner':
            self.banner_title(bounds)
        else:
            raise RuntimeError("Unexpected block title method: " + str(block.options.title))

    def place_block_title(self, bounds: Rect) -> PlacedGroupContent:
        raise NotImplementedError()

    def inline_title(self, bounds: Rect):
        title_style = self.style
        title_font = self.pdf.get_font(title_style)
        pad = title_style.box.padding
        # Only pad left to right as we want to draw directly over the frame
        title_bounds = Rect(bounds.left + pad.left, bounds.right - pad.right, bounds.top, bounds.bottom)
        placed = self.place_block_title(title_bounds)
        placed.location = Point(title_bounds.left, title_bounds.top - title_font.descent / 2)
        drawn = placed.drawn_bounds()

        drawn_bounds = drawn + title_style.box.padding
        plaque = PlacedRectContent(drawn_bounds, title_style, quality.for_decoration())
        self.title = PlacedGroupContent.from_items([plaque, placed], placed.quality, plaque.extent)
        self.content_spacing = Spacing(0, 0, placed.extent.height, 0)
        self.frame_spacing = Spacing(0, 0, placed.extent.height / 2, 0)

    def banner_title(self, bounds: Rect):
        title_style = self.style
        title_bounds = title_style.box.inset_within_padding(bounds)
        placed = self.place_block_title(title_bounds)
        placed.location = title_bounds.top_left
        r1 = title_style.box.inset_within_margin(bounds)
        r2 = title_style.box.outset_to_border(placed.bounds)
        plaque_rect = Rect(r1.left, r1.right, r2.top, r2.bottom)
        plaque_rect_to_draw = plaque_rect
        if title_style.box.has_border():
            # Need to reduce the plaque to draw INSIDE the border
            plaque_rect_to_draw = plaque_rect - Spacing.balanced(title_style.box.width / 2)
        # When we have a border effect, we need to expand the plaque to make sure it is behind it all.
        # But not below, since the simple plaque is on the top
        if self.bleed_space:
            plaque_rect_to_draw = plaque_rect_to_draw + Spacing(self.bleed_space, self.bleed_space, self.bleed_space, 0)
        plaque_quality = quality.for_decoration()
        plaque = PlacedRectContent(plaque_rect_to_draw, title_style, plaque_quality)
        title_extent = plaque_rect.extent + title_style.box.margin
        # The plaque makes no difference, so the group quality is the same as the title
        self.title = PlacedGroupContent.from_items([plaque, placed], placed.quality, title_extent)
        self.content_spacing = Spacing(0, 0, title_extent.height, 0)
        self.title_inside_clip = True
