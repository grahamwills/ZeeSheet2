from __future__ import annotations

import re
import warnings
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Iterable, Tuple, List

from reportlab.lib import fonts
from reportlab.pdfbase import pdfmetrics as metrics, pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFNameBytes

import common
from common.textual import NGram

LOGGER = common.configured_logger(__name__)

FONT_DIR = Path(__file__).parent / 'resources' / 'google-fonts'


def _key(txt: str) -> str:
    return txt.lower().replace('-', '').replace('_', '').replace(' ', '')


@dataclass
class FontFamily:
    name: str
    category: str
    faces: Dict[str, str]

    def ps_name(self, is_bold, is_italic) -> str:
        """ Returns the bane by which it is known internally (file name if not built in)"""
        if self.category == 'builtin':
            return fonts.tt2ps(self.name, 1 if is_bold else 0, 1 if is_italic else 0)

        faces = self.faces
        if len(faces) == 1:
            # Only one font, so that must be used for everything
            return list(faces.values())[0]

        # See which of these options is best

        if not is_bold and not is_italic:
            if 'Regular' in faces:
                return faces['Regular']
            elif 'Medium' in faces:
                return faces['Medium']
            else:
                raise KeyError('Cannot find a regular font!')

        possibles = list(faces.keys())
        bold_possibles = {p for p in possibles if 'Bold' in p or 'Black' in p}
        italic_possibles = {p for p in possibles if 'Italic' in p}
        if is_bold and is_italic:
            possibles = bold_possibles & italic_possibles
        elif is_bold:
            possibles = bold_possibles - italic_possibles
        elif is_italic:
            possibles = italic_possibles - bold_possibles
        if not possibles:
            warnings.warn(f"For font {self.name}, could not find face with bold={is_bold} and italic={is_italic}. "
                          f"Options are {sorted(faces.keys())}")
            return self.ps_name(False, False)
        # Shortest name that qualifies (note that 'bold' is thus preferred to 'black')
        mediums = {p for p in possibles if 'Medium' in p}
        if mediums:
            possibles = mediums

        return faces[min(possibles, key=lambda x: len(x))]

    def __lt__(self, other):
        """ Sort using names """
        return self.name < other.name

    def contains_standard_faces(self) -> bool:
        """ Returns true if it has regular, bold, italic, and boldItalic"""
        files = {self.ps_name(False, False), self.ps_name(False, True),
                 self.ps_name(True, False), self.ps_name(True, True)}
        return len(files) == 4

    def _register_font(self, zipfile_name, is_bold, is_italic) -> str:
        name = self.ps_name(is_bold, is_italic)
        if self.category == 'builtin':
            return name
        with zipfile.ZipFile(zipfile_name.absolute(), 'r') as z:
            file = z.open(name + '.ttf')
            font = TTFont(name, file)
            pdfmetrics.registerFont(font)
            return font.fontName

    def register_single_font(self, ps_name):
        if self.category == 'builtin':
            return
        try:
            pdfmetrics.getFont(ps_name)
            return ps_name
        except KeyError:
            zf = _zipfile(self.name)
            with zipfile.ZipFile(zf.absolute(), 'r') as z:
                file = z.open(ps_name + '.ttf')
                font = TTFont(ps_name, file)
                # My conversion of variable google fonts did not do a good job of setting thr face names in the files,
                # so they need to be fixed up here
                full_name = TTFNameBytes(ps_name.replace('-', ' ').encode('utf-8'))
                font.face.familyName = full_name
                font.face.styleName = full_name
                font.face.fullName = full_name
                font.face.name = full_name

                LOGGER.debug(f"Registering {ps_name}")
                pdfmetrics.registerFont(font)
                return font.fontName

    def register_with_reportlab(self):
        regular = self.register_single_font(self.ps_name(False, False))
        bold = self.register_single_font(self.ps_name (True, False))
        italic = self.register_single_font(self.ps_name ( False, True))
        boldItalic = self.register_single_font(self.ps_name (True, True))
        pdfmetrics.registerFontFamily(self.name, normal=regular, bold=bold, italic=italic, boldItalic=boldItalic)

    def face(self, bold: bool, italic: bool) -> str:
        if bold and italic:
            return 'BoldItalic'
        elif bold:
            return 'Bold'
        elif italic:
            return 'Italic'
        else:
            return 'Regular'

    def __str__(self):
        return self.name + '(' + self.category + ')'


@dataclass
class Font:
    library: Any
    name: str
    family: FontFamily
    face: str
    size: float
    ascent: float = None
    descent: float = None
    _font: pdfmetrics.Font = None

    def __post_init__(self):
        self._font = pdfmetrics.getFont(self.name)
        a, d = metrics.getAscentDescent(self.name, self.size)
        self.ascent = abs(a)
        self.descent = abs(d)

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

    def modify(self, bold: bool = None, italic: bool = None) -> Font:
        if bold is None and italic is None:
            return self
        return self.library.get_font(self.family.name, self.size,
                                     ('Bold' in self.face) if bold is None else bold,
                                     ('Italic' in self.face) if italic is None else italic)

    def __str__(self):
        return f"{self.name}:{self.size}({self.family}, {self.face})"

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
    def get_font(self, family_name: str, size: float, bold: bool = False, italic: bool = False) -> Font:
        """ Registers the font family if needed and returns the font requested"""

        LOGGER.debug(f"Looking for font: {family_name}")

        try:
            family = self[family_name]
            face = family.face(bold, italic)
            name = family.ps_name(bold, italic)
            family.register_with_reportlab()
        except KeyError:
            # The family name could actually be a name including fact like 'Generic-ExtraBold'; search for that
            name = family_name
            family, face = self._search_for_font_by_name(name)
            family.register_single_font(name)
            LOGGER.debug(f"Registering family: {name}")
            pdfmetrics.registerFontFamily(name, name, name, name, name)

        font = Font(self, name, family, face, size)
        LOGGER.debug(f"Created font: {font}")
        return font

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

    def _search_for_font_by_name(self, fontName) -> Tuple[FontFamily, str]:
        name_key = _key(fontName)
        for k, family in self.content.items():
            if name_key.startswith(k):
                face_key = name_key[len(k):]
                for face in family.faces.keys():
                    if _key(face) == face_key:
                        return family, face
        raise KeyError(fontName)


def _zipfile(name):
    """ Return the zipfile containing the info """
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
