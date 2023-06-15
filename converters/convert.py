from typing import List, Tuple

import xmltodict

from converters import dnd4e
from main import Document

RULES = None


def convert(text: str) -> Tuple[str, List[str]]:
    global RULES
    if RULES is None:
        RULES = dnd4e.read_rules_elements()

    errors = []
    try:
        xml_dict = xmltodict.parse(text, process_namespaces=True)
    except:
        errors.append('The document was not a valid XML document, which is the required format for D&D4E')
        return text, errors
    try:
        dnd = dnd4e.DnD4E(xml_dict, RULES)
        result = dnd.to_rst()
    except Exception as ex:
        errors.append('Error encountered while reading the file: ' + str(ex))
        return text, errors

    try:
        doc = Document(result)
        return doc.prettified(100), errors
    except Exception as ex:
        errors.append('File was converted, but has errors: ' + str(ex))
        return result, errors
