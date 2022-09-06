from typing import List

from docutils import parsers, utils, core, nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives, Directive

from . import model
from . import visitors

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


directives.register_directive('styles', StylesDirectiveHandler)


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


def prettify(sheet: model.Sheet, width: int = 100) -> str:
    lines = []

    # List the errors and warnings up front
    append_issues_rst(lines, ERROR_DIRECTIVE, [i for i in sheet.problems if i.is_error])
    append_issues_rst(lines, WARNING_DIRECTIVE, [i for i in sheet.problems if not i.is_error])

    # Add lines for each section
    for s in sheet.children:
        append_section_rst(lines, s, width)

    # Remove trailing section definition and blank lines
    while lines and lines[-1] == '':
        lines = lines[:-1]

    # Handle styles
    if sheet.styles:
        lines.append('')
        lines.append('.. styles::')
        for name, style in sheet.styles.items():
            lines.append('  ' + name)
            lines.append('    ' + style.to_definition())

    return '\n'.join(lines)


def description(comp: model.StructureUnit, short: bool = False) -> str:
    try:
        return comp.description(short)
    except AttributeError:
        return str(comp)


def append_issues_rst(lines: List[str], directive: str, issues: List[model.Problem]):
    """Convert issues to restructured text directives"""
    if issues:
        lines.append(directive)
        for issue in issues:
            lines.append(f"   [{issue.lineNo:3}] {issue.message}")
        lines.append('')


def append_item_rst(lines: List[str], item: model.Item, width: int):
    if not item.children:
        return
    txt = '- ' + item.children[0].to_rst(width, indent=2)
    lines.append(txt)

    if len(item.children) > 1:
        lines.append('')
        for run in item.children[1:]:
            txt = '  - ' + run.to_rst(width, indent=4)
            lines.append(txt.rstrip())
        lines.append('')


def append_block_rst(lines: List[str], block: model.Block, width: int):
    if block.title:
        lines.append(block.title.to_rst(width))
        lines.append('')

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
        space_for_last = width - (indent + column_widths_except_last + column_dividers)

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
                lines.append(('- ' + ' | '.join(row_parts).rstrip()))
            lines.append('')
            return lines

    # Could not fit onto one line; need to use the simple method
    for item in block.children:
        append_item_rst(lines, item, width)
    lines.append('')


def append_section_rst(lines: List[str], section: model.Section, width: int):
    """Adds restructured text lines for the given section"""
    if section.title:
        # Since the section title has to be underlined, we cannot wrap it
        title = section.title.to_rst()
        lines.append(title)
        lines.append('-' * len(title))
        lines.append('')
    if section.children:
        for b in section.children:
            append_block_rst(lines, b, width)
        lines.append('')
