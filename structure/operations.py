from typing import List, Union, Iterable

from docutils import parsers, utils, core, nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives, Directive

from . import model, style
from . import visitors
from .model import SheetOptions, Sheet, Section, Block, ContainerOptions

ERROR_DIRECTIVE = '.. ERROR::'
WARNING_DIRECTIVE = '.. WARNING::'


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


class SettingsDirectiveHandler(Directive):
    required_arguments = 0
    optional_arguments = 100
    has_content = False

    def run(self):
        return [settings(self.name, self.arguments)]


# Register our directives
directives.register_directive('styles', StylesDirectiveHandler)
directives.register_directive('page', SettingsDirectiveHandler)
directives.register_directive('section', SettingsDirectiveHandler)
directives.register_directive('block', SettingsDirectiveHandler)


def text_to_sheet(text: str) -> model.Sheet:
    """Parses the text and builds the basic structure out of it"""
    parser = parsers.rst.Parser()
    # noinspection PyTypeChecker
    settings = core.Publisher(parser=parsers.rst.Parser).get_settings()
    settings.halt_level = 99
    document = utils.new_document(text, settings)
    parser.parse(text, document)
    main_visitor = visitors.StructureBuilder(document)
    document.walkabout(main_visitor)
    return main_visitor.get_sheet()


class Prettify:

    def __init__(self, sheet: model.Sheet, width):
        self.width = width
        self.sheet = sheet
        self.lines = None

        self.current_sheet_options = SheetOptions()
        self.current_section_options = Section().options
        self.current_block_options = Block().options

    def run(self) -> str:
        self.lines = []

        # Output the options if they are not the default
        if self.current_sheet_options != self.sheet.options:
            self.append_sheet_options(self.sheet.options)

        # Add lines for each section
        for s in self.sheet.children:
            self.append_section_rst(s)

        # Remove trailing section definition and blank lines
        while self.lines and self.lines[-1] == '':
            self.lines = self.lines[:-1]

        # Handle styles
        if self.sheet.styles:
            self.append('')
            self.append('.. styles::')
            for name, style in self.sheet.styles.items():
                self.append('   ' + name)
                self.append('     ' + style.to_definition())

        return '\n'.join(self.lines)

    def append(self, txt: str) -> None:
        self.lines.append(txt)

    def _append_options(self, owner: str, options: Union[SheetOptions, ContainerOptions], default, attributes: str):
        parts = [f".. {owner}::"]
        for k in attributes.split():
            v = getattr(options, k)
            if v != getattr(default, k):  # Only output attributes which are not the default
                k = k.replace('_', '-')
                if v is True:
                    parts.append(k)
                else:
                    if k in {'width', 'height'}:
                        v = style.len2str(v)
                    parts.append(k + '=' + v)
        self.append(' '.join(parts))
        self.append('')

    def append_sheet_options(self, options: SheetOptions):
        self._append_options('page', options, SheetOptions(), "width height style debug")

    def append_container_options(self, owner: str, options: ContainerOptions,  default:ContainerOptions):
        self._append_options(owner, options, default, "title style title_style")

    def append_item_rst(self, item: model.Item):
        if not item.children:
            return
        txt = '- ' + item.children[0].to_rst(self.width, indent=2)
        self.append(txt)

        if len(item.children) > 1:
            self.append('')
            for run in item.children[1:]:
                txt = '  - ' + run.to_rst(self.width, indent=4)
                self.append(txt.rstrip())
            self.append('')

    def append_block_rst(self, block: model.Block):
        if block.title:
            self.append(block.title.to_rst(self.width))
            self.append('')

        if block.options != self.current_block_options:
            # Remember the new one and write it out
            self.current_block_options = block.options
            self.append_container_options('block', block.options, Block().options)

        if not block.children:
            return

        # Try to show as matrix of aligned cells
        ncols = block.column_count()

        if ncols > 1:
            # Create a table of simple text representations and calculate the maximum widths of each column
            table = [[run.to_rst().strip() for run in item.children] for item in block.children]
            col_widths = [0] * ncols
            for row in table:
                for c, txt in enumerate(row):
                    col_widths[c] = max(col_widths[c], len(txt))
            col_widths[-1] = 0  # stops it being left justified with trailing spaces

            indent = 2  # leading '- '
            column_widths_except_last = sum(col_widths[:1])
            column_dividers = 3 * (ncols - 1)  # ' | ' between each column
            space_for_last = self.width - (indent + column_widths_except_last + column_dividers)

            # Require at least 8 characters for the last cell. This is an ad-hoc number
            if space_for_last >= 8:
                for row, item in zip(table, block.children):
                    row_parts = []
                    for i, txt in enumerate(row):
                        if i < ncols - 1 or len(txt) <= space_for_last:
                            # Add the simple text, left-justified
                            row_parts.append(txt.ljust(col_widths[i]))
                        else:
                            # Need to wrap the text onto the next line
                            txt = item.children[i].to_rst(space_for_last, indent=2).strip()
                            row_parts.append(txt)
                    self.append(('- ' + ' | '.join(row_parts).rstrip()))
                self.append('')
                return

        # Could not fit onto one line; need to use the simple method
        for item in block.children:
            self.append_item_rst(item)
        self.append('')

    def append_section_rst(self, section: model.Section):
        """Adds restructured text lines for the given section"""
        if section.title:
            # Since the section title has to be underlined, we cannot wrap it
            title = section.title.to_rst()
            self.append(title)
            self.append('-' * len(title))
            self.append('')

        if section.options != self.current_section_options:
            # Remember the new one and write it out
            self.current_section_options = section.options
            self.append_container_options('section', section.options, Section().options)

        if section.children:
            for b in section.children:
                self.append_block_rst(b)
            self.append('')


def prettify(sheet: Sheet, width: int = 100) -> str:
    return Prettify(sheet, width).run()


def description(comp: model.StructureUnit, short: bool = False) -> str:
    try:
        return comp.description(short)
    except AttributeError:
        return str(comp)
