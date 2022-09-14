from __future__ import annotations

from collections import Counter, defaultdict


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
            return self.dot(other) / abs(other)**2
        else:
            return self.dot(other) / abs(other) / abs(self)



if __name__ == '__main__':
    print(NGram('Freehand').similarity(NGram('This is a Freehand')))
