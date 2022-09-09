import warnings
from dataclasses import dataclass
from typing import Iterable, Callable, List, Any

from common import Extent, Point, Spacing
from common import configured_logger
from generate.pdf import PDF
from structure import StructureUnit, description
from .content import PlacedContent, PlacedGroupContent

LOGGER = configured_logger(__name__)


@dataclass
class ColumnSpan:
    index: int
    left: int
    right: int

    @property
    def width(self) -> int:
        return self.right - self.left

    def __str__(self) -> str:
        return f"{self.left}:{self.right}"


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

    def __init__(self,
                 represents: Any,
                 items: Iterable[type(StructureUnit)],
                 place_function: Callable[[type(StructureUnit), Extent, PDF], PlacedContent],
                 margin: Spacing, padding: Spacing,
                 pdf: PDF = None):
        self.represents = represents
        self.items = list(items)
        self.place_function = place_function
        self.pdf = pdf
        self.margin = margin
        self.padding = padding

    def into_columns(self, width: float, ncol: int = 1) -> PlacedGroupContent:
        n_items = len(self.items)
        spans = self.divide_width(width, ncol)

        ss = ", ".join(str(s) for s in spans)
        LOGGER.debug(f"Packing '{description(self.represents, short=True)}' into columns: {ss}")

        group = self.find_best_allocation(width, spans, [0] * ncol, n_items, index=0)

        for c in group.group:
            LOGGER.debug(f".. placed {c.name()} into {c.bounds}")

        return group

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
        """Divide space evenly, taking into account paddings and margins"""
        left_inset = max(self.margin.left, self.padding.left)
        right_inset = max(self.margin.right, self.padding.right)

        column_spacing = max(self.padding.left, self.padding.right)
        available = width - left_inset - right_inset - (ncol - 1) * column_spacing

        column_width = available / ncol

        if column_width < 1:
            msg = f"Cannot divide space of size {width} into {ncol} columns with given padding and margins"
            raise RuntimeError(msg)

        result = []
        for i in range(0, ncol):
            left = left_inset + (column_width + column_spacing) * i
            right = left + column_width
            result.append(ColumnSpan(i, round(left), round(right)))
        return result

    # noinspection PyUnboundLocalVariable
    def place_columnwise(self, width: float, assignment: List[ColumnSpan]) -> PlacedGroupContent:
        results = []
        last_span = None
        for item, span in zip(self.items, assignment):
            if span != last_span:
                last_y = 0
                last_y_with_padding = self.margin.top
                last_span = span

            placed = self.place_function(item, Extent(span.width, 9e99), self.pdf)
            y = max(last_y_with_padding, last_y + self.padding.top)
            placed.location = Point(span.left, y)
            last_y = placed.bounds.bottom
            last_y_with_padding = last_y + self.padding.bottom
            results.append(placed)

        ncols = assignment[-1].index + 1
        column_bottom = [0] * ncols
        column_width = [0] * ncols
        for item, span in zip(results, assignment):
            column_bottom[span.index] = max(column_bottom[span.index], item.bounds.bottom)
            column_width[span.index] = span.width

        lowest = max(column_bottom)
        wasted = sum((lowest - c) * width for c, width in zip(column_bottom, column_width))

        return PlacedGroupContent.from_items(self.represents,
                                             results,
                                             Extent(width, last_y + self.margin.bottom),
                                             wasted)
