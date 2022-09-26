from functools import lru_cache
from typing import List


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
    counts = items_in_bins_counts(n, m)
    if counts <= limit or n < 2 * m:
        results = _pack_recursive(n, m)
        µ = n / m
        return sorted(results, key=lambda array: sum((v - µ) ** 2 for v in array))
    else:
        # Try with half the number of items
        smaller = items_in_bins_combinations(n // 2, m, limit)
        # Scale up the values
        results = []
        if n % 2:
            # Add the extra number to a different bin
            for i, vals in enumerate(smaller):
                new_vals = [2 * v for v in vals]
                results.append(new_vals)
                new_vals[i % m] += 1
        else:
            # Just scale up
            for vals in smaller:
                results.append([2 * v for v in vals])
        return results


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
