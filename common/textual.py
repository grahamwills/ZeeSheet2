from __future__ import annotations

import math
import numbers
import reprlib
from collections import defaultdict
from typing import List, Tuple, Any, Iterable


class MyRepr(reprlib.Repr):

    def __init__(self):
        super().__init__()
        self.maxlevel = 2
        self.maxtuple = 4
        self.maxlist = 4
        self.maxarray = 4
        self.maxdict = 4
        self.maxset = 4
        self.maxfrozenset = 4
        self.maxdeque = 4

    def repr_str(self, x: str, level: int) -> str:
        t = super().repr_str(x, level)
        return t[1:-1]


_REPR = MyRepr()


def name_of(v: Any):
    if v is None:
        return 'None'

    try:
        return name_of(v.name())
    except TypeError:
        return name_of(v.name)
    except AttributeError:
        pass

    if isinstance(v, numbers.Number):
        return to_str(v)

    if type(v) == str:
        return _REPR.repr(v).replace('...', '\u2026')

    if type(v) in {tuple, list}:
        parts = tuple(name_of(w) for w in v)
        return _REPR.repr(parts).replace('...', '\u2026')

    cl_name = v.__class__.__name__
    cl_id = id(v) % 10000
    return f"{cl_name}({cl_id:04d})"


def to_str(v: Any, places: int = 3):
    try:
        if math.isnan(v):
            return 'nan'
        if abs(v) > 1e6:
            millions = round(v / 1e6, places)
            int_m = int(millions)
            if int_m == millions:
                return str(int_m) + 'M'
            else:
                return str(millions) + 'M'
        v = round(v, places)
        i = int(v)
        if i == v:
            return str(i)
        else:
            return str(v)
    except TypeError:
        pass
    except OverflowError:
        return '\u221e' if v > 0 else '-\u221e'
    try:
        return format(v, f'0.{places}f')
    except:
        pass
    if isinstance(v, str):
        return v
    if isinstance(v, Iterable):
        return ', '.join(to_str(x, places) for x in v)

    return str(v)


class NGram:
    def __init__(self, txt: str, n: int = 3):
        self.n = n
        self.txt = txt
        self.counts = defaultdict(lambda: 0)
        for i in range(len(txt) - n + 1):
            ngram = txt[i:i + n]
            self.counts[ngram] += 1

    def __abs__(self) -> float:
        return max(1.0, sum(x * x for x in self.counts.values()) ** 0.5)

    def dot(self, other: NGram) -> float:
        if len(self.counts) > len(other.counts):
            return other.dot(self)
        else:
            return sum(x_val * other.counts.get(x_key) for x_key, x_val in self.counts.items() if x_key in other.counts)

    def similarity(self, other):
        if len(self.txt) < len(other.txt):
            return self.dot(other) / abs(other) ** 2
        else:
            return self.dot(other) / abs(other) / abs(self)


def parse(text: str) -> List[Tuple[str, str]]:
    results = []

    key = None
    value = ''
    state = 'outside'
    for c in text:
        if state == 'outside':
            if not c.isspace():
                key = c
                state = 'in key'
        elif state == 'in key':
            if c.isspace():
                state = 'before joiner'
            elif c == ':' or c == '=':
                state = 'after joiner'
                value = ''
            else:
                key += c
        elif state == 'before joiner':
            if c == ':' or c == '=':
                state = 'after joiner'
                value = ''
            elif not c.isspace():
                # key with no value, we are starting a new key
                results.append((key, ''))
                key = c
                state = 'in key'
        elif state == 'after joiner':
            if c == "'" or c == '"':
                state = 'in quote'
            elif not c.isspace():
                state = 'in value'
                value = c
        elif state == 'in value':
            if c.isspace():
                # finished value
                results.append((key, value))
                key = None
                value = ''
                state = 'outside'
            else:
                value += c
        elif state == 'in quote':
            if c == "'" or c == '"':
                # finished quote (and hence also finished value)
                results.append((key, value))
                key = None
                value = None
                state = 'outside'
            else:
                value += c

    if key:
        results.append((key, value))

    return results


if __name__ == '__main__':
    print(NGram('Freehand').similarity(NGram('This is a Freehand')))
