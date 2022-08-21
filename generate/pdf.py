import os
from dataclasses import dataclass
from io import BytesIO
from typing import NamedTuple, List, Tuple

from django.contrib.auth.models import User
from django.contrib.sessions.backends import file
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files import File
from reportlab.pdfbase import pdfmetrics as metrics
from reportlab.pdfgen import canvas

from common.geom import Rect, Point
from common.logging import configured_logger
from rst.structure import Sheet

LOGGER = configured_logger(__name__)


class DrawMethod(NamedTuple):
    fill: bool
    stroke: bool


DrawMethod.FILL = DrawMethod(True, False)
DrawMethod.STROKE = DrawMethod(False, True)
DrawMethod.BOTH = DrawMethod(True, True)


@dataclass
class TextSegment:
    text: str
    offset: Point


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
        self.line_spacing = (self.ascent + self.descent) * 1.2

    def width(self, text: str) -> float:
        return metrics.stringWidth(text, self.name, self.size)


class PDF(canvas.Canvas):

    def __init__(self, pagesize: Tuple[int, int]) -> None:
        self.buffer = BytesIO()
        super().__init__(self.buffer, pagesize=pagesize, bottomup=0)
        self.setLineJoin(1)
        self.setLineCap(1)
        self.font = FontInfo("Helvetica", 14)

    def draw_rect(self, r: Rect, method: DrawMethod):
        self.rect(r.left, r.top, r.width, r.height, fill=method.fill, stroke=method.stroke)

    def draw_text(self, segments: List[TextSegment], location: Point):
        textobject = self.beginText()
        textobject.setFont(self.font.name, self.font.size)
        textobject.setTextOrigin(location.x, location.y)
        for segment in segments:
            if segment.offset:
                textobject.moveCursor(segment.offset.x, segment.offset.y)
            textobject.textOut(segment.text)
        self.drawText(textobject)

    def output(self) -> bytes:
        self.save()
        bytes = self.buffer.getvalue()
        self.buffer.close()
        return bytes


def make_pdf(sheet:Sheet, owner:User) -> str:
    file_name = f"sheets/{owner.username}-sheet.pdf"

    pdf = PDF(sheet.page_size)
    pdf.drawString(100, 100, "Hello World")
    bytes = pdf.output()
    path = default_storage.save(file_name, ContentFile(bytes))
    return path[7:] # remove the 'sheets/'



