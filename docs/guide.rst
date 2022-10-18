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
using the following syntax and table of options::

    .. sheet:: {options}

======================= =========================== =====================================================
Name                    Example                     Description
======================= =========================== =====================================================
width                   width=8.5in                 Page width in pixels, or with a sufix as in, cm, mm
height                  height=800                  Page height in pixels, or with a sufix as in, cm, mm
columns                 columns=2                   (experimental) Layout the sections in columns
quality                 quality=low                 Trade speed for quality in layout (low, medium, high, extreme)
debug                   debug                       Set to turn on debugging mode
style                   style=my_style_1            Define a style for each page (see styles documentation)
image                   image=1                     Set an image to use as a page background (1,2,3 or 0 for none)
image-mode              image-mode=stretch          image draw mode (see image documentation)
image-width             image-width=2in             image preferred width (see image documentation)
image-height            image-height=5cm            image preferred height (see image documentation)
image-anchor            image-anchor=nw             placement within frame (see image documentation)
image-brightness        image-brightness=50%        modification to image brightness (see image documentation)
image-contrast          image-contrast=120%         modification to image contrast (see image documentation)
======================= =========================== =====================================================




Sections
--------

Each sheet contain at least one section. If you set section options before adding any content to the section,
then the options will be appleid to that section. Once you define content for a section, then a section
directive will start a new section with the options given (if any)::

    .. section:: {options}

======================= =========================== =====================================================
Name                    Example                     Description
======================= =========================== =====================================================
columns                 columns=3                   Number of columns to use to lay out the section
equal                   equal                       If set, columns will all be the same width
style                   style=my_style_1            Define a style for the section (see styles documentation)
image                   image=1                     Set an image to use as a section background (1,2,3 or 0 for none)
image-mode              image-mode=stretch          image draw mode (see image documentation)
image-width             image-width=2in             image preferred width (see image documentation)
image-height            image-height=5cm            image preferred height (see image documentation)
image-anchor            image-anchor=nw             placement within frame (see image documentation)
image-brightness        image-brightness=50%        modification to image brightness (see image documentation)
image-contrast          image-contrast=120%         modification to image contrast (see image documentation)
======================= =========================== =====================================================

Sections contain multiple blocks, and those blocks are laid out newspaper-style with the number of columns
defined by the section options. Blocks are placed into the first column until it is filled, and then into
the second and so on.

If 'equal' has been defiend as an option, then the column widths will all be the same. Otehrwise, their
widths will be dynamically chosen to make the layout look good by minimizing breaks, trying to get the columns
a similar height and so on. This can be a slow algorithm as it tries out many combinations, and this is where the
sheet 'quality' setting comes in; the higher the quality, the more combiantions are tried and the slower the process.

.. note:: If the layout is slow, set the 'equal' option to avoid the complex calculation until the content looks
          good. Alternatively, you could lower the quality and switch it to a high setting when you are happy with
          the overall look and want to make it perfect!

Blocks
------

Blocks are the fundamental unit that contains information to display on a sheet. Blocks may contain a **title**
and **content**.

The general format of a block looks like this::

    .. block:: options

       block title

       - first block item
       - second block item

.. note:: You must separate a block title from its items by a blank line

Block options are optional -- any text on a new line with a blank line before it defines a new block,
whether or not options have been defined. Furthermore, the options for a new block are coptied from the previous
ones, so if you change (say) the style for one block, that will be the style used for all subsequent blocks
in the document until you set a new style in a block options. Block options are:


    method: str = 'table'
    equal : bool = False
    title: str = None
    title_style: str = None

======================= =========================== =====================================================
Name                    Example                     Description
======================= =========================== =====================================================
method                  method='attributes'         How to display the items (table, attributes)
equal                   equal                       If set, table columns will all be the same width
style                   style=my_style_1            Define a style for the block (see styles documentation)
title                   title='none'                How to display the title (banner, inline, none)
title_style             title_style=t2              Define a style for the block title (see styles documentation)
image                   image=1                     Set an image to use in the block (1,2,3 or 0 for none)
image-mode              image-mode=stretch          image draw mode (see image documentation)
image-width             image-width=2in             image preferred width (see image documentation)
image-height            image-height=5cm            image preferred height (see image documentation)
image-anchor            image-anchor=nw             placement within frame (see image documentation)
image-brightness        image-brightness=50%        modification to image brightness (see image documentation)
image-contrast          image-contrast=120%         modification to image contrast (see image documentation)
======================= =========================== =====================================================


Titles and content items in a block can contain multiple parts, separated by a '|' symbol
(often called a *pipe symbol*). When the block method is `table` -- the default -- then the pipe symbol
divides up a row into columns; the first part is the in the first column, the second in the second, etc. Some
notes for tables:

* The number of columns in a table is equal to the number of columns in the row with the most columns
* The last part in a row fills all the remaining columns to the right of the table.
* By default, the right column is right aligned.
* If there are more than two columns, the central columns are center aligned

When the block method is `attributes`, then each itme is expected to have two or three parts.
The first is the name of an attribute, the second its value and the third is a optional 'other value'.
These are drawn in a specific block layout for that attribute


Items
-----

As mentioned above, items form the content of blocks.

An item is defined using a list item prefix, a dash or a bullet.
If an item text is long, then when you wrap it, make sure you indent subsequent lines to keep them part
of the same item. You do not need to put blank lines between list items.

Here is an example of a block with three items::

    History

    - Born in Ireland in 787AD
    - Age 18, they went on a raid against the Cymric
      tribes to the east, and won much glory
    - Settled in the south

items can be divided up into part by pipe symbols, and within each part further special markup is allowed:


======================= =========================== =====================================================
Type                    Examples                    Notes
======================= =========================== =====================================================
Check Box               [X] or [ ]                  Exactly one character must be present between the square braces
Text Field              [[ abc ]]                   Text inside is placed in the editable field
Literal                 \`\`\*asterisks are fun\`\`      Anything between double back-quotes is treated as simple text
Bold                    \*\*wow\*\*                     asterisks must surround words, not white space
Italic                  \*gosh\*                      asterisks must surround words, not white space
Script Variable         {level}                     the value of a *script variable*
======================= =========================== =====================================================

For text fields, the width of them (use blank spaces just to make them longer) is taken as a hint as to the size
you want them to be, but when actually placed in a block, they will fill up the available space.

Script Variables are covered later in the **Scripts** topic.


Styles
======

Styles are designed to be similar to the way they are used in HTML.
They provide a list of options that control the appearance of the content.
Sheets, sections, blocks and block titles each have their own style with a default that can be overriden
by definign a **styles** section, usually placed at the bottom of your sheet. An example style section looks
like this::

    .. styles::
       default
         text-opacity:0.8 font-family:Montserrat font-size:8 font-spacing:90%
       attr
         text-color:white text-align:center font-size:14 border:black border-width:0.5 background:brown
         padding:4
       default-block
         border:none
 
After the `.. styles:` directive, styls are defined by a name ona  sinlge line, followed by a list of 
properties on indented lines following. 

In the above example, the default font **default** has been overriden. Since all styles are based on this
style to some extent, those definitions will affect pretty much everything. The default definition for the block
has also been changed so that blcoks no longer have borders by default.

The style **attr** is not a default style however, so setting values for it will only change the appearance of
parts of the sheet that specifically reference this style.


Style Inheritance
-----------------

All styles (except *default*) inherit from another style, and if values of the base style are not defined,
then the values of the style's parent are used. When you define your own style, it is automatcially given a
parent to inherit from if you do not define one explicitly. Usually, that should be a good enough choice for
you. The choice of what to inherit from is done semi-intelligently; if a style is mostly used for attributes,
for example, it will inherit from *default-attributes*.


Default Styles
--------------

The following styles are the pre-defined defaults used in ZeeSheet::

        default =   text-color:auto text-opacity:1 text-align:auto text-align-last:same text-indent:4 
                    font:Montserrat font-size:10 font-face:Regular font-spacing:100%
                    box-color:auto box-opacity:1 box-width:1 box-border-color:auto box-border-opacity:1
                    box-margin:0 box-padding:2 effect:none effect-size:3
        
        default-title =     inherit:default font-size:11 font-face:bold padding:1
        default-block =     inherit:default margin:8
        default-section =   inherit:default margin:0 padding:0 border:none background:none
        default-image =     inherit:default-block inherit:default-block border:none background:none
        default-sheet =     inherit:default padding:0.25in margin:0 border:none background:none
        default-hidden =    inherit:default margin:0 padding:0 font-size:1 border:none 
        
        default-attributes =        inherit:default-block font-size:12 bg:#004166 padding:'6 4' 
                                    align:auto box-effect:rounded
        default-attributes-title =  inherit:default-title font-size:22 margin:2 padding:6 
                                    text-color:yellow align:auto

Style Attributes
----------------

Styles are defined with a simple key-value pairs. You can use quotes to surround attribute values that
have spaces in them, such as font names or padding arrays. Here is the full list of style options:

======================= =========================== =====================================================
Name                    Example                     Description
======================= =========================== =====================================================
text-color              text-color:#dfe             Color of the text drawn
text-opacity            text-opacity:1              How transparent the text is to be displayed as
text-align              text-align:auto             How to align the text
text-align-last         text-align-last:same        How to align the last line of text that wraps
text-indent             text-indent:4               Indentation for 2nd and subsequent lines of wrapped text
font                    font:Montserrat             The family to use for the font
font-size               font-size:10                font size in points
font-face               font-face:ExtraThin         Fonts can have a variety of faces to choose from
font-spacing            font-spacing:90%            Modify the default line spacing between text lines
box-color               box-color:auto              The background color (usually of a box, but not always)
box-opacity             box-opacity:1               The opacity of the background color
box-width               box-width:1                 The width of the box border
box-border-color        box-border-color:auto       The color of the box border
box-border-opacity      box-border-opacity:1        The opacity of the box border
box-margin              box-margin:0                The space between the border of a box and its container
box-padding             box-padding:2               The space between the border of a box and its contents
effect                  effect:none                 A special effect for the border (none, rounded, rough, cogs)
effect-size             effect-size:3               How big the effect is, in pixels
======================= =========================== =====================================================

Color
    Colors can be a name (red, pink, beige, ...) or a hex representation (#ddd, #fda43c).
    The name 'none' requests that text not be drawn, and the special name 'auto' attmpts to choose
    a color that will match well with other defined colors for the style. It even considers the colors in
    other styles in the same block. This allows you to define a background color, for example, and have the
    text color automatically chosen to contrast well with it.
Fraction
    Fractions can be defined as a number such as '0.75', or as a poercentage, such as '75%'
Alignment
    'auto' alignment is used in tables so that the left column is left aligned and the right column
    right aligned. 'same' alignment (for *text-align-last*) sattes that the alignment of the last
    line in some wrapping text is aligned the same was as the previous lines. Standard alignments are left,
    right and center.
Font
    Helvetica, Courier and Times and all Google Fonts (as of 2022-10-1) are available to be used.
    The excellent site https://goofonts.com is a great resource to choose a font for
    a sheet.
