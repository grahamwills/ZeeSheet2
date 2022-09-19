from dataclasses import dataclass
from typing import Iterable, Callable, List

from common import Extent, Point, Spacing
from common import configured_logger
from generate.pdf import PDF
from structure import StructureUnit
from .content import PlacedContent, PlacedGroupContent

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


class ColumnWidthChooser:
    def __init__(self, left: float, right: float, column_gap: float, ncols: int,
                 granularity: int = 10, min_width: int = 20):
        self.min_width = min_width
        self.granularity = granularity
        self.left = left
        self.right = right
        self.ncols = ncols
        self.column_gap = column_gap

    def divide_width(self, proportions: Iterable[float]):
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
            right = x + widths[i]
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
            for choices in self._divisions(width-v, n - 1):
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

    def into_columns(self, width: float, ncol: int = 1) -> PlacedGroupContent:
        n_items = len(self.items)
        left = self.margins.left
        right = self.margins.right
        chooser = ColumnWidthChooser(left, width - right, max(left, right), ncol)
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
        wasted = sum((lowest - c) * width for c, width in zip(column_bottom, column_width))

        group = PlacedGroupContent.from_items(results, Extent(width, lowest + self.margins.bottom))
        group.error.extra += wasted
        return group
