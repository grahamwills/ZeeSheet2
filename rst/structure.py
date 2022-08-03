from dataclasses import dataclass, field
from typing import List, NamedTuple, Optional

ERROR_DIRECTIVE = '.. ERROR::'
WARNING_DIRECTIVE = '.. WARNING::'


@dataclass
class Element:
    value: str

    def __str__(self):
        return f"Element[{self.value}]"

    def structure_str(self):
        return self.value

    def as_str(self):
        return self.value


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

    def structure_str(self):
        return ' | '.join(s.structure_str() for s in self.elements)

    def as_str(self) -> str:
        return ''.join(s.as_str() for s in self.elements)


@dataclass
class Block:
    title: str
    items: List[Run] = field(default_factory=list)

    def append(self, run: Run):
        self.items.append(run)

    def __str__(self):
        n = len(self)
        return f"Block[{n} Runs]"

    def __len__(self):
        return len(self.items)

    def __getitem__(self, item):
        return self.items[item]

    def structure_str(self):
        pre = f"[{self.title}: " if self.title else '[ '
        return pre + ' \u2022 '.join(s.structure_str() for s in self.items) + ']'

    def add_lines_to(self, lines):
        if self.title:
            lines.append(self.title)
            lines.append('')
        if self.items:
            for item in self.items:
                lines.append('- ' + item.as_str())
            lines.append('')


@dataclass
class Section:
    title: str
    blocks: List[Block] = field(default_factory=list)

    def append(self, block: Block):
        self.blocks.append(block)

    def __str__(self):
        n = len(self)
        return f"Section[{n} Blocks]"

    def __len__(self):
        return len(self.blocks)

    def __getitem__(self, item):
        return self.blocks[item]

    def structure_str(self):
        pre = f"<{self.title}: " if self.title else '<'
        return pre + ' '.join(s.structure_str() for s in self.blocks) + '>'

    def add_lines_to(self, lines):
        if self.title:
            lines.append(self.title)
            lines.append('-' * len(self.title))
            lines.append('')
        for b in self.blocks:
            b.add_lines_to(lines)
        lines.append('')


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
    sections: List[Section] = field(default_factory=list)
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
        return ' '.join(s.structure_str() for s in self.sections)

    def combined_issues(self):
        return ' \u2022 '.join(s.message for s in self.issues)

    def to_text(self) -> str:
        lines = []

        errors = [i for i in self.issues if i.is_error]
        warnings = [i for i in self.issues if not i.is_error]

        if errors:
            lines.append(ERROR_DIRECTIVE)
            for issue in errors:
                lines.append('\t' + issue.as_text())
            lines.append('')
        if warnings:
            lines.append(WARNING_DIRECTIVE)
            for issue in warnings:
                lines.append('\t' + issue.as_text())
            lines.append('')

        # Add lines for each section
        for s in self.sections:
            s.add_lines_to(lines)

        # Remove trailing section definition and blank lines
        while lines and lines[-1] == '':
            lines = lines[:-1]
        return '\n'.join(lines)
