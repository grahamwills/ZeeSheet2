from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Generator

import reportlab.pdfgen.pathobject
from reportlab.graphics.shapes import Path

from common import Point


@dataclass
class Effect:
    name: str  # name
    needs_path_conversion: bool  # if true, rects need convertign to paths first
    needs_padding: bool  # space needed inside the usual frame
    size: float = None

    def sized(self, size: float) -> Effect:
        return Effect(self.name, self.needs_path_conversion, self.needs_padding, size)

    def padding(self) -> float:
        return self.size if self.needs_padding else 0

    def apply(self, coords: list[tuple], seed: int) -> Path:
        return Effects.make_from_coords(self, coords, seed)


class Effects:
    NONE = Effect('none', False, False)
    ROUNDED = Effect('rounded', False, False)
    ROUGH = Effect('rough', True, True)
    ALL = {e.name: e for e in (NONE, ROUNDED, ROUGH)}

    @classmethod
    def make_from_coords(cls, effect: Effect, coords: list[tuple], seed: int) -> Path:
        if effect.name == Effects.NONE.name:
            transformed = coords
        elif effect.name == Effects.ROUNDED.name:
            transformed = round_edges(coords, effect.size)
        elif effect.name == Effects.ROUGH.name:
            transformed = roughen_edges(coords, effect.size, seed)
        else:
            raise RuntimeError(f"Unknown effect '{effect.name}'")
        return toPath(transformed)


def round_edges(coords: list[tuple], radius) -> list[tuple]:
    # We find all corners and round them off
    # In this simple version a corner is 2 consecutive lines forming a corner p,q,r

    result = []
    for shape in closed_shapes(coords):
        result += round_closed_shape(shape, radius)
        result += tuple()  # close indicator
    return result


def roughen(points: list[Point], radius: float, rand: random.Random) -> list[Point]:
    DECAY = 0.45
    result = []
    n = len(points)
    v = 0
    for idx in range(0, n):
        p = points[(idx + n - 1) % n]
        q = points[idx]
        r = points[(idx + 1) % n]

        # Find a point 's' a distance 'radius' from q and perpendicular to the line (p,r)
        if abs(r.y - p.y) < 1e-4:
            # If p and r have the same y value
            s = Point(q.x, q.y + radius)
        else:
            slope = - (r.x - p.x) / (r.y - p.y)
            scale = radius * (1 + slope * slope) ** 0.5
            s = Point(q.x + 1 * scale, q.y + slope * scale)

        v1 = 9e99
        while abs(v1) > 1:
            v1 = v * (1 - DECAY) + rand.gauss(0, 0.5) * DECAY
        v = v1

        # v = math.sin(2*math.pi*idx/4)
        result.append(linear(q, s, v))
    return result


def roughen_edges(coords: list[tuple], radius: float, seed: int) -> list[tuple]:
    r = random.Random(seed)
    result = []
    for shape in closed_shapes(coords):
        points = flatten(shape, radius * 1.618)
        result += roughen(points, radius, r)
        result += tuple()  # close indicator
    return result


def closed_shapes(coords: list[tuple]) -> Generator[list[tuple], None, None]:
    """ Break coords into closed shapes """
    n = len(coords)
    first = 0
    while first < n:
        # fid the indices for the closed shape
        last = first
        while last < n and len(coords[last]) > 0:
            last += 1
        yield coords[first:last]
        first = last + 1


def distance(a: tuple, b: tuple):
    d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    return d


def between(a: tuple, b: tuple, θ: float):
    """ Travel a fraction θ of the distance between a and b """
    return a[0] * (1 - θ) + b[0] * θ, a[1] * (1 - θ) + b[1] * θ


def linear(a: Point, b: Point, t) -> Point:
    return a * (1 - t) + b * t


def bezier(a: Point, c1: Point, c2: Point, b: Point, t) -> Point:
    return (1 - t) ** 3 * a + 3 * t * (1 - t) * (1 - t) * c1 + 3 * t * t * (1 - t) * c2 + t ** 3 * b


def round_closed_shape(coords: list[tuple], radius) -> list[tuple]:
    # We find all corners and round them off
    # In this simple version a corner is 2 consecutive lines former a corner p,q,r

    result = []
    n = len(coords)

    for idx in range(0, len(coords)):
        p = coords[(idx + n - 1) % n]
        q = coords[idx]
        r = coords[(idx + 1) % n]

        if len(p) == len(q) == len(r) == 2:
            d1 = distance(p, q)
            d2 = distance(q, r)

            # Curve the corner
            result.append(q)
            rad = min(radius, d1 * 0.5, d2 * 0.5)
            θ1 = rad / d1
            θ2 = rad / d2
            a = between(q, p, θ1)
            b = between(q, p, θ1 * 0.55)
            c = between(q, r, θ2 * 0.55)
            d = between(q, r, θ2)
            result.append(a)
            result.append((b[0], b[1], c[0], c[1], d[0], d[1]))

        else:
            result.append(q)
    return result


def bezier_approx_length(p: Point, c1: Point, c2: Point, q: Point):
    # Use a seven point approximation (5 interior points)
    interpolated = [bezier(p, c1, c2, q, i / 6) for i in range(1, 6)]
    return sum(a.distance(b) for a, b in zip([p] + interpolated, interpolated + [q]))


def flatten(coords: list[tuple], step: float) -> list[Point]:
    """
        Reduce the coords given to points separated approximately the step size given .
        Because we always want all the end points, we might not be able to honor the step size exactly
    """
    result = []
    p = Point(coords[-1][-2], coords[-1][-1])
    for q in coords:
        if len(q) == 2:
            q = Point(q[0], q[1])
            d = p.distance(q)
            divisions = round(d / step)
            for i in range(1, divisions):
                result.append(linear(p, q, i / divisions))
        else:
            # A bezier
            c1 = Point(q[0], q[1])
            c2 = Point(q[2], q[3])
            q = Point(q[4], q[5])
            d = bezier_approx_length(p, c1, c2, q)
            divisions = round(d / step)
            for i in range(1, divisions):
                result.append(bezier(p, c1, c2, q, i / divisions))
        result.append(q)
        p = q
    return result


def toPath(coords: list[tuple]) -> Path:
    p = reportlab.pdfgen.pathobject.PDFPathObject()
    need_move = True
    for c in coords:
        m = len(c)
        if m == 0:
            p.close()
            need_move = True
        elif m == 2:
            if need_move:
                p.moveTo(*c)
                need_move = False
            else:
                p.lineTo(*c)
        elif m == 6:
            p.curveTo(*c)
        else:
            raise RuntimeError('Bad path specification')
    if not need_move:
        p.close()
    return p
