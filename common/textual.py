from __future__ import annotations

import re
from collections import defaultdict
from typing import List, Tuple


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
                value=''
            elif not c.isspace():
                # key with no value, we are starting a new key
                results.append((key, ''))
                key = c
                state = 'in key'
        elif state == 'after joiner':
            if c == "'" or c =='"':
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
            if c == "'" or c =='"':
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
