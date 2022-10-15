Document structure
==================

A character sheet document has the following structure, working from the top down:

Sheet
    This is the whole document. It comprises one or more sections.
    The sheet has the same layout options as a section does, but typically the simple
    layout of of stacking sections below each other works well
Section
    A section is a rectangular area comprised of a set of blocks.
    Each section has a defined layout and places the blocks inside that layout.
    Sections usually have titles which can be displayed or hidden.
    A simple sheet may only have a single section.
Block
    The block is the fundamental layout unit. It is rectangular area and contains a
    number of items that are laid out inside it. It has a title which may be displayed or hidden.
    Blocks have differemt layout options, sometimes very specific to the content,
    but the table layout is the most common (nd the default).
    All items in a block share the same basic presentation style
Item
    Blocks are divided into items, each of which displays as a coherent whole.
    In a 'table' block, an item corresponds to a row of the table.
    In an 'attributes' block, an item corresponds to a single attribute.
    Items usually have multiple parts, each of which is a combination of
    piece of text, editable fields, or checkboxes.

Example
-------

For a simple character sheet consisting of a name, a picture, a description, three statistics and two skills,
we might have something like this::

    Basic Information

    - Zonani the fire mage
    - Powerfully built, she wields a staff of living flame
    - [image:nowhere.com/abc.png]

    Statistics

    - Body: **2**
    - Mind: **6**
    - Soul: **4**

    Skills

    - Oration  | +4
    - Sneaking Up On People | +3

This has one (unnamed, default) section and three blocks. The blocks have 3, 3, and 2 items in them.
The second block uses asterisks to give a strong style to the numbers, and the third block uses a vertical
bar (also knowns as a 'pipe symbol') to specify alignment.


Syntax
======

This section describes the syntax for each component

Sheet
-----

The sheet is the top level object. It consists of a list of sections and can be given the following options
using the following syntax::
    .. sheet:: {options}

Sheet Options

======================= =========================== =====================================================
Name                    Example                     Description
======================= =========================== =====================================================
width                   width=8.5in                 Page width in pixels, or with a sufix as in, cm, mm
height                  height=800                  Page height in pixels, or with a sufix as in, cm, mm
columns                 columns=2                   (experimental) Layout the sections in columns
quality                 quality=low                 Trade speed for quality in layout (low, medium, high, extreme)
debug                   debug                       Set to turn on debugging mode
style                   style='name'                Define a style for each page (see styles documentation)
image                   image=1                     Set an image to use as a page background (1,2,3 or 0 for none)
*image-?????*           *various options*           Set image options (see image documentation)
======================= =========================== =====================================================

Sections
--------

A sheet starts with a default unnamed section. If you define a section before other content, it will be
replaced with that section. Sections are defined as an underlined title, like so::

    Best Section Ever
    -----------------

Note that section titles cannot span multiple lines.


To start a new section, simply add a new heading, like the one above.

.. note:: You can use equal signs or a few other symbols to underline if you prefer,
          but you must be consistent; don't mix two different styles!




Blocks
------

Any block of text that has no indentation and is surrounded by blank lines defines a new block
with that text as the title. It's legal for the block title to span multiple lines, but it's
not a great idea to have long block titles, so in general, try and keep them short.

.. note:: You must separate a block title from its items by a blank line in all cases.


Items
-----

An item is defined using a list item prefix, a dash or a bullet.
If an item text is long, then when you wrap it, make sure you indent subsequent lines to keep them part
of the same item. You do not need to put blank lines between list items.

Here is an example of a block with three items::

    History

    - Born in Ireland in 787AD
    - Age 18, they went on a raid against the Cymric
      tribes to the east, and won much glory
    - Settled in the south


Special Text Markup
===================

Anytime text is defined for viewing (item content, block and section markers) it can be simple text
or it can contain special markup. Here is a list of the markup allowed:

Bold and Italic
  Use single or double asterisks around simple text to indicate italic or bold content.
  There must be no whitespace between the asterisks and the content.

Literal tags
  To ensure that text is processed as literal text with no processing, use two back-quotes around
  the content. The enclosed content can span lines if desired


Examples
--------

.. code-block::

    Asterisks denote **bold** or *italic* text

    ``This is literal text. Special characters are ignored,
    such as *these*, [ ]``.


