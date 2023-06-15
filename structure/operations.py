import dataclasses
import re
from typing import List

from docutils import nodes
from docutils.parsers.rst import directives, Directive
from docutils.statemachine import StringList

from . import model, style
from .model import SheetOptions, Section, Block, Item, CommonOptions


# noinspection PyPep8Naming
class style_definitions(nodes.important):

    def __init__(self, lines: List[str]):
        super().__init__()
        self.lines = lines


class StylesDirectiveHandler(Directive):
    required_arguments = 0
    optional_arguments = 0
    has_content = True

    def run(self):
        lines = [s.rstrip() for s in self.content if s.rstrip()]
        return [style_definitions(lines)]


# noinspection PyPep8Naming
class settings(nodes.important):
    def __init__(self, name: str, options: str):
        super().__init__()
        self.name = name
        self.options = options


class script(nodes.important):
    def __init__(self, name: str, content: StringList):
        super().__init__()
        self.name = name
        self.content = content


class SettingsDirectiveHandler(Directive):
    required_arguments = 0
    optional_arguments = 100
    has_content = False

    # noinspection PyTypeChecker
    def run(self):
        return [settings(self.name, self.arguments)]


class ScriptDirectiveHandler(Directive):
    required_arguments = 0
    optional_arguments = 0
    has_content = True

    def run(self):
        return [script(self.name, self.content)]


# Register our directives
directives.register_directive('styles', StylesDirectiveHandler)
directives.register_directive('sheet', SettingsDirectiveHandler)
directives.register_directive('section', SettingsDirectiveHandler)
directives.register_directive('block', SettingsDirectiveHandler)
directives.register_directive('script', ScriptDirectiveHandler)


class Prettify:

    def __init__(self, sheet: model.Sheet, width):
        self.width = width
        self.sheet = sheet
        self.lines = None

        self.current_sheet_options = SheetOptions()
        self.current_section_options = Section().options
        self.current_block_options = Block.default_options('table')

    def run(self) -> str:
        self.lines = []

        # Output the options if they are not the default
        if self.current_sheet_options != self.sheet.options:
            self.append_sheet_options(self.sheet.options)

        # If we have multiple scripts, the first one goes up front
        scripts = self.sheet.scripts
        if len(self.sheet.scripts) > 1:
            self.append_script(scripts[0])
            scripts = scripts[1:]

        # Add lines for each section
        for s in self.sheet.children:
            self.append_section_rst(s, s == self.sheet.children[0])

        # Remove trailing section definition and blank lines
        while self.lines and self.lines[-1] == '':
            self.lines = self.lines[:-1]

        # Handle styles
        if self.sheet.styles:
            self.ensure_blank()
            self.append('.. styles::')
            for name, s in self.sheet.styles.items():
                self.append('   ' + name)
                self.append_wrapped(s.to_definition(), prefix='     ')

        # Scripts
        for script in scripts:
            self.append_script(script)

        return '\n'.join(self.lines)

    def append(self, txt: str) -> None:
        self.lines.append(txt)

    def _append_options(self, owner: str, options: CommonOptions, default: CommonOptions, forced: bool):
        owner_plus = owner + '::'
        parts = [f".. {owner_plus:9}"]

        parent_fields = [field.name for field in dataclasses.fields(CommonOptions)]
        my_fields = [field.name for field in dataclasses.fields(options)]

        ordered = [f for f in my_fields if f not in parent_fields] + parent_fields

        for k in ordered:
            v = getattr(options, k)
            if v != getattr(default, k):  # Only output attributes which are not the default
                k = k.replace('_', '-')
                if v is True:
                    parts.append(k)
                else:
                    if k in {'width', 'height', 'image-width', 'image-height', 'spacing'}:
                        v = style.len2str(v)
                    if k in {'image-brightness', 'image-contrast', }:
                        v = f"{round(v * 100)}%"
                    parts.append(k + '=' + str(v))

        # Only add if there actually were any changed values -- or we MUST do so
        if forced or len(parts) > 1:
            # If we had a previous '.. XXX::' or a previous blank line we do not need a blank line before
            while len(self.lines) > 1 and self.lines[-1] == '' and \
                    (self.lines[-2].startswith('..') or self.lines[-2] == ''):
                self.lines = self.lines[:-1]
            self.append(' '.join(parts))
            self.ensure_blank()

    def append_sheet_options(self, options: SheetOptions):
        self._append_options('sheet', options, SheetOptions(), False)

    def append_container_options(self, owner: str, options: CommonOptions, default: CommonOptions, forced: bool):
        self._append_options(owner, options, default, forced)

    def append_item_rst(self, item: model.Item, prefix: str):
        if not item.children:
            return
        txt = prefix + item.children[0].to_rst(self.width, indent=len(prefix))
        self.append(txt)

        if len(item.children) > 1:
            for run in item.children[1:]:
                txt = '  | ' + run.to_rst(self.width, indent=4)
                self.append(txt.rstrip())

    def append_block_rst(self, block: model.Block, is_first: bool):

        block_items = block.children
        if not block.title and not block_items and block.options.image > 0:
            # This is just an image, so we can represent it  easily
            self.append_image_block(block)
            return

        # If no title to define a start, then this defines the start
        if not block.title or block.options != self.current_block_options:
            # If we are the first block in our section, we do not need to force it
            forced = not block.title and not is_first
            # A new method resets the defaults
            if block.options.method != self.current_block_options.method:
                self.current_block_options = Block.default_options(block.options.method)
                self.current_block_options.method = '???????'
            self.append_container_options('block', block.options, self.current_block_options, forced)
            self.current_block_options = block.options

        if block.title:
            self.append_items([block.title], prefix='')
            self.ensure_blank()

        if not block_items:
            return

        self.append_items(block_items, prefix='- ')

    def append_items(self, items: list[Item], prefix: str):
        # Try to show as matrix of aligned cells
        ncols = max(len(i.children) for i in items)
        indent = len(prefix)

        if ncols > 1:
            # Create a table of simple text representations and calculate the maximum widths of each column
            table = [[run.to_rst().strip() for run in item.children] for item in items]
            col_widths = [0] * ncols
            ncol = max(len(r) for r in table)
            for row in table:
                if len(row) == ncol:
                    for c, txt in enumerate(row):
                        col_widths[c] = max(col_widths[c], len(txt))
            col_widths[-1] = 0  # stops it being left justified with trailing spaces

            column_widths_except_last = sum(col_widths[:1])
            column_dividers = 3 * (ncols - 1)  # ' | ' between each column
            space_for_last = self.width - (indent + column_widths_except_last + column_dividers)

            # Require at least 8 characters for the last cell. This is an ad-hoc number
            if space_for_last >= 8:
                for row, item in zip(table, items):
                    row_parts = []
                    for i, txt in enumerate(row):
                        if i < ncols - 1 or len(txt) <= space_for_last:
                            # Add the simple text, left-justified
                            row_parts.append(txt.ljust(col_widths[i]))
                        else:
                            # Need to wrap the text onto the next line
                            txt = item.children[i].to_rst(space_for_last, indent=2).strip()
                            row_parts.append(txt)
                    txt = (prefix + ' | '.join(row_parts).rstrip())
                    self.append(txt)
                self.ensure_blank()
                return
        # Could not fit onto one line; need to use the simple method
        for item in items:
            self.append_item_rst(item, prefix=prefix)
        self.ensure_blank()

    def append_image_block(self, block):
        # We just use the block options, but reformat for the image directive
        self._append_options('image', block.options, Block.default_options('image'), True)
        txt = self.lines[-2].replace('image=', 'index=').replace('image-', '')
        self.lines[-2] = txt

    def append_section_rst(self, section: model.Section, is_first):
        """Adds restructured text lines for the given section"""

        # If we have no title, the options define the start of a section, so we need this
        if section.options != self.current_section_options:
            # We do not require this if we have a title or we are the first section
            self.append_container_options('section', section.options, self.current_section_options, False)
            self.current_section_options = section.options
        elif is_first:
            pass
        else:
            self.ensure_blank()
            self.append('-' * self.width)
            self.ensure_blank()

        if section.children:
            for b in section.children:
                self.append_block_rst(b, b == section.children[0])
            self.ensure_blank()

    def append_wrapped(self, text: str, prefix: str):
        allowed = self.width - len(prefix)
        while True:
            if len(text) <= allowed:
                self.append(prefix + text)
                return
            p = text.rfind(' ', 0, self.width)
            if p < 0:
                # Fail; just throw everything in there
                self.append(prefix + text)
                return
            else:
                self.append(prefix + text[:p].rstrip())
                text = text[p:].lstrip()

    def ensure_blank(self, n: int = 1) -> None:
        if len(self.lines) >= n:
            while not all(s == '' for s in self.lines[-n:]):
                self.lines.append('')

    def append_script(self, script: list[str]):
        self.ensure_blank()
        self.append('.. script::')
        for s in script:
            s = s.strip()
            if s:
                self.append('   ' + s)
            else:
                self.ensure_blank()
        self.ensure_blank()


def description(comp: model.StructureUnit, short: bool = False) -> str:
    try:
        return comp.description(short)
    except AttributeError:
        return str(comp)


def prepare_for_visit(text: str) -> str:
    """ Solves common input formatting issues by modifying input"""
    text = re.sub("^(---*)\s*$", '\n----------------\n', text, flags=re.MULTILINE)
    return text


class Prettify2:

    def __init__(self, sheet: model.Sheet, width):
        self.width = width
        self.sheet = sheet
        self.lines = []

        self.current_section_options = Section().options
        self.current_block_options = Block().options

    def run(self) -> str:
        self.lines = []

        # Output the options if they are not the default
        if self.sheet.options != SheetOptions():
            self.append_options('sheet', self.sheet.options, SheetOptions())

        # Add lines for each section
        for s in self.sheet.children:
            self.process_section(s, s == self.sheet.children[0])

        # Handle styles
        if self.sheet.styles:
            self.ensure_blank()
            for name, s in self.sheet.styles.items():
                head = format(name)
                self.append(f".. style {name} " + s.to_definition())

        self.add_blank_lines()

        return '\n'.join(self.lines)

    def process_section(self, section: model.Section, is_first: bool):
        if not is_first:
            self.ensure_blank()
            self.append('-' * self.width)
            self.ensure_blank()
        if section.options != self.current_section_options:
            # We do not require this if we have a title or we are the first section
            self.append_options('section', section.options, self.current_section_options)
        if section.children:
            self.ensure_blank()
            for b in section.children:
                self.process_block(b, b == section.children[0])
        self.current_section_options = section.options

    def process_block(self, block: model.Block, is_first: bool):
        if block.title:
            self.ensure_blank()
            self.append_items([block.title], prefix='# ')
        elif not is_first:
            self.ensure_blank()
            self.append('#')
        if block.options != self.current_block_options:
            self.append_options('block', block.options, self.current_block_options)
        if block.options.image > 0:
            # Image first
            self.append_image_block(block)
        if block.children:
            self.append_items(block.children)
        self.current_block_options = block.options

    def add_blank_lines(self):
        pass

    def append_options(self, owner: str, options: CommonOptions, default: CommonOptions):
        head = f".. {owner}"
        parts = [f"{head:11}"]
        for field in dataclasses.fields(options):
            k = field.name
            v = getattr(options, k)
            if v != getattr(default, k):  # Only output attributes which are not the default
                k = k.replace('_', '-')
                if v is True:
                    parts.append(k)
                else:
                    if k in {'width', 'height', 'image-width', 'image-height'}:
                        v = style.len2str(v)
                    parts.append(k + '=' + str(v))

        # Only add if there actually were any changed values
        if len(parts) > 1:
            self.append(' '.join(parts))

    def append_items(self, items, prefix=''):
        ncols = max(len(item.children) for item in items)
        indent = max(2, len(prefix))

        # Create a table of simple text representations and calculate the maximum widths of each column
        table = [[run.to_rst().strip() for run in item.children] for item in items]
        col_widths = [0] * ncols
        for row in table:
            for c, txt in enumerate(row):
                col_widths[c] = max(col_widths[c], len(txt))
        col_widths[-1] = 0  # stops it being left justified with trailing spaces

        column_widths_except_last = sum(col_widths[:1])
        column_dividers = 3 * (ncols - 1)  # ' | ' between each column
        space_for_last = self.width - (indent + column_widths_except_last + column_dividers)

        # Require at least 8 characters for the last cell. This is an ad-hoc number
        if space_for_last >= 8:
            for row, item in zip(table, items):
                row_parts = []
                for i, txt in enumerate(row):
                    if i < ncols - 1 or len(txt) <= space_for_last:
                        # Add the simple text, left-justified
                        row_parts.append(txt.ljust(col_widths[i]))
                    else:
                        # Need to wrap the text onto the next line
                        txt = item.children[i].to_rst(space_for_last, indent=2).strip()
                        row_parts.append(txt)
                self.append((prefix + ' | '.join(row_parts).rstrip()))
            return

        # Could not fit onto one line; need to use a simpler method
        for item in items:
            for run in item.children:
                txt = prefix + '- ' + run.to_rst(self.width, indent=2 + len(prefix))
                self.append(txt.rstrip())
            self.ensure_blank()

    def append_image_block(self, block):
        # We just use the block options, but reformat for the image directive
        self.append_options('image', block.options, self.current_block_options,
                            "image image_mode image_width image_height image_anchor")
        self.lines[-1] = self.lines[-1].replace('image=', 'index=').replace('image-', '')

    def append(self, txt: str) -> None:
        self.lines.append(txt)

    def ensure_blank(self, n: int = 1) -> None:
        if len(self.lines) >= n:
            while not all(s == '' for s in self.lines[-n:]):
                self.lines.append('')
