from copy import copy
from functools import lru_cache
from typing import Tuple, Union

import layout.quality
from common import Extent
from drawing import Font
from drawing import TextSegment, CheckboxSegment, PDF, TextFieldSegment
from layout.content import PlacedRunContent, ExtentTooSmallError
from structure import Run, Element
from structure import Style


@lru_cache(maxsize=10000)
def _build_run(run: Run, extent: Extent, style: Style, pdf: PDF) -> PlacedRunContent:
    return RunBuilder(run, style, extent, pdf).build()


def place_run(run: Run, extent: Extent, style: Style, pdf: PDF, forced_align: str = None) -> PlacedRunContent:
    placed = copy(_build_run(run, extent, style, pdf))
    align = forced_align or style.text.align

    if align == 'right':
        dx = extent.width - placed.extent.width
        placed.offset_content(dx)
    elif align == 'center':
        dx = (extent.width - placed.extent.width) / 2
        placed.offset_content(dx)
    else:
        dx = 0

    segments = placed.segments
    if segments and segments[0].y != segments[-1].y:
        # May need special alignment for last line
        last_align = style.text.align_last
        len_last = segments[-1].x + segments[-1].width

        # Choose alignment
        if last_align == 'same':
            last_align = align
        elif last_align == 'auto':
            if align == 'left' and len_last < placed.extent.width / 2:
                last_align = 'right'
            else:
                last_align = align

        # If needed, re-align the last line
        if last_align != align:
            if last_align == 'right':
                dx = extent.width - len_last - dx
            elif last_align == 'center':
                dx = (extent.width - len_last) / 2 - dx
            else:
                dx = -dx
            last_line_y = segments[-1].y

            # Move all segments on that line
            for segment in segments:
                if segment.y == last_line_y:
                    segment.x += dx

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
        if line_spacing > height:
            raise ExtentTooSmallError()

        bad_breaks = breaks = 0

        x = y = 0

        textfield_on_this_line = None
        for element in self.elements:
            text = element.value
            modifier = element.modifier
            font = self.font
            if modifier == 'emphasis' or modifier == 'strong':
                font = font.modify(element.modifier)

            while text:
                if modifier == 'checkbox':
                    # Try to place checkbox on the line
                    w = (font.ascent + font.descent) * 1.1
                    if x + w <= width:
                        segments.append(CheckboxSegment(text == 'X', x, y, w, font))
                        x += w
                        text = None
                elif modifier == 'textfield':
                    # Textfield has a minimum size based on content, plus a bit for the border
                    # When initially placing, we use the minimum size
                    w = min(font.width(text) + 4, 20)
                    if x + w <= width:
                        textfield_on_this_line = len(segments)
                        segments.append(TextFieldSegment(text, x, y, w, font))
                        x += w
                        text = None
                else:
                    # Place as much text as possible on this line
                    w = font.width(text)
                    if x + w <= width:
                        # Happy path; it all fits
                        segments.append(TextSegment(text, x, y, w, font))
                        x += w
                        text = None
                    else:
                        # Need to split the line
                        p, w, is_bad = split_text(text, font, width - x, w, x > 0)
                        if p > 0:
                            segments.append(TextSegment(text[:p], x, y, w, font))
                            x += w
                            text = text[p:]
                            if is_bad:
                                bad_breaks += 1

                if text:
                    if x == 0 or y + line_spacing > height:
                        # We were unable to place it and had the whole space to place into
                        # Or the text cannot fit into the next line
                        raise ExtentTooSmallError()

                    # Handle any text fields on this line, expanding to fill line
                    if textfield_on_this_line is not None:
                        self.expand_field_size(segments, textfield_on_this_line, width - x)
                        textfield_on_this_line = None

                    # Start a new line, indenting as per the style
                    x = self.style.text.indent
                    y += line_spacing
                    text = text.lstrip()  # No leading spaces on new lines

                    breaks += 1

        # Handle any text fields on this line, expanding to fill line
        if textfield_on_this_line is not None:
            self.expand_field_size(segments, textfield_on_this_line, width - x)

        bottom = y + line_spacing
        right = max(s.x + s.width for s in segments)
        outer = Extent(right, bottom)

        # Only count excess for the last lines; not using 'right' which would be for all lines
        excess = self.extent.width - x

        # The good breaks equals all the breaks minus the bad ones
        quality = layout.quality.for_wrapping(self.run, excess, bad_breaks, breaks - bad_breaks)
        content = PlacedRunContent(segments, self.style, outer, quality)
        return content

    @staticmethod
    def expand_field_size(segments: list[Union[TextFieldSegment, CheckboxSegment, TextSegment]],
                          index: int, dx: float):
        segments[index].width += dx
        for s in segments[index + 1:]:
            s.x += dx


def tiny_run() -> Run:
    """ Makes a small run to be added to a block as a filler item """
    return Run([Element(' ')])
