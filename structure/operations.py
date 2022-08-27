from typing import List

from docutils import parsers, utils, core
from docutils.parsers import rst

from . import model
from . import visitors

ERROR_DIRECTIVE = '.. ERROR::'
WARNING_DIRECTIVE = '.. WARNING::'


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
    append_issues_rst(lines, ERROR_DIRECTIVE, [i for i in sheet.issues if i.is_error])
    append_issues_rst(lines, WARNING_DIRECTIVE, [i for i in sheet.issues if not i.is_error])

    # Add lines for each section
    for s in sheet.children:
        append_section_rst(lines, s, width)

    # Remove trailing section definition and blank lines
    while lines and lines[-1] == '':
        lines = lines[:-1]

    return '\n'.join(lines)

def description(comp: model.StructureComponent, short:bool =False) -> str:
    return comp.structure_str(short)

def append_issues_rst(lines: List[str], directive: str, issues: List[model.Issue]):
    """Convert issues to restructured text directives"""
    if issues:
        lines.append(directive)
        for issue in issues:
            lines.append('   ' + issue.as_text())
        lines.append('')


def append_item_rst(lines: List[str], item: model.Item, width: int):
    if not item.children:
        return
    txt = '- ' + item.children[0].as_str(width, indent=2)
    lines.append(txt)

    if len(item.children) > 1:
        lines.append('')
        for run in item.children[1:]:
            txt = '  - ' + run.as_str(width, indent=4)
            lines.append(txt)
        lines.append('')


def append_block_rst(lines: List[str], block: model.Block, width: int):
    if block.title:
        lines.append(block.title.as_str(width))
        lines.append('')

    if not block.children:
        return

    # Try to show as matrix of aligned cells
    ncols = block.column_count()

    if ncols > 1:
        # Create a table of simple text representations and calculate the maximum widths of each column
        table = [[run.as_str().strip() for run in item.children] for item in block.children]
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
                        txt = item.children[i].as_str(space_for_last, indent=2).strip()
                        row_parts.append(txt)
                lines.append(('- ' + ' | '.join(row_parts)))
            lines.append('')
            return lines

    # Could not fit onto one line; need to use the siple method
    for item in block.children:
        append_item_rst(lines, item, width)
    lines.append('')


def append_section_rst(lines: List[str], section: model.Section, width: int):
    """Adds restructured text lines for the given section"""
    if section.title:
        # Since the section title has to be underlined, we cannot wrap it
        title = section.title.as_str()
        lines.append(title)
        lines.append('-' * len(title))
        lines.append('')
    if section.children:
        for b in section.children:
            append_block_rst(lines, b, width)
        lines.append('')
