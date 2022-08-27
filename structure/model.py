from __future__ import annotations

import itertools
import re
import reprlib
from collections import namedtuple
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import List, Optional, ClassVar, Tuple

import reportlab.lib.pagesizes

FormatPieces = namedtuple('FormatInfo', 'open close sep')
Problem  = namedtuple('Problem', 'lineNo is_error message')

@dataclass
class Element():
    value: str
    modifier: Optional[str] =  None

    def __post_init__(self):
        assert self.value, 'Element must be created with valid content'

    def structure_str(self, short: bool):
        if short:
            if self.modifier == 'checkbox':
                if self.value == 'X':
                    return '\u2612'
                else:
                    return '\u2610'
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
        if txt == '[ ]' or txt == '[O]':
            return cls(' ', 'checkbox')
        elif txt == '[X]':
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
            parts = re.split(r'(\[[ XO]])', text)
            return [cls._from_text(t) for t in parts if t]


# noinspection PyUnresolvedReferences
@dataclass
class StructureUnit:
    format_pieces: ClassVar[FormatPieces]

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
        if self._titled():
            self.title.tidy()
        for s in self.children:
            s.tidy()
        self.children = [s for s in self.children if s]

    def structure_str(self, short: bool):
        open, sep, close = self.format_pieces

        title = self.title.structure_str(short) + " ~ " if self._titled() and self.title else ''

        if short:
            content = str(len(self.children)) + " items"
        else:
            content = sep.join(s.structure_str(short) for s in self.children)

        return open + (title + content).strip() + close

@dataclass
class Run(StructureUnit):
    format_pieces: ClassVar[Tuple[str, str, str]] = ('', '', '')

    children: List[Element] = field(default_factory=list)

    def append(self, element: Element):
        self.children.append(element)

    def structure_str(self, short: bool):
        if len(self.children) == 1:
            return self.children[0].structure_str(short)
        else:
            return super().structure_str(short)

    def strip(self):
        """Remove heading and trailing whitespace if the edge elements are simple text"""
        if self.children:
            if not self.children[0].modifier:
                self.children[0].value = self.children[0].value.lstrip()
            if not self.children[-1].modifier:
                self.children[-1].value = self.children[-1].value.rstrip()

        # Remove empty items
        self.tidy()

    def as_str(self, width: int = 9e99, indent: int = 0) -> str:
        if not self.children:
            return ''

        splitter = re.compile(r'(\S+)')

        items = []
        for s in self.children:
            if s.modifier != 'literal':
                # Using explicit space to split keeps the whitespace around
                for w in splitter.split(s.to_rst()):
                    if w != '':
                        items.append(w)
            else:
                # Do not split up anything that is not simple text
                items.append(s.to_rst())

        results = []
        current_line_length = indent

        # Then try all the rest
        for this, next in zip(items, items[1:] + [' ']):
            if this == ' ':
                # a potential break point
                if current_line_length + 1 + len(next) > width:
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


    def __bool__(self):
        return bool(self.children)

    def tidy(self) -> None:
        pass


def split_run_into_cells(base: Run) -> List[Run]:
    current = Run()
    cells: List[Run] = [current]
    for element in base.children:
        if element.modifier or '|' not in element.value:
            # Does not contain a cell splitter
            current.append(element)
        else:
            items = element.value.split('|')
            if items[0]:
                # add the first one
                current.append(Element(items[0], element.modifier))
            for s in items[1:]:
                # For the next items, start a new cell first
                current = Run()
                cells.append(current)
                if s:
                    current.append(Element(s, element.modifier))
    return cells


@dataclass
class Item(StructureUnit):
    format_pieces: ClassVar[Tuple[str, str, str]] = ('[', ' \u2b29 ', ']')

    children: List[Run] = field(default_factory=lambda: [Run()])

    def append(self, run: Run):
        self.children.append(run)

    def as_str(self, width: int, indent: int = 0):
        assert len(self.children) == 1
        return self.children[0].as_str(width, indent=indent)

    def add_to_content(self, element: Element):
        self.children[-1].append(element)

    def tidy(self) -> None:
        super().tidy()

        # Now divide into cells
        divided = [split_run_into_cells(run) for run in self.children]
        self.children = list(itertools.chain(*divided))


@dataclass
class Block(StructureUnit):
    format_pieces: ClassVar[Tuple[str, str, str]] = ('\u276e', ' ', '\u276f')

    title: Run = field(default_factory=lambda: Run())
    children: List[Item] = field(default_factory=lambda: [Item()])


    def name(self):
        """ Descriptive name for debugging"""
        if self.title:
            return 'Block{' + reprlib.repr(self.title.as_str()) + ', ' + str(len(self.children)) + ' items}'
        else:
            return 'Block{' + str(len(self.children)) + ' items}'

    def column_count(self) ->int:
        """Maximum number of runs in each block item"""
        return max(len(item.children) for item in self.children) if self.children else 0

    def tidy(self) -> None:
        super().tidy()

        # If we have cells for the block, then the runs get stripped
        if self.column_count() > 1:
            for item in self:
                for run in item:
                    run.strip()




@dataclass
class Section(StructureUnit):
    format_pieces: ClassVar[Tuple[str, str, str]] = ('', ' ', '')

    title: Run = field(default_factory=lambda: Run())
    children: List[Block] = field(default_factory=lambda: [Block()])

    def name(self):
        """ Descriptive name for debugging"""
        if self.title:
            return 'Section{' + reprlib.repr(self.title.as_str()) + ', ' + str(len(self.children)) + ' items}'
        else:
            return 'Section{' + str(len(self.children)) + ' items}'

    def append(self, block: Block):
        self.children.append(block)


@dataclass
class Sheet(StructureUnit):
    format_pieces: ClassVar[Tuple[str, str, str]] = ('', ' --- ', '')

    children: List[Section] = field(default_factory=lambda: [Section()])
    issues: List[Problem] = field(default_factory=list)
    page_size: Tuple[int, int] = reportlab.lib.pagesizes.LETTER

    def append(self, section: Section):
        self.children.append(section)

    def describe_issues(self):
        return ' \u2022 '.join(s.message for s in self.issues)

