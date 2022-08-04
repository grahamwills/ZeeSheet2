import re
from dataclasses import dataclass, field
from typing import List, NamedTuple, Optional

ERROR_DIRECTIVE = '.. ERROR::'
WARNING_DIRECTIVE = '.. WARNING::'


@dataclass
class Element:
    value: str
    modifier: Optional[str]

    def __str__(self):
        return f"Element[{self.value}]"

    def debug_str(self):
        if self.modifier:
            return self.value + '\u22a3' + self.modifier[:3]
        else:
            return self.value

    def as_str(self):
        if self.modifier == 'strong':
            return '**' + self.value + '**'
        elif self.modifier == 'emphasis':
            return '*' + self.value + '*'
        elif self.modifier is None:
            return self.value
        else:
            raise ValueError('Unknown Element modifier: ' + self.modifier)

    @classmethod
    def from_text(cls, text: str, modifier: Optional[str]):
        return cls(text, modifier)

    def is_plain_text(self):
        return self.modifier is None


@dataclass
class Run:
    elements: List[Element] = field(default_factory=list)

    def append(self, element: Element):
        self.elements.append(element)

    def __str__(self):
        n = len(self)
        return f"Run[{n} Elements]"

    def __len__(self):
        return len(self.elements)

    def __getitem__(self, item):
        return self.elements[item]

    def debug_str(self):
        return '\u2016'.join(s.debug_str() for s in self.elements)

    def as_str(self, width: int, indent: int = 0) -> str:
        if not self.elements:
            return ''

        splitter = re.compile(r'(\S+)')

        items = []
        for s in self.elements:
            if s.is_plain_text():
                # Using explicit space to split keeps the whitespace around
                for w in splitter.split(s.as_str()):
                    if w != '':
                        items.append(w)
            else:
                # Do not split up anything that is not simple text
                items.append(s.as_str())

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

    def empty(self) -> bool:
        return len(self.elements) == 0

    def tidy(self) -> None:
        # Nothing needed
        pass


@dataclass
class Block:
    title: Run = field(default_factory=lambda: Run())
    items: List[Run] = field(default_factory=lambda: [Run()])

    def append(self, run: Run):
        self.items.append(run)

    def __str__(self):
        n = len(self)
        return f"Block[{n} Runs]"

    def __len__(self):
        return len(self.items)

    def __getitem__(self, item):
        return self.items[item]

    def debug_str(self):
        pre = f"[{self.title.debug_str()}: " if self.title else '[ '
        return pre + ' \u2022 '.join(s.debug_str() for s in self.items) + ']'

    def add_lines_to(self, lines, width: int):
        if self.title:
            lines.append(self.title.as_str(width))
            lines.append('')
        if self.items:
            for item in self.items:
                lines.append('- ' + item.as_str(width, indent=2))
            lines.append('')

    def empty(self):
        return self.title.empty() and len(self.items) == 1 and self.items[0].empty()

    def add_to_title(self, element: Element):
        self.title.append(element)

    def add_to_content(self, element: Element):
        self.items[-1].append(element)

    def tidy(self) -> None:
        self.title.tidy()
        for s in self.items:
            s.tidy()
        if self.items[-1].empty():
            del self.items[-1]


@dataclass
class Section:
    title: Run = field(default_factory=lambda: Run())
    blocks: List[Block] = field(default_factory=lambda: [Block()])

    def append(self, block: Block):
        self.blocks.append(block)

    def __str__(self):
        n = len(self)
        return f"Section[{n} Blocks]"

    def __len__(self):
        return len(self.blocks)

    def __getitem__(self, item):
        return self.blocks[item]

    def debug_str(self):
        pre = f"<{self.title.debug_str()}: " if self.title else '<'
        return pre + ' '.join(s.debug_str() for s in self.blocks) + '>'

    def add_lines_to(self, lines, width: int):
        if self.title:
            # Since the title has to be underlined, we cannot wrap it
            title = self.title.as_str(10000)
            lines.append(title)
            lines.append('-' * len(title))
            lines.append('')
        for b in self.blocks:
            b.add_lines_to(lines, width)
        lines.append('')

    def add_to_title(self, element: Element):
        self.title.append(element)

    def empty(self):
        return self.title.empty() and len(self.blocks) == 1 and self.blocks[0].empty()

    def tidy(self) -> None:
        self.title.tidy()
        for s in self.blocks:
            s.tidy()
        if self.blocks[-1].empty():
            del self.blocks[-1]


class Issue(NamedTuple):
    lineNo: Optional[int]
    is_error: bool
    message: str

    def as_text(self) -> str:
        if self.lineNo:
            return f"[{self.lineNo:3}] {self.message}"
        else:
            return self.message


@dataclass
class Sheet:
    sections: List[Section] = field(default_factory=lambda: [Section()])
    issues: List[Issue] = field(default_factory=list)

    def append(self, section: Section):
        self.sections.append(section)

    def __str__(self):
        n = len(self)
        return f"Sheet[{n} Sections]"

    def __len__(self):
        return len(self.sections)

    def __getitem__(self, item):
        return self.sections[item]

    def structure_str(self):
        return ' '.join(s.debug_str() for s in self.sections)

    def combined_issues(self):
        return ' \u2022 '.join(s.message for s in self.issues)

    def to_text(self, width: int = 100) -> str:
        lines = []

        errors = [i for i in self.issues if i.is_error]
        warnings = [i for i in self.issues if not i.is_error]

        if errors:
            lines.append(ERROR_DIRECTIVE)
            for issue in errors:
                lines.append('   ' + issue.as_text())
            lines.append('')
        if warnings:
            lines.append(WARNING_DIRECTIVE)
            for issue in warnings:
                lines.append('   ' + issue.as_text())
            lines.append('')

        # Add lines for each section
        for s in self.sections:
            s.add_lines_to(lines, width)

        # Remove trailing section definition and blank lines
        while lines and lines[-1] == '':
            lines = lines[:-1]
        return '\n'.join(lines)

    def tidy(self) -> None:
        for s in self.sections:
            s.tidy()
        if self.sections[-1].empty():
            del self.sections[-1]
