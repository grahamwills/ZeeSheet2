import reprlib
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import List, Tuple, Union, Dict

from reportlab.lib import fonts, colors
from reportlab.pdfbase import pdfmetrics as metrics
from reportlab.pdfgen import canvas

from common import Rect, Point
from common import configured_logger
from structure.model import checkbox_character
from structure.style import Style

LOGGER = configured_logger(__name__)

_WHITE = colors.Color(1, 1, 1)


class DrawMethod(Enum):
    FILL = 1
    DRAW = 2
    BOTH = 3


@dataclass
class FontInfo:
    name: str
    size: float
    bold: bool
    italic: bool

    def __post_init__(self):
        self.ps_name = fonts.tt2ps(self.name, 1 if self.bold else 0, 1 if self.italic else 0)
        a, d = metrics.getAscentDescent(self.ps_name, self.size)
        self.ascent = abs(a)
        self.descent = abs(d)

    def width(self, text: str) -> float:
        """Measures the width of the text"""
        return metrics.stringWidth(text, self.ps_name, self.size)

    @property
    def line_spacing(self):
        """The distance between two lines"""
        return (self.ascent + self.descent) * 1.2

    @property
    def top_to_baseline(self):
        """The distance from the notional top to the baseline for the font"""
        # We split the leading half above the text and half below it
        leading = self.line_spacing - (self.ascent + self.descent)
        return self.ascent + leading / 2

    def modify(self, bold: bool, italic: bool):
        return FontInfo(self.name, self.size, bold or self.bold, italic or self.italic)


@dataclass
class TextSegment:
    text: str
    offset: Point
    font: FontInfo

    def __str__(self):
        return reprlib.repr(self.text) + '@' + str(self.offset)


@dataclass
class CheckboxSegment:
    state: bool
    offset: Point
    font: FontInfo

    def __str__(self):
        return checkbox_character(self.state) + '@' + str(self.offset)


class PDF(canvas.Canvas):

    def __init__(self,
                 pagesize: Tuple[int, int],
                 styles:Dict[str, Style]= None,
                 debug: bool = False) -> None:
        self.buffer = BytesIO()
        super().__init__(self.buffer, pagesize=pagesize, bottomup=0)
        self.setLineJoin(1)
        self.setLineCap(1)
        self.font = FontInfo("Helvetica", 14, False, False)
        self.styles = styles
        self.debug = debug

        # Keep an index to give unique names to form items
        self._name_index = 0

    def draw_rect(self, r: Rect, method: DrawMethod):
        self.rect(r.left, r.top, r.width, r.height,
                  fill=(method != DrawMethod.DRAW), stroke=(method != DrawMethod.FILL))

    def _draw_checkbox(self, rx, ry, font: FontInfo, state):
        size = font.ascent + font.descent

        x, y = self.absolutePosition(rx, ry + size)
        y = self._pagesize[1] - y
        self._name_index += 1
        name = 'f' + str(self._name_index)
        LOGGER.debug("Adding checkbox name='%s' with state=%s ", name, state)
        self.acroForm.checkbox(name=name, x=x, y=y, size=size,
                               fillColor=_WHITE,
                               buttonStyle='cross', borderWidth=0.5, checked=state)

    def draw_text(self, segments: List[Union[TextSegment, CheckboxSegment]]):
        ss = ', '.join([str(s) for s in segments])
        LOGGER.debug(f"Drawing segments {ss}")

        text = self.beginText()
        text.setTextOrigin(0, self.font.top_to_baseline)
        off = Point(0, 0)
        current_font = None
        for segment in segments:
            if segment.font != current_font:
                current_font = segment.font
                text.setFont(current_font.ps_name, current_font.size, current_font.line_spacing)
            if segment.offset:
                text.moveCursor(segment.offset.x - off.x, segment.offset.y - off.y)
                off = segment.offset
            if hasattr(segment, 'text'):
                # It is text, so just output it
                text.textOut(segment.text)
            else:
                self._draw_checkbox(segment.offset.x, segment.offset.y, current_font, segment.state)

        self.drawText(text)

    def output(self) -> bytes:
        self.save()
        bytes = self.buffer.getvalue()
        self.buffer.close()
        return bytes
