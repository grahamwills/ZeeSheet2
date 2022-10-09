import random
from typing import Generator

from common import Point


def round_edges(coords: list[tuple], radius) -> list[tuple]:
    # We find all corners and round them off
    # In this simple version a corner is 2 consecutive lines forming a corner p,q,r

    result = []
    for shape in closed_shapes(coords):
        result += round_closed_shape(shape, radius)
        result += tuple()  # close indicator
    return result


def roughen(points: list[Point], radius: float, rand: random.Random) -> list[Point]:
    DECAY = 0.5
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
            v1 = v * (1-DECAY) + rand.gauss(0, 0.25) * DECAY
        v = v1
        result.append(linear(q, s, v))
    return result


def roughen_edges(coords: list[tuple], radius:float, seed:int) -> list[tuple]:
    r = random.Random(seed)
    result = []
    for shape in closed_shapes(coords):
        points = flatten(shape, radius)
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

#
#     def __init__(self, canvas: Canvas, method: str = 'rough', σ=1):
#         """
#             Class used to add a rough effect to drawing constructs
#             :param str method:'rough' or 'teeth'
#             :param float σ: The size of the roughness effect. The range (0, 3] is generally good
#         """
#
#         self.canvas = canvas
#         self.method = method
#         self.σ = σ / 2
#         if method == 'teeth':
#             self.step = self.σ * 10
#         else:
#             self.step = 10
#         self.rand = random.Random()
#
#     # noinspection PyProtectedMember
#     def mangle(self, path: PDFPathObject) -> PDFPathObject:
#         path._code = self._mangle_path_code(path._code)
#         return path
#
#     def roughen_path(self, path: PDFPathObject) -> PDFPathObject:
#         return self.mangle(copy(path))
#
#     def _mangle_path_code(self, path: Sequence[str]) -> List[str]:
#         self._offset = Point(*self.canvas.absolutePosition(0, 0))
#         result = []
#         start = None
#         last = None
#         for term in path:
#             parts = term.split()
#             code = parts[-1]
#             coords = [Point(float(parts[i]), float(parts[i + 1])) for i in range(0, len(parts) - 1, 2)]
#             if code == 'm':
#                 if self.method == 'teeth':
#                     start = last = coords[0]
#                 else:
#                     start = last = self.jitter(coords[0])
#                 result.append(join(code, last))
#             elif not coords and code not in {'h', 's', 'b', 'b*'}:
#                 # Drawing operations that do not close the path
#                 result.append(code)
#             else:
#                 if code == 'l':
#                     f = functools.partial(linear, last, coords[0])
#                 elif code in {'h', 's', 'b', 'b*'}:
#                     # These all close the path
#                     f = functools.partial(linear, last, start)
#                 elif code == 'c':
#                     f = functools.partial(bezier, last, coords[0], coords[1], coords[2])
#                 elif code == 'v':
#                     f = functools.partial(bezier, last, last, coords[0], coords[1])
#                 elif code == 'y':
#                     f = functools.partial(bezier, last, coords[0], coords[1], coords[1])
#                 else:
#                     raise ValueError("Unhandled PDF path code: '%s'" % code)
#
#                 if self.method == 'teeth':
#                     pts, _ = self.interpolate(f, min_steps=1)
#                     for pt in pts:
#                         result += self.teeth(last, pt)
#                         last = pt
#                 else:
#                     pts, factor = self.interpolate(f)
#                     self.σ /= factor
#                     for pt in pts:
#                         p = self.jitter(pt)
#                         result.append(join('l', p))
#                     last = pts[-1]
#                     self.σ *= factor
#
#                 # Need to add close after the other interpolations
#                 if code == 'h':
#                     result.append('h')
#
#         return result
#
#     def jitter(self, p: Point):
#         # Randomize the seed based on the absolute location, so any new values at this location get the same amount
#         self.rand.seed(round(p + self._offset))
#         return Point(p[0] + self._noise(), p[1] + self._noise())
#
#     def _noise(self):
#         return min(2 * self.σ, max(-2 * self.σ, self.rand.gauss(0, self.σ)))
#
#     def interpolate(self, func: Callable, min_steps=5) -> (Sequence[Point], float):
#         v = [func(i / 5) for i in range(0, 6)]
#         d = sum(abs(v[i] - v[i + 1]) for i in range(0, 5))
#         if d < 1:
#             return v[:-1:], 1
#         steps = max(min_steps, round(d / self.step))
#
#         # This is the factor by which our steps are smaller than expected
#         # We use this to reduce the sigma value proportionally
#         factor = steps * self.step / d
#
#         return [func(i / steps) for i in range(1, steps + 1)], factor
#
#     def teeth(self, a: Point, b: Point) -> List[str]:
#         θ, d = (b - a).to_polar()
#         c1 = 0.95 * a + 0.05 * b
#         c2 = 0.55 * a + 0.45 * b
#         c3 = 0.45 * a + 0.55 * b
#         c4 = 0.05 * a + 0.95 * b
#         v = Point.from_polar(θ - math.pi / 2, self.σ)
#         return [
#             join('l', c1 + v),
#             join('l', c2 + v),
#             join('l', c3 - v),
#             join('l', c4 - v),
#             join('l', b),
#         ]
#
#
#
