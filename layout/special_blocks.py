from functools import lru_cache

from reportlab.lib.colors import Color

import layout
from common import Extent, Rect, Spacing
from drawing import Font
from drawing import PDF, TextSegment
from layout import PlacedPathContent, PlacedGroupContent, PlacedRunContent, ExtentTooSmallError
from structure import Block


@lru_cache
def text_details(texts: tuple[str], font: Font):
    boxes = tuple(font.bbox(t) for t in texts)
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

        # The bulb on the left extends to xa. The center part extends to xb
        xa = e_width + e_pad.horizontal
        xb = xa + c_width + c_pad.horizontal

        if xb > self.extent.width:
            raise ExtentTooSmallError(self.block, f"Width of {self.extent.width} could not fit central text")

        excess = self.extent.width - xb
        xb = self.extent.width

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
        top = 0
        for row, name_width, value_width in zip(rows, c_widths, e_widths):
            coords += [(0, top), (xa, top), (xa, top + y1), (xb, top + y1),
                       (xb, top + y2), (xa, top + y2), (xa, top + y3,), (0, top + y3),
                       tuple()]

            name_box = Rect(xa, xb, top + y1, top + y2)
            value_box = Rect(0, xa, top, top + y3)

            name = self.text_in_box(row[0], name_box, c_pad, c_align, name_width, c_height, c_dy, font, color)
            value = self.text_in_box(row[1], value_box, e_pad, e_align, value_width, e_height, e_dy, font2, color2)
            attributes.append(name)
            values.append(value)

            top += max(ha, hb) + v_gap

        bounds = Rect(0, self.extent.width, 0, top)

        q_decoration = layout.quality.for_decoration()
        placed_attributes = PlacedRunContent(attributes, self.style, bounds.extent, q_decoration, bounds.top_left)
        placed_values = PlacedRunContent(values, self.style2, bounds.extent, q_decoration, bounds.top_left)

        # The excess is really minor -- downgrade it a lot
        quality = layout.quality.for_wrapping(excess * 0.5, 0, 0)
        path = PlacedPathContent(coords, bounds, self.style, quality)

        return PlacedGroupContent.from_items([path, placed_attributes, placed_values], quality, bounds.extent)

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
