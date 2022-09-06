from __future__ import annotations

import re
from collections import namedtuple
from dataclasses import dataclass, field
from typing import List, Optional, ClassVar, Tuple, Dict

import reportlab.lib.pagesizes

from structure.style import Style

FormatPieces = namedtuple('FormatInfo', 'open close sep')
Problem = namedtuple('Problem', 'lineNo is_error message')


def checkbox_character(state) -> str:
    if state == 'X' or state is True:
        return '\u2612'
    else:
        return '\u2610'


@dataclass
class Element:
    value: str
    modifier: Optional[str] = None

    def __post_init__(self):
        assert self.value, 'Element must be created with valid content'

    def description(self, short: bool):
        if short:
            if self.modifier == 'checkbox':
                return checkbox_character(self.value)
            return self.value if len(self.value) <= 20 else self.value[:19] + '\u2026'
        elif self.modifier:
            return '\u00ab' + self.value + '\u22a3' + self.modifier[:3] + '\u00bb'
        else:
            return self.value

    def to_rst(self):
        if self.modifier == 'strong':
            return '**' + self.value + '**'
        elif self.modifier == 'emphasis':
            return '*' + self.value + '*'
        elif self.modifier == 'literal':
            return '``' + self.value + '``'
        elif self.modifier == 'checkbox':
            return '[' + self.value + ']'
        elif self.modifier is None:
            return self.value
        else:
            raise ValueError('Unknown Element modifier: ' + self.modifier)

    @classmethod
    def _from_text(cls, txt):
        if txt == '[ ]' or txt == '[O]' or txt == '[o]':
            return cls(' ', 'checkbox')
        elif txt == '[X]' or txt == '[x]':
            return cls('X', 'checkbox')
        else:
            return cls(txt, None)

    @classmethod
    def text_to_elements(cls, text: str, modifier: Optional[str]) -> List[Element]:
        if modifier:
            # Keep it as it is
            return [cls(text, modifier)]
        else:
            # Split up to define checkboxes and other special items
            parts = re.split(r'(\[[ XOxo]])', text)
            return [cls._from_text(t) for t in parts if t]


# noinspection PyUnresolvedReferences,PyAttributeOutsideInit
@dataclass
class StructureUnit:
    FMT: ClassVar[FormatPieces]

    def __str__(self):
        return self.__class__.__name__

    def __len__(self):
        return len(self.children)

    def __getitem__(self, item):
        return self.children[item]

    def _titled(self):
        return hasattr(self, 'title')

    def __bool__(self) -> bool:
        return bool(self.children) or (self._titled() and bool(self.title))

    def tidy(self) -> None:
        raise NotImplementedError('Must be implemented by descendents')

    def _tidy_title(self):
        self.title.tidy()

    def _tidy_children(self, keep_empty: bool = False):
        """ Tidy children, and optionally throw away children with no centent"""
        for s in self.children:
            s.tidy()
        if not keep_empty:
            self.children = [s for s in self.children if s]

    def description(self, short: bool):
        start, sep, end = self.FMT

        title = self.title.description(short) + " ~ " if self._titled() and self.title else ''

        if short:
            content = str(len(self.children)) + " items"
        else:
            content = sep.join(s.description(short) for s in self.children)

        return start + (title + content).strip() + end


@dataclass
class Run(StructureUnit):
    FMT = FormatPieces('', '', '')
    children: List[Element] = field(default_factory=list)

    def append(self, element: Element):
        self.children.append(element)

    def description(self, short: bool):
        if len(self.children) == 1:
            return self.children[0].description(short)
        else:
            return super().description(short)

    def to_rst(self, width: int = 9e99, indent: int = 0) -> str:
        if not self.children:
            return ''

        # Split plain text (no modifier elements) into words and create a list of all unsplittable units
        splitter = re.compile(r'(\S+)')
        atoms = []
        for s in self.children:
            if s.modifier == 'literal':
                # Do not split literals
                atoms.append(s.to_rst())
            else:
                # Using explicit space to split keeps the whitespace around
                for w in splitter.split(s.to_rst()):
                    if w != '':
                        atoms.append(w)

        results = []
        current_line_length = indent
        for this, after in zip(atoms, atoms[1:] + [' ']):
            if this == ' ':
                # a potential break point
                if current_line_length + 1 + len(after) > width:
                    results.append('\n' + ' ' * indent)
                    current_line_length = indent
                else:
                    results.append(' ')
                    current_line_length += 1
            else:
                # Just add the item
                results.append(this)
                current_line_length += len(this)

        return ''.join(results)

    def tidy(self) -> None:
        # We do not need to tidy runs
        pass


@dataclass
class Item(StructureUnit):
    FMT = FormatPieces('[', ' \u2b29 ', ']')

    children: List[Run] = field(default_factory=lambda: [Run()])

    def as_str(self, width: int, indent: int = 0):
        assert len(self.children) == 1
        return self.children[0].to_rst(width, indent=indent)

    def add_to_content(self, element: Element):
        self.children[-1].append(element)

    def _split_run_into_cells(self, base: Run):
        self.children.append(Run())
        for element in base.children:
            if element.modifier or '|' not in element.value:
                # Does not contain a cell splitter
                self.add_to_content(element)
            else:
                items = element.value.split('|')
                if items[0]:
                    # add the first one
                    self.add_to_content(Element(items[0], element.modifier))
                for s in items[1:]:
                    # For the next items, start a new cell first
                    self.children.append(Run())
                    if s:
                        self.add_to_content(Element(s, element.modifier))

    def tidy(self) -> None:
        # replace children with a new list, breaking runs into cells to do so

        old = self.children
        self.children = []
        for run in old:
            if run:
                self._split_run_into_cells(run)

        self._tidy_children(keep_empty=True)


@dataclass
class Block(StructureUnit):
    FMT = FormatPieces('\u276e', ' ', '\u276f')
    title: Run = field(default_factory=lambda: Run())
    children: List[Item] = field(default_factory=lambda: [Item()])

    def column_count(self) -> int:
        """Maximum number of runs in each block item"""
        return max(len(item.children) for item in self.children) if self.children else 0

    def tidy(self) -> None:
        self._tidy_title()
        self._tidy_children()


@dataclass
class Section(StructureUnit):
    FMT = FormatPieces('', ' ', '')
    title: Run = field(default_factory=lambda: Run())
    children: List[Block] = field(default_factory=lambda: [Block()])

    def tidy(self) -> None:
        self._tidy_title()
        self._tidy_children()


@dataclass
class Sheet(StructureUnit):
    FMT = FormatPieces('', ' --- ', '')
    children: List[Section] = field(default_factory=lambda: [Section()])
    styles: Dict[str, Style] = field(default_factory=lambda: {})
    problems: List[Problem] = field(default_factory=list)
    page_size: Tuple[int, int] = reportlab.lib.pagesizes.LETTER

    def describe_issues(self):
        return ' \u2022 '.join(s.message for s in self.problems)

    def tidy(self) -> None:
        self._tidy_children()
