from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any

from reportlab.lib import fonts
from reportlab.pdfbase import pdfmetrics as metrics, pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = Path(__file__).parent / 'resources' / 'google-fonts'


@dataclass
class FontFamily:
    name: str
    category: str
    faces: Dict[str, str]

    def font_file(self, is_bold, is_italic):
        faces = self.faces
        if len(faces) == 1:
            # Only one font, so that must be used for everything
            return list(faces.values())[0]

        if not is_bold and not is_italic:
            if 'Regular' in faces:
                return faces['Regular']
            elif 'Medium' in faces:
                return faces['Medium']
            else:
                raise KeyError('Cannot find a regular font!')

        possibles = list(faces.keys())
        if is_bold:
            possibles = [p for p in possibles if 'Bold' in p or 'Black' in p]
        if is_italic:
            possibles = [p for p in possibles if 'Italic' in p]
        if not possibles:
            return self.font_file(False, False)
        # Shortest name that qualifies (note that 'bold' is thus preferred to 'black')
        return faces[min(possibles, key=lambda x: len(x))]


@dataclass
class Font:
    library: Any
    name: str
    family: FontFamily
    face: str
    size: float
    ascent: float
    descent: float

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

    def modify(self, bold: bool = None, italic: bool = None) -> Font:
        return self.library.get_font(self.family.name, self.size,
                                     'Bold' in self.face if bold is None else bold,
                                     'Italic' in self.face if italic is None else italic)


def read_font_info():
    out = {}
    with open(FONT_DIR / '_INDEX.txt') as f:
        for line in f.readlines():
            # Sample:     WindSong|handwriting|Medium:WindSong-Medium;Regular:WindSong-Regular
            name, cat, faces_all = tuple(line.strip().split('|'))
            faces = {}
            for part in faces_all.split(';'):
                a, b = tuple(part.split(':'))
                faces[a] = b
            out[name.lower().replace(' ', '')] = FontFamily(name, cat, faces)
    return out


class FontLibrary():
    def __init__(self):
        self.content: Dict[str, FontFamily] = read_font_info()

        # Add built-in fonts
        self.content['courier'] = FontFamily('Courier', 'builtin',
                                             {'Regular': '', 'Bold': 'Bold', 'Italic': 'Oblique',
                                              'BoldItalic': 'BoldOblique'})
        self.content['helvetica'] = FontFamily('Helvetica', 'builtin',
                                               {'Regular': '', 'Bold': 'Bold', 'Italic': 'Oblique',
                                                'BoldItalic': 'BoldOblique'})
        self.content['times'] = FontFamily('Times', 'builtin', {'Regular': '', 'Bold': 'Bold', 'Italic': 'Italic',
                                                                   'BoldItalic': 'BoldItalic'})
        self.content['symbol'] = FontFamily('Symbol', 'builtin', {'Regular': ''})
        self.content['zapfdingbats'] = FontFamily('ZapfDingbats', 'builtin', {'Regular': ''})

    def __len__(self):
        return len(self.content)

    def __getitem__(self, item: str):
        key = item.lower().replace(' ', '')
        return self.content[key]

    def font_file(self, family: str, is_bold: bool = False, is_italic: bool = False):
        """ Returns Just the name of the font"""
        return self[family].font_file(is_bold, is_italic)

    @lru_cache
    def get_font(self, family: str, size: float, bold: bool = False, italic: bool = False) -> Font:
        """ Registers the font family if needed and returns the font requested"""

        # Check for built-in font
        name  = None
        try:
            if self[family].category == 'builtin':
                name = fonts.tt2ps(family, 1 if bold else 0, 1 if italic else 0)
        except KeyError:
            pass
        if not name:
            # Not a built-in font
            name = self.font_file(family, is_bold=bold, is_italic=italic)

        family = self[family]
        if bold and italic:
            face = 'BoldItalic'
        elif bold:
            face = 'Bold'
        elif italic:
            face = 'Italic'
        else:
            face = 'Regular'

        try:
            a, d = metrics.getAscentDescent(name, size)
        except KeyError:
            loc = FONT_DIR / (name + '.ttf')
            font = TTFont(name, loc.absolute())
            pdfmetrics.registerFont(font)
            a, d = metrics.getAscentDescent(name, size)

        return Font(self, name, family, face, size, abs(a), abs(d))