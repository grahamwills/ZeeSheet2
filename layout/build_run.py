from functools import lru_cache
from typing import Tuple

import layout.quality
from common import Extent, Point
from generate.fonts import Font
from generate.pdf import TextSegment, CheckboxSegment, PDF
from layout.content import PlacedRunContent, ExtentTooSmallError
from structure import Run, Element
from structure.style import Style


@lru_cache(maxsize=1000)
def place_run(run: Run, extent: Extent, style: Style, pdf: PDF) -> PlacedRunContent:
    bldr = RunBuilder(run, style, extent, pdf)
    placed = bldr.build()

    # Apply alignment
    if style.text.align == 'right':
        placed.offset_content(extent.width - placed.extent.width)
    elif style.text.align == 'center':
        placed.offset_content((extent.width - placed.extent.width) / 2)

    # After alignment, it fills the width. Any unused space is captured in the extent
    placed.extent = Extent(extent.width, placed.extent.height)
    return placed


@lru_cache(maxsize=1000)
def split_text(text: str,
               font: Font,
               width: float,
               text_width: float,
               only_at_whitespace
               ) -> Tuple[int, float, bool]:
    """ Find a good splitting position for the text """

    n = len(text)

    # A guess at where we might find a good split
    guess = max(1, min(round(width * n / text_width), n - 2))

    # Step backwards through white spaces
    loc = 0
    wid = 0

    first = True
    for p in range(guess, 1, -1):
        if text[p].isspace() and not text[p + 1].isspace():
            w = font.width(text[:p])
            if w <= width:
                loc = p
                wid = w
                break
            else:
                first = False

    if loc:
        # We found a good breaking point
        if first:
            # There maybe one further ahead, so we need to keep looking and noting better break points
            for p in range(guess, n - 1):
                if text[p].isspace() and not text[p + 1].isspace():
                    w = font.width(text[:p])
                    if w <= width:
                        loc = p
                        wid = w
                    else:
                        break

    if loc or only_at_whitespace:
        return loc, wid, False

    # Now try a break anywhere
    w = font.width(text[:guess])
    if w > width:
        # Search backwards until something fits
        for p in range(guess - 1, 0, -1):
            w = font.width(text[:p])
            if w <= width:
                return p, w, True
    else:
        # Search forward while we have a good fit
        loc = guess
        wid = w
        for p in range(guess, n - 1):
            w = font.width(text[:p])
            if w <= width:
                loc = guess
                wid = w
            else:
                break

    return loc, wid, True


class RunBuilder:

    def __init__(self, run: Run, style: Style, extent: Extent, pdf: PDF):
        self.run = run
        self.extent = extent
        self.elements = run.children
        self.style = style
        self.font = pdf.get_font(style)

    def build(self) -> PlacedRunContent:

        segments = []
        width = self.extent.width
        height = self.extent.height

        # Keep same line spacing regardless of font changes
        line_spacing = self.font.line_spacing

        clipped = bad_breaks = good_breaks = 0

        x = 0
        y = 0
        right = 0
        last_top_right = (0, 0)
        for element in self.elements:
            text = element.value
            modifier = element.modifier
            font = self.font
            if modifier:
                font = font.modify(element.modifier == 'strong', element.modifier == 'emphasis')

            while text:

                if y > 0 and x == 0:
                    # No leading white space on new lines
                    text = text.lstrip()

                # If it does not fit vertically, record how much was clipped (in pixels) and do nothing else
                if y + line_spacing > height:
                    if y == 0:
                        raise ExtentTooSmallError()
                    clipped += font.width(text) * line_spacing
                    text = None
                    continue

                if modifier == 'checkbox':
                    # Try to place checkbox on the line
                    checkbox_width = (font.ascent + font.descent) * 1.1
                    if x + checkbox_width <= width:
                        segments.append(CheckboxSegment(text == 'X', Point(x, y), font))
                        x += checkbox_width
                        last_top_right = (x, y)
                        right = max(right, x)
                        text = None

                else:
                    # Place as much text as possible on this line
                    text_width = font.width(text)
                    if x + text_width <= width:
                        # Happy path; it all fits
                        segments.append(TextSegment(text, Point(x, y), font))
                        x += text_width
                        last_top_right = (x, y)
                        right = max(right, x)
                        text = None
                    else:
                        # Need to split the line
                        p, text_width, is_bad = split_text(text, font, width - x, text_width, x > 0)
                        if p > 0:
                            segments.append(TextSegment(text[:p], Point(x, y), font))
                            x += text_width
                            last_top_right = (x, y)
                            right = max(right, x)
                            text = text[p:]
                            if is_bad:
                                bad_breaks += 1

                if text:
                    if x == 0:
                        # We were unable to place it and had the whole space to place into
                        raise ExtentTooSmallError()
                    else:
                        # Start a new line
                        x = 0
                        y += line_spacing
                        good_breaks += 1

        bottom = last_top_right[1] + line_spacing
        outer = Extent(right, bottom)

        good_breaks -= bad_breaks  # They have been double-counted
        excess = self.extent.width - last_top_right[0]

        quality = layout.quality.for_wrapping(self.run, excess, clipped, bad_breaks, good_breaks, bottom)
        content = PlacedRunContent(segments, self.style, outer, quality, required_width=last_top_right[0])

        return content


def tiny_run() -> Run:
    """ Makes a small run to be added to a block as a filler item """
    return Run([Element(' ')])
