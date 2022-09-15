"""

    This file contains code needed to take a download of the full google fonts and package them up
    suitable for use in the system.

    This code should not be run by the service.

"""
from collections import defaultdict

import fontTools.ttLib as ttLib
import fontTools.varLib.mutator

from fonts import *


def copy_fonts_locally():
    """
        Extracts ttf fonts and copies them to local directory.
        The 'src' defined below is where the fotns have been downloaded
    """
    src = Path('/Users/graham/Downloads/fonts-main')
    assert src.exists() and src.is_dir()
    assert FONT_DIR.exists() and FONT_DIR.is_dir()
    for f in src.glob('**/*.ttf'):
        name = f.name
        if '[' in name:
            name = name[:name.index('[')] + '.ttf'
        print(FONT_DIR / name)
        f.rename(FONT_DIR / name)


def convert_variable_fonts():
    files = list(FONT_DIR.glob('*.ttf'))

    for i, f in enumerate(files):
        tt = ttLib.TTFont(f.absolute())
        try:
            instances = tt["fvar"].instances
            for instance in instances:
                variant = str(tt["name"].getName(instance.subfamilyNameID, 3, 1)).replace(' ', '')
                family = tt['name'].getBestFamilyName()
                dest = f.parent / (family + '-' + variant + '.ttf')
                if not dest.exists():
                    print(f'[{i:4}/{len(files)}]: Creating {dest}')
                    tt1 = fontTools.varLib.mutator.instantiateVariableFont(tt, instance.coordinates)
                    tt1.save(dest.absolute())
            f.unlink()
        except KeyError:
            pass


def _register_single(name):
    loc = FONT_DIR / (name + '.ttf')
    font = TTFont(name, loc.absolute())
    pdfmetrics.registerFont(font)


def _register_multiple(name):
    loc = FONT_DIR / (name + '.ttf')
    font = TTFont(name, loc.absolute())
    pdfmetrics.registerFont(font)


def find_or_default(name, variants, default):
    """ Find the font or return a default result"""
    for variant in variants:
        loc = FONT_DIR / (name + '-' + variant + '.ttf')
        if loc.exists():
            _register_single(loc.stem)
            return loc.stem
    return default


def read_files_for_faces() -> Dict[str, Dict[str, str]]:
    files = list(FONT_DIR.glob('*.ttf'))
    result = defaultdict(lambda: {})
    for i, f in enumerate(sorted(files)):
        tt = ttLib.TTFont(f.absolute())
        family = tt['name'].getBestFamilyName()
        if family.startswith('js'):
            continue

        # Sighs. Why bad names, why?
        if f.stem.startswith('Recursive-MonoCasual'):
            family = 'Recursive-MonoCasual'
            face = f.stem[len(family):]
        elif f.stem.startswith('Recursive-MonoLinear'):
            family = 'Recursive-MonoLinear'
            face = f.stem[len(family):]
        elif f.stem.startswith('Recursive-SansCasual'):
            family = 'Recursive-SansCasual'
            face = f.stem[len(family):]
        elif f.stem.startswith('Recursive-SansLinear'):
            family = 'Recursive-SansLinear'
            face = f.stem[len(family):]
        else:
            p = f.stem.rfind('-')
            if p < 0:
                if f.stem.endswith('Bold'):
                    family, face = f.stem[:-4], 'Bold'
                elif f.stem.endswith('Italic'):
                    family, face = f.stem[:-6], 'Italic'
                elif f.stem.endswith('BoldItalic'):
                    family, face = f.stem[:-10], 'Italic'
                else:
                    face = 'Regular'
            else:
                face = f.stem[p + 1:]

        if not face:
            face = 'Regular'
        # print(f"{f.stem:>50}: face = {face}")
        result[family.lower()][face] = f.stem
    return result


def build_family_info():
    """
        Extracts ttf fonts and copies them to local directory.
        The 'src' defined below is where the fotns have been downloaded
    """
    categories = read_names_from_google_pb_files()
    faces = read_files_for_faces()

    defs = []
    for name, cat in categories.items():
        key = name.lower()
        variants = faces[key]
        if not variants:
            variants = faces[key.replace(' ', '')]
        if not variants:
            variants = faces[key.replace(' ', '-')]
        while not variants and ' ' in key:
            v = key.rfind(' ')
            key = key[:v]
            variants = faces[key]
            if not variants:
                variants = faces[key.replace(' ', '')]

        if not variants:
            print('unfound:', name)
        else:
            defs.append((name, cat, variants))

    with open(FONT_DIR / '_INDEX.txt', 'wt') as f:
        for (name, cat, variants) in sorted(defs):
            ss = ";".join(f"{a}:{b}" for a, b in sorted(variants.items()))
            f.write(f"{name}|{cat}|{ss}\n")


def read_names_from_google_pb_files():
    src = Path('/Users/graham/Downloads/fonts-main')
    assert src.exists() and src.is_dir()
    pattern = re.compile('.*"(.*)".*')

    # Sigh. Why name files differently and make these special cases
    categories = {
        'Recursive-MonoCasual': 'monospace',
        'Recursive-MonoLinear': 'monospace',
        'Recursive-SansCasual': 'sans-serif',
        'Recursive-SansLinear': 'sans-serif',
    }

    for file_name in src.glob('**/*.pb'):
        with open(file_name, 'rt') as f:
            first_line = f.readline()
            if first_line.startswith('name:'):
                name = pattern.match(first_line).group(1)
                f.readline()
                f.readline()
                category = pattern.match(f.readline()).group(1).lower().replace('_', '-')
                categories[name] = category
    return categories


def generate_docs():
    lib = FontLibrary()
    families = sorted(lib.families())
    categories = "builtin sans-serif serif monospace handwriting display".split()
    all_faces = [f for f in families if f.contains_standard_faces()]
    print('Font Families with Regular, Bold, Italic and BoldItalic variations')
    print('==================================================================')
    print()
    for c in categories:
        title = f"Category: {c[0].upper()}{c[1:]}"
        print(title)
        print('-' * len(title))
        names = [f.name for f in all_faces if f.category == c]
        print(", ".join(names))
        print()

    print('Individual Fonts')
    print('================')
    for c in categories:
        title = f"Category: {c[0].upper()}{c[1:]}"
        print(title)
        print('-' * len(title))
        names = []
        for family in families:
            if family.category == c:
                if len(family.faces) > 1:
                    item = family.name + '[+' + str(', '.join(set(family.faces.keys())-{'Regular'})) + ']'
                    names.append(item)
                else:
                    names.append(family.name)

        print(", ".join(names))
        print()


def copy_temp():
    src = Path('/Users/graham/Desktop/gf_all')

    for f in src.glob('Noto*.ttf'):
        if not f.stem.endswith('-Regular') and not f.stem.endswith('-Bold') \
                and not f.stem.endswith('-Italic') and not f.stem.endswith('-BoldItalic'):
            f.unlink()


def remove_noto_non_canonical():
    lib = FontLibrary()
    families = sorted(f for f in lib.families() if f.category != 'builtin')
    with open(FONT_DIR / '_INDEX2.txt', 'wt') as f:
        for family in families:
            if family.name.startswith('Noto'):
                family.faces = {k: v for k, v in family.faces.items() if k in "Regular Bold Italic BoldItalic".split()}
            ss = ";".join(f"{a}:{b}" for a, b in sorted(family.faces.items()))
            f.write(f"{family.name}|{family.category}|{ss}\n")


if __name__ == '__main__':
    # copy_fonts_locally()
    # convert_variable_fonts()
    # build_family_info()
    generate_docs()
    # remove_noto_non_canonical()
    pass
