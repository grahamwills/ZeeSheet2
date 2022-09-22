from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Iterable, Tuple, List

from reportlab.lib import fonts
from reportlab.pdfbase import pdfmetrics as metrics, pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from common.textual import NGram

FONT_DIR = Path(__file__).parent / 'resources' / 'google-fonts'


def _key(txt: str) -> str:
    return txt.lower().replace('-', '').replace('_', '').replace(' ', '')


@dataclass
class FontFamily:
    name: str
    category: str
    faces: Dict[str, str]

    def font_file(self, is_bold, is_italic) -> str:
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

    def __lt__(self, other):
        """ Sort using names """
        return self.name < other.name

    def contains_standard_faces(self) -> bool:
        """ Returns true if it has regular, bold, italic, and boldItalic"""
        files = {self.font_file(False, False), self.font_file(False, True),
                 self.font_file(True, False), self.font_file(True, True)}
        return len(files) == 4


@dataclass
class Font:
    library: Any
    name: str
    family: FontFamily
    face: str
    size: float
    ascent: float
    descent: float
    _font: pdfmetrics.Font = None

    def __post_init__(self):
        self._font = pdfmetrics.getFont(self.name)

    @lru_cache(maxsize=10000)
    def width(self, text: str) -> float:
        """Measures the width of the text"""
        return self._font.stringWidth(text, self.size)

    @property
    def line_spacing(self):
        """The distance between two lines"""
        return (self.ascent + self.descent) * 1.2

    @property
    def top_to_baseline(self):
        """ The distance from the notional top to the baseline for the font """
        # We split the leading half above the text and half below it
        leading = self.line_spacing - (self.ascent + self.descent)
        return self.ascent + leading / 2

    def change_face(self, bold: bool = None, italic: bool = None) -> Font:
        return self.library.get_font(self.family.name, self.size,
                                     'Bold' in self.face if bold is None else bold,
                                     'Italic' in self.face if italic is None else italic)

    def __hash__(self):
        return hash((self.name, self.size))


def read_font_info() -> List[FontFamily]:
    out = []
    with open(FONT_DIR / '_INDEX.txt') as f:
        for line in f.readlines():
            # Sample:     WindSong|handwriting|Medium:WindSong-Medium;Regular:WindSong-Regular
            name, cat, faces_all = tuple(line.strip().split('|'))
            faces = {}
            for part in faces_all.split(';'):
                a, b = tuple(part.split(':'))
                faces[a] = b
            out.append(FontFamily(name, cat, faces))
    return out


class FontLibrary():
    def __init__(self):
        families = read_font_info()
        self.content: Dict[str, FontFamily] = {_key(f.name): f for f in families}

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
        return self.content[_key(item)]

    @lru_cache
    def get_font(self, familyName: str, size: float, bold: bool = False, italic: bool = False) -> Font:
        """ Registers the font family if needed and returns the font requested"""

        try:
            # Family and types
            family = self[familyName]
            if family.category == 'builtin':
                name = fonts.tt2ps(family.name, 1 if bold else 0, 1 if italic else 0)
            else:
                name = family.font_file(bold, italic)

            if bold and italic:
                face = 'BoldItalic'
            elif bold:
                face = 'Bold'
            elif italic:
                face = 'Italic'
            else:
                face = 'Regular'
        except KeyError:
            name = None

        if not name:
            # Maybe it's an individual font name, not a family
            family, face = self._search_for_font_by_name(familyName)
            name = family.faces[face]

        try:
            a, d = metrics.getAscentDescent(name, size)
        except KeyError:
            zipfile_name = self._zipfile(name)
            with zipfile.ZipFile(zipfile_name.absolute(), 'r') as z:
                file = z.open(name + '.ttf')
                font = TTFont(name, file)
            pdfmetrics.registerFont(font)
            a, d = metrics.getAscentDescent(name, size)

        return Font(self, name, family, face, size, abs(a), abs(d))

    @staticmethod
    def _zipfile(name):
        s = name.lower()
        if re.match(r'Noto Sans ..-.*', name):
            stem = 'noto-sans-xx'
        elif re.match(r'Noto Serif ..-.*', name):
            stem = 'noto-serif-xx'
        elif s[0] == 's':
            stem = 'sa-se' if s[1] < 'h' else 'sh-sz'
        else:
            stem = s[0]
        return FONT_DIR / ('fonts-' + stem + '.zip')

    def families(self) -> Iterable[FontFamily]:
        return self.content.values()

    def similar_names(self, family_name: str) -> List[str]:
        N = 3
        target = NGram(family_name.lower(), N)

        def sim(f: FontFamily):
            other = NGram(f.name.lower(), N)
            return other.similarity(target), f.name

        similarity = [sim(f) for f in self.families()]
        a, b, c = tuple(sorted(similarity)[:-4:-1])
        # Look for a big difference and stop adding when we find it
        result = [a[1]]
        if a[0] - b[0] < 0.1:
            result.append(b[1])
            if b[0] - c[0] < 0.1:
                result.append(c[1])
        return result

    @lru_cache
    def _search_for_font_by_name(self, fontName) -> Tuple[FontFamily, str]:
        name_key = _key(fontName)
        for k, family in self.content.items():
            if name_key.startswith(k):
                face_key = name_key[len(k):]
                for face in family.faces.keys():
                    if _key(face) == face_key:
                        return family, face
        raise KeyError(fontName)
