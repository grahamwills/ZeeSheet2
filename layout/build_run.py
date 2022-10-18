from functools import lru_cache
from typing import Tuple, Union

import common
import layout.quality
from common import Extent
from drawing import Font, TextSegment, CheckboxSegment, PDF, TextFieldSegment, TextFontModifier, Segment
from layout.content import PlacedRunContent, ExtentTooSmallError
from structure import Run, Element
from structure import Style

LOGGER = common.configured_logger(__name__)


@lru_cache(maxsize=10000)
def _build_run(run: Run, width: float, style: Style, auto_align: str, pdf: PDF, modifier: TextFontModifier) -> PlacedRunContent:
    return RunBuilder(run, style, auto_align, width, pdf, modifier).build()


def place_run(run: Run, extent: Extent, style: Style, pdf: PDF, modifier: TextFontModifier, auto_align: str = None) -> PlacedRunContent:
    placed = _build_run(run, extent.width, style, auto_align, pdf, modifier)
    if placed.extent.height > extent.height:
        raise ExtentTooSmallError()

    # After alignment, it fills the width. Any unused space is captured in the quality
    placed.extent = Extent(extent.width, placed.extent.height)
    return placed


@lru_cache(maxsize=10000)
def split_text(text: str,
               font: Font,
               width: float,
               text_width: float,
               only_at_whitespace
               ) -> Tuple[int, float, bool]:
    """ Find a good splitting position for the text """

    n = len(text)
    if n < 2:
        return -1, 0, True

    # A guess at where we might find a good split
    guess = max(1, min(round(width * n / text_width), n - 2))

    # Step backwards through white spaces
    loc = 0
    wid = 0

    first = True
    for p in range(guess, 0, -1):
        try:
            if text[p].isspace() and not text[p + 1].isspace():
                w = font.width(text[:p])
                if w <= width:
                    loc = p
                    wid = w
                    break
                else:
                    first = False
        except IndexError as ex:
            LOGGER.error("{}   {}", guess, n)

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

    def __init__(self, run: Run, style: Style, auto_align: str, width: float, pdf: PDF, modifier: TextFontModifier):
        self.run = run
        self.width = width
        self.elements = run.children
        self.style = style
        self.txt_style = style.text
        self.font = pdf.get_font(style)
        self.align = style.text.align
        if self.align == 'auto':
            self.align = auto_align
        self.lines = []
        self.modifier = modifier

    def build(self) -> PlacedRunContent:

        segments = []
        width = self.width
        font = self.font
        color = self.style.get_color()
        line_spacing = font.line_spacing

        bad_breaks = breaks = 0

        x = left = y = 0
        line_start = 0
        textfield_on_this_line = None
        for element in self.elements:
            text = element.value
            modifier = element.modifier

            while text:
                if modifier == 'checkbox':
                    # Try to place checkbox on the line
                    w = line_spacing * 0.9
                    if x + w <= width:
                        segments.append(CheckboxSegment(text == 'X', x, y, w, font, color))
                        x += w
                        text = None
                elif modifier == 'textfield':
                    # Textfield has a minimum size based on content, plus a bit for the border
                    # When initially placing, we use the minimum size
                    w = min(font.width(text) + 4, 20)
                    if x + w <= width:
                        textfield_on_this_line = len(segments)
                        segments.append(TextFieldSegment(text, x, y, w, font, color))
                        x += w
                        text = None
                else:
                    if y > 0:
                        # No leading whitespace on second and subsequent lines
                        text = text.lstrip()

                    if modifier:
                        fnt = self.modifier.modify_font(font, modifier)
                        col = self.modifier.modify_color(color, modifier)
                    else:
                        fnt = font
                        col = color

                    w = fnt.width(text)
                    if x + w <= width:
                        # Happy path; it all fits
                        segments.append(TextSegment(text, x, y, w, fnt, col))
                        x += w
                        text = None
                    else:
                        # Need to split the line
                        p, w, is_bad = split_text(text, fnt, width - x, w, x > 0)
                        if p > 0:
                            segments.append(TextSegment(text[:p], x, y, w, fnt, col))
                            x += w
                            text = text[p:]
                            if is_bad:
                                bad_breaks += 1

                if text:
                    if x == left:
                        # We were unable to place it and had the whole space to place into
                        raise ExtentTooSmallError()

                    # Handle any text fields on this line, expanding to fill line
                    if textfield_on_this_line is not None:
                        self.expand_field_size(segments, textfield_on_this_line, width - x)
                        textfield_on_this_line = None
                    elif self.align != 'left':
                        self.align_segments(segments[line_start:], left, width)

                    # Start a new line, indenting as per the style
                    x = left = self.style.text.indent
                    y += line_spacing
                    breaks += 1
                    line_start = len(segments)

        # Handle any text fields on this line, expanding to fill line
        if textfield_on_this_line is not None:
            self.expand_field_size(segments, textfield_on_this_line, width - x)
        elif self.align != 'left':
            self.align_segments(segments[line_start:], left, width)

        # Set the extent to cover the whole space
        right = max(s.right for s in segments)
        outer = Extent(right, y + line_spacing)

        # Only count excess for the last lines; not using 'right' which would be for all lines
        excess = self.width - x

        # The good breaks equals all the breaks minus the bad ones
        quality = layout.quality.for_wrapping(excess, bad_breaks, breaks - bad_breaks)
        return PlacedRunContent(segments, self.style, outer, quality)

    @staticmethod
    def expand_field_size(segments: list[Segment],
                          index: int, dx: float):
        segments[index].width += dx
        for s in segments[index + 1:]:
            s.x += dx

    def align_segments(self, segments: list[Segment], left, width):
        if self.align == 'right':
            dx = width - segments[-1].right
        elif self.align == 'center':
            dx = (width + left - segments[-1].right) / 2
        else:
            dx = 0
        for s in segments:
            s.x += dx


def tiny_run() -> Run:
    """ Makes a small run to be added to a block as a filler item """
    return Run([Element(' ')])
