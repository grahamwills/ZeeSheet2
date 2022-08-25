import reprlib
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import List, Tuple

from reportlab.lib import fonts
from reportlab.pdfbase import pdfmetrics as metrics
from reportlab.pdfgen import canvas

from common.geom import Rect, Point
from common.logging import configured_logger

LOGGER = configured_logger(__name__)


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


class PDF(canvas.Canvas):

    def __init__(self, pagesize: Tuple[int, int]) -> None:
        self.buffer = BytesIO()
        super().__init__(self.buffer, pagesize=pagesize, bottomup=0)
        self.setLineJoin(1)
        self.setLineCap(1)
        self.font = FontInfo("Helvetica", 14, False, False)

    def draw_rect(self, r: Rect, method: DrawMethod):
        self.rect(r.left, r.top, r.width, r.height,
                  fill=(method != DrawMethod.DRAW), stroke=(method != DrawMethod.FILL))

    def draw_text(self, segments: List[TextSegment]):
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
            text.textOut(segment.text)
        self.drawText(text)

    def output(self) -> bytes:
        self.save()
        bytes = self.buffer.getvalue()
        self.buffer.close()
        return bytes
