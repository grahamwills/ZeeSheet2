from __future__ import annotations

import re
import warnings
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Iterable, Tuple, List

from reportlab.graphics.charts import textlabels
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics as metrics, pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFNameBytes

import common
from common import Rect
from common.textual import NGram
from structure import TextStyle

LOGGER = common.configured_logger(__name__)

FONT_DIR = Path(__file__).parent / 'resources' / 'google-fonts'


def _key(txt: str) -> str:
    return txt.lower().replace('-', '').replace('_', '').replace(' ', '')


@dataclass
class FontFamily:
    name: str
    category: str
    faces: Dict[str, str]

    def __lt__(self, other):
        """ Sort using names """
        return self.name < other.name

    def __str__(self):
        return self.name + '(' + self.category + ')'

    def match_face_name(self, name: str) -> str:
        """ Find the face with the closest matching name"""
        if name in self.faces:
            return name

        # Caseless match
        key = _key(name)
        for a in self.faces.keys():
            if key == _key(a):
                return a

        if key == 'regular':
            if len(self.faces) == 1:
                return tuple(self.faces.keys())[0]
            if 'Medium' in self.faces:
                return 'Medium'
            if 'Light' in self.faces:
                return 'Light'
            else:
                raise RuntimeError(f"Family '{self.name}' did not contain a regular font")
        if key == 'bold':
            if 'Black' in self.faces:
                return 'Black'
        if key == 'italic':
            if 'MediumItalic' in self.faces:
                return 'MediumItalic'

        warnings.warn(f"Face '{name}' is not defined for font family {self.name}. "
                      f"Defined faces are: {', '.join(sorted(self.faces.keys()))}. Using default face instead.")
        return self.match_face_name('regular')

    def internal_font_name(self, face: str) -> str:
        return self.faces[face]

    def contains_standard_faces(self):
        return 'BoldItalic' in self.faces \
               and ('Italic' in self.faces or 'MediumItalic' in self.faces) \
               and ('Bold' in self.faces or 'Black' in self.faces) \
               and ('Regular' in self.faces or 'Medium' in self.faces)


@dataclass
class Font:
    library: Any
    name: str
    family: FontFamily
    face: str
    size: float
    ascent: float = None
    descent: float = None
    line_spacing: float = None
    _font: pdfmetrics.Font = None

    def __post_init__(self):
        self._font = pdfmetrics.getFont(self.name)
        a, d = metrics.getAscentDescent(self.name, self.size)
        self.ascent = abs(a)
        self.descent = abs(d)

        # Built-in fonts seem a bit tighter
        if self.family.category == 'builtin':
            self.line_spacing = (self.ascent + self.descent) * 1.20
        else:
            self.line_spacing = (self.ascent + self.descent) * 1.1

    @lru_cache(maxsize=10000)
    def width(self, text: str) -> float:
        """Measures the width of the text"""
        return self._font.stringWidth(text, self.size)

    def bbox(self, t: str) -> Rect:
        """
            Measures the bounding box of the drawn results.

            Rect returned is relative to the baseline, and is inverted, so
            bottom is the max height above the baseline and top is the max height below the baseline
        """

        try:
            # noinspection PyProtectedMember
            r = textlabels._text2Path(t, fontName=self.name, fontSize=self.size).getBounds()
            return Rect(r[0], r[2], r[1], r[3])
        except ValueError:
            # Text did not have a path (probably all spaces)
            return Rect(0,0,0,0)

    @property
    def top_to_baseline(self):
        """ The distance from the notional top to the baseline for the font """
        # We split the leading half above the text and half below it
        leading = self.line_spacing - (self.ascent + self.descent)
        return self.ascent + leading / 2

    def modify(self, modifier: str):
        if modifier:
            return self.library.modify(self, modifier)
        else:
            return self

    def __str__(self):
        return f"{self.name}:{self.size}({self.family}, {self.face})"

    def __hash__(self):
        # A slight speed improvement over the default
        return hash(self.name) + 13 * int(100 * self.size)


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


class FontLibrary:
    _families: Dict[str, FontFamily]

    def __init__(self):
        families = read_font_info()
        self._families: Dict[str, FontFamily] = {_key(f.name): f for f in families}

        # Add built-in fonts
        self._families['courier'] = FontFamily('Courier', 'builtin',
                                               {'Regular': 'Courier', 'Bold': 'Courier-Bold',
                                                'Italic': 'Courier-Oblique',
                                                'BoldItalic': 'Courier-BoldOblique'})
        self._families['helvetica'] = FontFamily('Helvetica', 'builtin',
                                                 {'Regular': 'Helvetica', 'Bold': 'Helvetica-Bold',
                                                  'Italic': 'Helvetica-Oblique',
                                                  'BoldItalic': 'Helvetica-BoldOblique'})
        self._families['times'] = FontFamily('Times', 'builtin',
                                             {'Regular': 'Times-Roman', 'Bold': 'Times-Bold',
                                              'Italic': 'Times-Italic', 'BoldItalic': 'Times-BoldItalic'})
        self._families['symbol'] = FontFamily('Symbol', 'builtin', {'Regular': 'Symbol'})
        self._families['zapfdingbats'] = FontFamily('ZapfDingbats', 'builtin', {'Regular': 'ZapfDingbats'})

    def __len__(self):
        return len(self._families)

    def __getitem__(self, item: str):
        return self._families[_key(item)]

    @lru_cache
    def get_font(self, family_name: str, size: float, face_name: str = 'regular') -> Font:
        """
            Returns the requested font

            :param family_name: The name of the family, e.g 'Montserrat'
            :param size: The font size
            :param face_name: Face variant of the font, e.g. regular, bold, thin, italic, etc.

            If the font has not been registered, then it is automatically registered
        """

        family = self.family_named(family_name)
        face = family.match_face_name(face_name)
        name = family.internal_font_name(face)

        register_single_font(family, name)

        font = Font(self, name, family, face, size)
        LOGGER.debug(f"Created font: {font}")
        return font

    def family_named(self, name: str) -> FontFamily:
        key = _key(name)
        try:
            return self[key]
        except KeyError:
            similar = self.similar_names(key)
            if len(similar) == 1:
                warnings.warn(f"Unknown font family '{key}'. "
                              f"Using similarly-named family '{similar[0]}' instead")
            else:
                ss = ', '.join("'" + s + "'" for s in similar)
                warnings.warn(f"Unknown font family '{key}'. Did you mean one of {ss}? "
                              f"Using '{similar[0]}' instead")
            return self[similar[0]]

    def families(self) -> Iterable[FontFamily]:
        return self._families.values()

    def modify(self, font: Font, modifier: str) -> Font:
        new_face = None
        if modifier == 'strong':
            if font.face == 'Regular' or font.face == 'Medium':
                new_face = 'Bold'
            if font.face == 'Italic':
                new_face = 'BoldItalic'
            if font.face == 'Bold':
                new_face = 'ExtraBold'
        if modifier == 'emphasis':
            if font.face == 'Regular' or font.face == 'Medium':
                new_face = 'Italic'
            if font.face == 'Bold':
                new_face = 'BoldItalic'
        if not new_face:
            warnings.warn(f"Cannot modify {font.face} for '{modifier}'. Ignoring modifier")
            return font
        else:
            return self.get_font(font.family.name, font.size, new_face)

    def similar_names(self, family_name: str) -> List[str]:
        n = 3
        target = NGram(family_name.lower(), n)

        def sim(f: FontFamily):
            other = NGram(f.name.lower(), n)
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

    def _search_for_font_by_name(self, font_name) -> Tuple[FontFamily, str]:
        name_key = _key(font_name)
        for k, family in self._families.items():
            if name_key.startswith(k):
                face_key = name_key[len(k):]
                for face in family.faces.keys():
                    if _key(face) == face_key:
                        return family, face
        raise KeyError(font_name)


class TextFontModifier:
    def modify_font(self, font: Font, modifier: str) -> Font:
        raise NotImplementedError()

    def modify_color(self, c: Color, modifier: str) -> Color:
        raise NotImplementedError()


def register_single_font(family: FontFamily, full_name: str):
    if family.category == 'builtin':
        return
    try:
        pdfmetrics.getFont(full_name)
    except KeyError:
        zf = _zipfile(family.name)
        with zipfile.ZipFile(zf.absolute(), 'r') as z:
            file = z.open(full_name + '.ttf')
            font = TTFont(full_name, file)
            # My conversion of variable google fonts did not do a good job of setting thr face names in the files,
            # so they need to be fixed up here
            full_name = TTFNameBytes(full_name.replace('-', ' ').encode('utf-8'))
            font.face.familyName = full_name
            font.face.styleName = full_name
            font.face.fullName = full_name
            font.face.name = full_name

            LOGGER.debug(f"Registering {full_name}")
            pdfmetrics.registerFont(font)
            return font.fontName


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
