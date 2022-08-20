from dataclasses import dataclass
from typing import Iterable, Callable, List

from .content import Content, Error
from .content import PlacedContent, PlacedGroupContent
from .geom import Extent, Point, Spacing


@dataclass
class ColumnSpan:
    index: int
    left: int
    right: int

    @property
    def width(self) -> int:
        return self.right - self.left


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
                 items: Iterable[Content],
                 place_function: Callable[[Content, Extent], PlacedContent],
                 margin: Spacing, padding: Spacing):
        self.items = list(items)
        self.place_function = place_function
        self.margin = margin
        self.padding = padding

    def into_columns(self, width: int, ncol: int = 1) -> PlacedGroupContent:
        n_items = len(self.items)
        if n_items < ncol:
            raise ValueError('Cannot have more columns than items in a layout')
        spans = self.divide_width(width, ncol)

        best, best_score = self.find_best_allocation(width, spans, [0] * ncol, n_items, index=0)
        return best

    def find_best_allocation(self, width: int, spans, column_counts: List[int], remaining_items: int, index):
        n_spans = len(spans)
        if index == n_spans - 1:
            # For the last column, place all remaining items in it
            column_counts[index] = remaining_items
            assignment = assign_to_spans(column_counts, spans)
            return self.place_columnwise(width, assignment)

        # Try possible combinations at ths index
        max_in_this_column = remaining_items - n_spans + 1
        best, best_error = None, Error(9e99, 0, 0)
        for i in range(1, max_in_this_column):
            column_counts[index] = i
            trial, error = self.find_best_allocation(width, spans, column_counts, remaining_items - i, index + 1)
            if error.better(best_error):
                best, best_error = trial, error

        return best, best_error

    def place_into_assigned_columns(self, width, column_tuples, assigned_column):
        results = []
        current_column_idx = -1
        for i, item in enumerate(self.items):
            col_idx = assigned_column[i]
            if col_idx != current_column_idx:
                last_y = 0
                last_y_with_padding = self.margin.top
                current_column_idx = col_idx

            column_left = column_tuples[col_idx][0]
            column_right = column_tuples[col_idx][1]

            placed = self.place_function(item, Extent(column_right - column_left, -1))
            y = max(last_y_with_padding, last_y + self.padding.top)
            placed.location = Point(column_left, y)
            last_y = placed.bounds.bottom
            last_y_with_padding = last_y + self.padding.bottom
            results.append(placed)
        return PlacedGroupContent.from_items(results, Extent(width, -1), Extent(width, last_y + self.margin.bottom))

    def divide_width(self, width: int, ncol: int) -> List[ColumnSpan]:
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

    def place_columnwise(self, width: int, assignment: List[ColumnSpan]):
        results = []
        last_span = None
        for item, span in zip(self.items, assignment):
            if span != last_span:
                last_y = 0
                last_y_with_padding = self.margin.top
                last_span = span

            placed = self.place_function(item, Extent(span.width, -1))
            y = max(last_y_with_padding, last_y + self.padding.top)
            placed.location = Point(span.left, y)
            last_y = placed.bounds.bottom
            last_y_with_padding = last_y + self.padding.bottom
            results.append(placed)
        result = PlacedGroupContent.from_items(results, Extent(width, -1), Extent(width, last_y + self.margin.bottom))
        return result, self.score_for_columnwise_layout(result, assignment)

    def score_for_columnwise_layout(self, group: PlacedGroupContent, assignment: List[ColumnSpan]) -> Error:
        ncols = assignment[-1].index + 1
        column_bottom = [0] * ncols
        column_width = [0] * ncols
        for item, span in zip(group.placed_group, assignment):
            column_bottom[span.index] = max(column_bottom[span.index], item.bounds.bottom)
            column_width[span.index] = span.width

        lowest = max(column_bottom)
        wasted = sum((lowest - c) * width for c, width in zip(column_bottom, column_width))
        print(assignment, column_bottom, wasted)
        return group.error + Error(0, 0, wasted)
