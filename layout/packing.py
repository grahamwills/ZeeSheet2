from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable, Callable, List

from common import Extent, Point, Spacing, Rect
from common import configured_logger
from generate.pdf import PDF
from structure import StructureUnit
from .content import PlacedContent, PlacedGroupContent, Error

LOGGER = configured_logger(__name__)


@dataclass
class ColumnSpan:
    index: int
    left: float
    right: float

    @property
    def width(self) -> float:
        return self.right - self.left

    def __str__(self) -> str:
        return f"{self.left:0.1f}:{self.right:0.1f}"

    def __round__(self, n=None):
        return ColumnSpan(self.index, round(self.left, n), round(self.right, n))


@lru_cache
def _bin_counts(n: int, m: int) -> int:
    # Recursion formula for the counts
    if n < m:
        return 0
    elif n == m or m == 1:
        return 1
    else:
        return _bin_counts(n - 1, m - 1) + _bin_counts(n - 1, m)


def _items_into_buckets_combinations(item_count: int, bin_count: int) -> List[List[int]]:
    """ Generates all possible combinations of items into buckets"""
    if bin_count == 1:
        return [[item_count]]

    results = []
    for i in range(1, item_count - bin_count + 2):
        # i items in the first, recurse to find the possibilities for the other bins
        for remainder in items_into_buckets_combinations(item_count - i, bin_count - 1):
            results.append([i] + remainder)
    return results


def items_into_buckets_combinations(item_count: int, bin_count: int, limit: int = 1500) -> List[List[int]]:
    counts = _bin_counts(item_count, bin_count)
    if counts <= limit or item_count < 2 * bin_count:
        results = _items_into_buckets_combinations(item_count, bin_count)
        µ = item_count / bin_count
        return sorted(results, key=lambda array: sum((v - µ) ** 2 for v in array))
    else:
        # Try with half the number of items
        smaller = items_into_buckets_combinations(item_count // 2, bin_count, limit)
        # Scale up the values
        results = []
        if item_count % 2:
            # Add the extra number to a different bin
            for i, vals in enumerate(smaller):
                new_vals = [2 * v for v in vals]
                results.append(new_vals)
                new_vals[i % bin_count] += 1
        else:
            # Just scale up
            for vals in smaller:
                results.append([2 * v for v in vals])
        return results


@dataclass
class ColumnFit:
    width: float
    height: int = 0
    items: List[PlacedContent] = field(default_factory=lambda: [])
    clipped_items_count: int = 0


class ColumnPacker:
    def __init__(self, bounds: Rect, item_count: int, column_count: int, granularity: int = 10):
        self.n = item_count
        self.k = column_count
        self.bounds = bounds
        self.granularity = granularity

    def place_item(self, item_index: int, extent: Extent) -> PlacedContent:
        raise NotImplementedError('This method must be defined by an inheriting class')

    def margins_of_item(self, item_index: int) -> Spacing:
        raise NotImplementedError('This method must be defined by an inheriting class')

    def column_count_possibilities(self) -> List[List[int]]:
        return items_into_buckets_combinations(self.n, self.k)

    def _gap_horizontal(self) -> float:
        # Average the different gaps to give a general size for the gaps between columns
        total = sum(self.margins_of_item(i).horizontal for i in range(0, self.n))
        return total / self.n

    def column_width_possibilities(self) -> List[List[float]]:
        available_space = self.bounds.width - self._gap_horizontal() * (self.k - 1)

        # The total number of granularity steps we can fit in
        segment_count = int(available_space / self.granularity)
        segment_allocations = items_into_buckets_combinations(segment_count, self.k)
        results = []
        for i, seg_alloc in enumerate(segment_allocations):
            column_widths = [s * self.granularity for s in seg_alloc]
            # Add in the additional part for the extra granularity
            additional = available_space - sum(column_widths)
            column_widths[i % self.k] += additional
            results.append(column_widths)
        return results

    def better(self, a: List[ColumnFit], b: List[ColumnFit]):
        if b is None:
            return True
        clip_a = sum(fit.clipped_items_count for fit in a)
        clip_b = sum(fit.clipped_items_count for fit in b)
        if clip_a != clip_b:
            return clip_a < clip_b

        err_a = Error.aggregate(p.error for fit in a for p in fit.items)
        err_b = Error.aggregate(p.error for fit in b for p in fit.items)

        if err_a.better(err_b, ignore_unused=True):
            return True
        elif err_b.better(err_a, ignore_unused=True):
            return False

        µ1 = sum(fit.height for fit in a) / self.k
        µ2 = sum(fit.height for fit in b) / self.k

        v1 = sum((fit.height - µ1) ** 2 for fit in a)
        v2 = sum((fit.height - µ2) ** 2 for fit in b)
        if v1 != v2:
            return v1 < v2

        return err_a.unused_horizontal < err_b.unused_horizontal

    def make_fits(self, widths: List[float], counts: List[int]) -> List[ColumnFit]:
        at = 0
        height = self.bounds.height
        results = []
        for width, count in zip(widths, counts):
            fit = ColumnFit(width)
            y = 0
            for i in range(at, at + count):
                if y >= height:
                    fit.clipped_items_count += 1
                else:
                    placed = self.place_item(i, Extent(width, height - y))
                    placed.location = Point(0, y)
                    fit.height = placed.bounds.bottom
                    fit.items.append(placed)
            results.append(fit)
        return results

    def run(self):
        count_choices = self.column_count_possibilities()
        width_choices = self.column_width_possibilities()

        best = None

        # Naive
        for counts in count_choices:
            for widths in width_choices:
                trial = self.make_fits(widths, counts)
                if self.better(trial, best):
                    best = trial

        all = [placed for fit in best for placed in fit.items]
        return PlacedGroupContent.from_items(all)


class ColumnWidthChooser:
    def __init__(self, left: float, right: float, column_gap: float, ncols: int,
                 granularity: int = 10, min_width: int = 20):
        self.min_width = min_width
        self.granularity = granularity
        self.left = left
        self.right = right
        self.ncols = ncols
        self.column_gap = column_gap

    def divide_width(self, proportions: Iterable[float]) -> List[ColumnSpan]:
        tot = sum(proportions)
        proportions = [p / tot for p in proportions]
        assert len(proportions) == self.ncols

        width = self.right - self.left
        available = width - (self.ncols - 1) * self.column_gap
        column_width = available / self.ncols

        if column_width < 1:
            raise RuntimeError(f"Cannot divide space of size {width} into "
                               f"{self.ncols} columns with gasp {self.column_gap}")

        widths = [available * p for p in proportions]

        x = self.left
        result = []
        for i in range(0, self.ncols):
            left = x
            right = left + widths[i]
            result.append(ColumnSpan(i, left, right))
            x = right + self.column_gap
        return result

    def divisions(self) -> List[List[float]]:
        """ Choose column divisions to attempt for given granularity"""
        if self.ncols == 1:
            return [[1]]

        width = self.right - self.left
        divisions = self._divisions(width, self.ncols)
        return divisions

    def _divisions(self, width: float, n: int) -> List[List[float]]:
        min = int(self.min_width)
        max = int(width - self.min_width)
        if n == 2:
            return [[v, width - v] for v in range(min, max, self.granularity)]

        # Recurse
        result = []
        for v in range(min, max, self.granularity):
            for choices in self._divisions(width - v, n - 1):
                result.append([float(v)] + choices)
        return result


def assign_to_spans(column_counts: List[int], spans: List[ColumnSpan]) -> List[ColumnSpan]:
    result = []
    current_column = 0
    assigned_to_this_column = 0
    for i in range(sum(column_counts)):
        if assigned_to_this_column == column_counts[current_column]:
            assigned_to_this_column = 0
            current_column += 1
        assigned_to_this_column += 1
        result.append(spans[current_column])
    return result


class Packer:
    """Packs rectangular content into a given space"""

    def __init__(self, items: Iterable[type(StructureUnit)],
                 place_function: Callable[[type(StructureUnit), Extent, PDF], PlacedContent], margins: Spacing,
                 pdf: PDF = None):
        self.items = list(items)
        self.place_function = place_function
        self.pdf = pdf
        self.margins = margins

    def into_columns(self, width: float, ncol: int = 1, equal: bool = False) -> PlacedGroupContent:
        n_items = len(self.items)
        left = self.margins.left
        right = self.margins.right
        chooser = ColumnWidthChooser(left, width - right, max(left, right), ncol)

        if equal:
            spans = chooser.divide_width([1] * ncol)
            return self.find_best_allocation(width, spans, [0] * ncol, n_items, index=0)

        divisions = chooser.divisions()

        best = None
        for div in divisions:
            spans = chooser.divide_width(div)
            group = self.find_best_allocation(width, spans, [0] * ncol, n_items, index=0)
            if group.better(best):
                best = group
        return best

    def find_best_allocation(self, width: float, spans, column_counts: List[int], remaining_items: int,
                             index) -> PlacedGroupContent:
        n_spans = len(spans)
        if index == n_spans - 1:
            # For the last column, place all remaining items in it
            column_counts[index] = remaining_items
            assignment = assign_to_spans(column_counts, spans)
            return self.place_columnwise(width, assignment)

        # Try all the  counts of items that are legal at this location
        max_in_this_column = remaining_items - (n_spans - index) + 1
        best = None
        for i in range(1, max_in_this_column + 1):
            column_counts[index] = i
            trial = self.find_best_allocation(width, spans, column_counts, remaining_items - i, index + 1)
            if trial.better(best):
                best = trial

        return best

    def divide_width(self, width: float, ncol: int) -> List[ColumnSpan]:
        """ Divide space evenly, taking into account margins """
        left = self.margins.left
        right = self.margins.right
        chooser = ColumnWidthChooser(left, width - right, max(left, right), ncol)
        return chooser.divide_width([1] * ncol)

    def place_columnwise(self, width: float, assignment: List[ColumnSpan]) -> PlacedGroupContent:
        row_gap = max(self.margins.top, self.margins.bottom)

        results = []
        last_span = None
        next_top = self.margins.top
        for item, span in zip(self.items, assignment):
            if span != last_span:
                next_top = self.margins.top
                last_span = span

            placed = self.place_function(item, Extent(span.width, 9e99), self.pdf)
            placed.location = Point(span.left, next_top)
            results.append(placed)
            next_top = placed.bounds.bottom + row_gap

        ncols = assignment[-1].index + 1
        column_bottom = [0] * ncols
        column_width = [0] * ncols
        for item, span in zip(results, assignment):
            column_bottom[span.index] = max(column_bottom[span.index], item.bounds.bottom)
            column_width[span.index] = span.width

        lowest = max(column_bottom)

        group = PlacedGroupContent.from_items(results, Extent(width, lowest + self.margins.bottom))
        return group
