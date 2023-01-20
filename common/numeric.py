from functools import lru_cache
from typing import List

import common

LOGGER = common.configured_logger(__name__)
_r_i = 0
_r_array = [0.5, 0.64285714, 0.35714286, 0.07142857, 0.78571429, 0.21428571]


class R:
    def __init__(self):
        self.i = 0
        self.array = [0.5, 0.64285714, 0.35714286, 0.07142857, 0.78571429, 0.21428571]

    def r(self) -> float:
        """ Deterministic 'random' function just cycles in sevenths"""
        self.i = (self.i + 1) % 7
        return self.array[_r_i]


def variance(a: List[float]) -> float:
    n = len(a)
    µ = sum(a) / n
    return sum((v - µ) * (v - µ) for v in a) / n


@lru_cache(maxsize=10000)
def items_in_bins_counts(n: int, m: int) -> int:
    """
        Returns the number of ways to split a list of n items across m bins.
        
        At least one item must be placed in each bin and the order must be maintained,
        so the first item must be in the first bin, and the last item must be in the last bin,
        as an example.
        
        :param n: number of items
        :param m: number of bins
    """
    if n < m:
        return 0
    elif n == m or m == 1:
        return 1
    else:
        return items_in_bins_counts(n - 1, m - 1) + items_in_bins_counts(n - 1, m)


def items_in_bins_combinations(n: int, m: int, limit: int = 100) -> List[List[int]]:
    """
        Returns a list of the different ways we can split a list of n items across m bins.
        
        At least one item must be placed in each bin and the order must be maintained,
        so the first item must be in the first bin, and the last item must be in the last bin,
        as an example.
        
        If too many combinations result, then we do not return all combinations, but instead use packets
        of 2,4,8 etc. items to place in each bin 
        
        :param n: number of items
        :param m: number of bins
        :param limit: maximum number of combinations to allow before starting to packet items together
    """

    n1 = n
    while True:
        counts = items_in_bins_counts(n1, m)
        if counts <= limit:
            break
        n1 -= 1
        LOGGER.fine("Too many combinations {}; increasing packing factor to {:1.2f}", counts, n / n1)

    results = _pack_recursive(n1, m)

    if n != n1:
        # We need to un-factor the items. For fractional parts we use a random allocation, but with a fixed seed so that
        # it remains repeatable
        r = R()
        results = [_un_fractional(combo, n, n1, r) for combo in results]

    µ = n / m
    return sorted(results, key=lambda array: sum((v - µ) ** 2 for v in array))


def _pack_recursive(item_count: int, bin_count: int) -> List[List[int]]:
    """ Generates all possible combinations of items into buckets"""
    if bin_count == 1:
        return [[item_count]]

    results = []
    for i in range(1, item_count - bin_count + 2):
        # i items in the first, recurse to find the possibilities for the other bins
        for remainder in items_in_bins_combinations(item_count - i, bin_count - 1):
            results.append([i] + remainder)
    return results


def _un_fractional(combo: list[int], n: int, used: int, r: R) -> list[int]:
    owed = 0.0  # Running total of the count owed
    result = [0] * len(combo)
    for i, c in enumerate(combo):
        owed += c * n / used
        result[i] = int(owed)
        if r.r() < owed - result[i]:
            result[i] += 1
        owed -= result[i]
    assert sum(result) == n
    return result
