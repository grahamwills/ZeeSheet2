import reprlib
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import List, Tuple

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
class TextSegment:
    text: str
    offset: Point

    def __str__(self):
        return reprlib.repr(self.text) + '@' + str(self.offset)


class FontInfo:
    name: str
    size: float
    ascent: float
    descent: float
    line_spacing: float

    def __init__(self, name: str, size: float):
        self.name = name
        self.size = size
        a, d = metrics.getAscentDescent(name, size)
        self.ascent = abs(a)
        self.descent = abs(d)

    def width(self, text: str) -> float:
        """Measures the width of the text"""
        return metrics.stringWidth(text, self.name, self.size)

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


class PDF(canvas.Canvas):

    def __init__(self, pagesize: Tuple[int, int]) -> None:
        self.buffer = BytesIO()
        super().__init__(self.buffer, pagesize=pagesize, bottomup=0)
        self.setLineJoin(1)
        self.setLineCap(1)
        self.font = FontInfo("Helvetica", 14)

    def draw_rect(self, r: Rect, method: DrawMethod):
        self.rect(r.left, r.top, r.width, r.height,
                  fill=(method != DrawMethod.DRAW), stroke=(method != DrawMethod.FILL))

    def draw_text(self, segments: List[TextSegment]):
        ss = ', '.join([str(s) for s in segments])
        LOGGER.debug(f"Drawing segments {ss}")
        textobject = self.beginText()
        textobject.setFont(self.font.name, self.font.size)
        textobject.setTextOrigin(0, self.font.top_to_baseline)
        textobject.setLeading(self.font.line_spacing)
        current_y = 0
        for segment in segments:
            if segment.offset:
                # The 'x' is absolute, but the 'y' is relative to the last move
                textobject.moveCursor(segment.offset.x, segment.offset.y - current_y)
                current_y = segment.offset.y
            textobject.textOut(segment.text)
        self.drawText(textobject)

    def output(self) -> bytes:
        self.save()
        bytes = self.buffer.getvalue()
        self.buffer.close()
        return bytes
