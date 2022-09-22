import reprlib
import warnings
from copy import copy

import docutils.nodes
import docutils.nodes
from reportlab.lib import units

from common.logging import message_unknown_attribute, message_parse, message_bad_value, configured_logger
from . import style
from .model import *

LOGGER = configured_logger(__name__)

# These tags will not  be recorded
IGNORE_TAGS = {'document', 'system_message', 'literal', 'substitution_reference',
               'problematic', 'settings', 'style_definitions'}

# These tags will be recorded, but they are only used to identify where we are in the
# processing tree; no action is taken when they are entered or departed from
NO_ACTION_TAGS = {'title', 'bullet_list', 'list_item', 'definition_list', 'term', 'emphasis', 'strong'}

# These items as out ancestors determine that text is the title of a block
BLOCK_TITLE_ANCESTRY = {'paragraph', 'section • paragraph', 'definition_list_item • term'}


def _tag(node: docutils.nodes.Node):
    return getattr(node, 'tagname')


# noinspection PyUnresolvedReferences
def _line_of(node: docutils.nodes.Node):
    if not node:
        return None
    if 'line' in node:
        return node['line']
    try:
        line = node.line
        if line is not None:
            return line
    except KeyError:
        pass
    return _line_of(node.parent)


def _apply_option_definitions(owner: str, definitions: Dict[str, str], options):
    for k, v in definitions.items():
        try:
            _set_option(options, owner, k, v)
        except AttributeError:
            warnings.warn(message_unknown_attribute(owner, k, 'option'))
        except ValueError:
            warnings.warn(message_bad_value(owner, k, f"Illegal value '{v}'", 'option'))
        except RuntimeError as ex:
            warnings.warn(message_bad_value(owner, k, str(ex), 'option'))


def _set_option(options, owner, k, v):
    if k == 'style':
        options.style = v
    elif k == 'title-style':
        options.title_style = v
    elif k == 'columns' and owner != 'block':
        i = int(v)
        if 1 <= i <= 8:
            options.columns = i
        else:
            message = f"columns attribute must be an integer in the range 1 .. 8, but was '{v}'."
            raise RuntimeError(message)
    elif k == 'width':
        options.width = units.toLength(v)
    elif k == 'height':
        options.height = units.toLength(v)
    elif k == 'title':
        if v.lower() in ('none', 'simple'):
            options.title = v.lower()
        else:
            message = f"'{v}' is not a legal value for the style attribute {k}. Should be one of none, simple"
            raise RuntimeError(message)
    elif isinstance(v, bool):
        if hasattr(options, k):
            setattr(options, k, v)
        else:
            raise AttributeError()
    else:
        raise AttributeError()


class StructureBuilder(docutils.nodes.NodeVisitor):
    def __init__(self, document):
        super().__init__(document)

        # Initialize the sheet with a new empty section and block
        self.sheet = Sheet()

        # Set our stack of what we are processing
        self.process_stack = []

        # Set the current options
        # There is only one sheet, so we don't need to keep track of the current sheet options
        self.section_options = self.current_section.options
        self.block_options = self.current_block.options

    def get_sheet(self) -> Sheet:
        # Fix up pieces we added, but ended up unused
        self.sheet.tidy()
        return self.sheet

    # noinspection PyTypeChecker
    @property
    def current_section(self) -> Section:
        """The Section we are currently defining"""
        component = self.sheet
        return component.children[-1]

    # noinspection PyTypeChecker
    @property
    def current_block(self) -> Block:
        """The Block we are currently defining"""
        return self.current_section.children[-1]

    # noinspection PyTypeChecker
    @property
    def current_item(self) -> Item:
        """The Item we are currently defining"""
        return self.current_block.children[-1]

    # noinspection PyTypeChecker
    @property
    def current_run(self) -> Run:
        """The Run we are currently defining"""
        return self.current_item.children[-1]

    def unknown_visit(self, node: docutils.nodes.Node) -> None:
        """Handle a visit for node type we do not explicitly handle"""
        tag = _tag(node)
        if tag not in IGNORE_TAGS:
            if tag not in NO_ACTION_TAGS:
                self.error(node, f"{tag} tag not supported")
            self.start(node)

    def unknown_departure(self, node) -> None:
        """Handle a visit for node type we do not explicitly handle"""
        if _tag(node) not in IGNORE_TAGS:
            self.finish(node)

    # Visit methods ###################################################################

    def visit_section(self, node) -> None:
        """Unsurprisingly, each Section defines a Section"""
        self.start(node)
        self._make_new_section()

    def visit_definition_list_item(self, node) -> None:
        """Each Definition List defines a block"""
        self.start(node)
        self._make_new_block()

    def visit_definition(self, node) -> None:
        p = self.start(node)
        if p == 'document':
            self._make_new_block()

    def visit_paragraph(self, node) -> None:
        p = self.start(node, n=1)
        if p == '' or p == 'section':
            self._make_new_block()
        elif p == 'list_item':
            if self._count_ancestors('list_item') > 1:
                # New run within the item
                self.current_item.children.append(Run())
            else:
                self._make_new_item()
        else:
            self.error(node, 'Unexpected paragraph encountered')

    def visit_system_message(self, node: docutils.nodes.system_message) -> None:
        # The departure will not be noted, so must not record this
        message = node.children[0].astext()
        self.error(node, message)

        # No processing of children
        raise docutils.nodes.SkipChildren

    def visit_literal(self, node: docutils.nodes.Node) -> None:
        assert len(node.children) == 1
        text = node.children[0].astext()
        element = Element(text, 'literal')

        p = self.start(node)
        self.add_elements([element], node, p)
        self.finish(node)

        # No processing of children
        raise docutils.nodes.SkipChildren

    # noinspection PyPep8Naming
    def visit_Text(self, node: docutils.nodes.Text) -> None:
        if self._parent() == 'emphasis':
            s = 'emphasis'
            p = self.start(node, skip_last=True)
        elif self._parent() == 'strong':
            s = 'strong'
            p = self.start(node, skip_last=True)
        else:
            s = None
            p = self.start(node)

        text = node.astext().replace('\n', ' ')
        elements = Element.text_to_elements(text, s)
        self.add_elements(elements, node, p)

    def visit_problematic(self, node: docutils.nodes.Node) -> None:
        if node.astext() == '|':
            pass
        else:
            self.error(node, 'Problematic syntax')

    def visit_substitution_reference(self, node: docutils.nodes.Node) -> None:
        # Treat the pipe symbols as actual text both before and after
        p = self._processing(2)
        elements = Element.text_to_elements('|', None)
        self.add_elements(elements, node, p)

    def depart_substitution_reference(self, node: docutils.nodes.Node) -> None:
        # Treat the pipe symbols as actual text both before and after
        p = self._processing(2)
        elements = Element.text_to_elements('|', None)
        self.add_elements(elements, node, p)

    def visit_settings(self, node):
        definitions = {}
        for o in node.options:
            oo = o.split('=')
            if len(oo) == 1:
                # No equals, so it's a boolean we set to true
                definitions[o] = True
            else:
                # Two parts
                definitions[oo[0]] = oo[1]

        # Find the options to set into
        if node.name == 'page':
            _apply_option_definitions(node.name, definitions, self.sheet.options)
        elif node.name == 'section':
            _apply_option_definitions(node.name, definitions, self.section_options)
        elif node.name == 'block':
            _apply_option_definitions(node.name, definitions, self.block_options)
        else:
            raise KeyError(f'Currently unsupported settings for {node.name}')

    def visit_style_definitions(self, node) -> None:
        lines: List[str] = node.lines
        current_style = None
        for raw in lines:
            line = raw.lstrip()
            if line == raw:
                # No indentation means we define a style
                name = line.lower()
                if name.endswith(':'):
                    name = name[:-1].strip()
                if not name.replace('-', '_').isidentifier():
                    self.error(node, f"{name} is not a valid identifier for a style")
                current_style = Style(name)
                self.sheet.styles[name] = current_style
            else:
                # Indented means this is a definition
                if not current_style:
                    self.error(node, 'You must name the style you wish to use before defining its properties')
                else:
                    style.set_using_definition(current_style, line.lstrip())

    # Other methods ####################################################################

    def start(self, node: docutils.nodes.Node, n: int = 2, skip_last: bool = False) -> str:
        current = self._processing(n, skip_last=skip_last)
        self.process_stack.append(_tag(node))
        return current

    def finish(self, node: docutils.nodes.Node):
        what = _tag(node)
        expected = self.process_stack.pop()
        if expected != what:
            raise RuntimeError(f"Expected to be finishing {expected}, but encountered {what}")

    def error(self, node: docutils.nodes.Node, message: str):
        ancestors = self._processing(n=5).strip()
        text = reprlib.repr(node.astext())
        warnings.warn(message_parse(message, text, ancestors, line=_line_of(node)))

    def add_elements(self, elements, node, p):
        if p in BLOCK_TITLE_ANCESTRY:
            self.current_block.title.children += elements
        elif p == 'section • title':
            self.current_section.title.children += elements
        elif p == 'list_item • paragraph':
            self.current_run.children += elements
        else:
            self.error(node, 'Unexpected text encountered')

    def _processing(self, n: int = 2, skip_last: bool = False):
        """Text form of where we are in the processing tree"""
        if skip_last:
            return ' • '.join(self.process_stack[-n - 1:-1])
        else:
            return ' • '.join(self.process_stack[-n:])

    def _parent(self):
        """Previous step in the tree"""
        return self.process_stack[-1]

    def _make_new_section(self) -> None:
        # If the current section is undefined, we just use that
        if self.current_section:
            section = Section(options=copy(self.section_options))
            self.sheet.children.append(section)

    def _make_new_block(self) -> None:
        # If the current block is undefined,we do not need a new one
        if self.current_block:
            block = Block(options=copy(self.block_options))
            self.current_section.children.append(block)

    def _make_new_item(self) -> None:
        # If the current run is undefined, we just use that
        block = self.current_block
        if block.children[-1]:
            block.children.append(Item())

    def _count_ancestors(self, target):
        return sum(t == target for t in self.process_stack)
