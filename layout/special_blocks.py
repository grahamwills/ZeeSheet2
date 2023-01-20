from functools import lru_cache

from reportlab.lib.colors import Color

import layout
from common import Extent, Rect, Spacing, configured_logger
from drawing import Font
from drawing import PDF, TextSegment
from layout import PlacedPathContent, PlacedGroupContent, PlacedRunContent, ExtentTooSmallError
from structure import Block

LOGGER = configured_logger(__name__)

@lru_cache
def text_details(texts: tuple[str], font: Font):
    boxes = tuple(font.bbox(t) for t in texts)
    if not boxes:
        return 0, 0, 0, tuple()
    overall = Rect.union(boxes)
    widths = tuple(r.width for r in boxes)

    # Heights are inverted -- top is the distance below the baseline,
    height = overall.height
    dy = -overall.top

    return overall.width, height, dy, widths


class AttributeTableBuilder:
    def __init__(self, block: Block, extent: Extent, pdf: PDF):
        self.block = block
        self.extent = extent
        self.pdf = pdf
        self.k = block.column_count()
        self.style = pdf.style(block.options.style)
        self.style2 = pdf.style(block.options.title_style)

    def build(self) -> PlacedGroupContent:
        rows = self.make_rows()

        three_sections = len(rows[0]) > 2

        v_gap = self.style2.box.margin.vertical
        if self.style.box.has_border():
            v_gap += self.style.box.width

        font = self.pdf.get_font(self.style)
        font2 = self.pdf.get_font(self.style2)
        color = self.style.get_color()
        color2 = self.style2.get_color()

        c_width, c_height, c_dy, c_widths = text_details(tuple(row[0] for row in rows), font)
        e_width, e_height, e_dy, e_widths = text_details(tuple(row[1] for row in rows), font2)

        c_pad = self.style.box.padding
        e_pad = self.style2.box.padding
        c_align = self.style.text.align
        e_align = self.style2.text.align

        if three_sections:
            f_width, f_height, f_dy, f_widths = text_details(tuple(row[2] for row in rows), font)
            f_pad = c_pad
        else:
            f_width = f_height = f_dy = 0
            f_widths = [0] * len(rows)
            f_pad = Spacing.balanced(0)

        # The bulb on the left extends to xa.
        # The center part extends to xb
        # The right part extends to xc
        xa = e_width + e_pad.horizontal
        xb = xa + c_width + c_pad.horizontal
        xc = xb + f_width + f_pad.horizontal

        if xc > self.extent.width:
            raise ExtentTooSmallError(self.block, f"Width of {self.extent.width} could not fit central text")

        excess = self.extent.width - xc
        xb += excess
        xc += excess

        # The bulb height is ha; the center height is hb
        ha = e_height + e_pad.vertical + max(0, e_dy)
        hb = c_height + c_pad.vertical + max(0, c_dy)

        # So the vertical offsets are
        y1 = (ha - hb) / 2
        y2 = y1 + hb
        y3 = ha

        coords = []
        attributes = []
        values = []
        values2 = []
        top = 0
        for row, name_width, value_width, value2_width in zip(rows, c_widths, e_widths, f_widths):
            coords += [(0, top), (xa, top), (xa, top + y1), (xc, top + y1),
                       (xc, top + y2), (xa, top + y2), (xa, top + y3,), (0, top + y3),
                       tuple()]

            name_box = Rect(xa, xb, top + y1, top + y2)
            value_box = Rect(0, xa, top, top + y3)
            value2_box = Rect(xb, xc, top + y1, top + y2)

            name = self.text_in_box(row[0], name_box, c_pad, c_align, name_width, c_height, c_dy, font, color)
            attributes.append(name)
            value = self.text_in_box(row[1], value_box, e_pad, e_align, value_width, e_height, e_dy, font2, color2)
            values.append(value)

            if three_sections:
                value2 = self.text_in_box(row[2], value2_box, f_pad, c_align, value2_width, f_height, f_dy, font, color2)
                values2.append(value2)

            top += max(ha, hb) + v_gap

        bounds = Rect(0, self.extent.width, 0, top)
        quality = layout.quality.for_wrapping(excess, 0, 0)
        path = PlacedPathContent(coords, bounds, self.style, quality)

        q_decoration = layout.quality.for_decoration()
        placed_attributes = PlacedRunContent(attributes, self.style, bounds.extent, q_decoration, bounds.top_left)
        placed_values = PlacedRunContent(values, self.style2, bounds.extent, q_decoration, bounds.top_left)

        parts = [path, placed_attributes, placed_values]

        if three_sections:
            placed_values2 = PlacedRunContent(values2, self.style, bounds.extent, q_decoration, bounds.top_left)
            parts.append(placed_values2)

        return PlacedGroupContent.from_items(parts, quality, bounds.extent)

    def make_rows(self) -> list[list[str, ...]]:
        rows = []
        for item in self.block.children:
            row = [run.as_simple_text() for run in item]
            if len(row) == 1:
                row = [' '] + row
            rows.append(row)
        return rows

    def text_in_box(self, txt: str, box: Rect, pad: Spacing, align: str,
                    width: float, height: float, dy: float, font: Font, color: Color) -> TextSegment:
        box = box - pad
        if align == 'left':
            dx = 0
        elif align == 'right':
            dx = box.width - width
        else:
            dx = (box.width - width) / 2

        # center in the box. The '0.75 * dy - 0.5' is a fudge factor, but does seem to make the results prettier
        y = box.center.y - font.ascent + height / 2 - 0.75 * dy - 0.5

        return TextSegment(txt, box.left + dx, y, width, font, color)
