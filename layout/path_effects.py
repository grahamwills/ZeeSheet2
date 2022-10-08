def distance(a: tuple, b: tuple):
    d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    return d


def between(a: tuple, b: tuple, θ: float):
    """ Travel a fraction θ of the distance between a and b """
    return a[0] * (1 - θ) + b[0] * θ, a[1] * (1 - θ) + b[1] * θ


def search_for_last_move(coords: list[tuple], idx):
    # Look for the coords immediately after a close
    while idx > 0 and len(coords[idx - 1]) > 0:
        idx -= 1
    return coords[idx]


def search_for_next_close(coords: list[tuple], idx):
    # Look for the coords immediately before a close
    while idx > 0 and len(coords[idx - 1]) > 0:
        idx -= 1
    return coords[idx]


def parallel(a: tuple, b: tuple, c: tuple, d: tuple) -> bool:
    f = abs((a[1] - b[1]) * (c[0] - c[0]))
    g = abs((c[1] - d[1]) * (a[0] - b[0]))
    return abs(f - g) < 1e-3


def closed_shape(coords: list[tuple], radius) -> list[tuple]:
    # We find all corners and round them off
    # In this simple version a corner is 2 consecutive lines formign a corner p,q,r

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


def round_edges(coords: list[tuple], radius) -> list[tuple]:
    # We find all corners and round them off
    # In this simple version a corner is 2 consecutive lines formign a corner p,q,r

    result = []

    n = len(coords)

    first = 0
    while first < n:
        # fid the indics for the closed shape
        last = first
        while last < n and len(coords[last]) > 0:
            last += 1

        # Add closed shape [first, last)
        result += closed_shape(coords[first:last], radius)

        if last < n:
            result.append(coords[last])
        first = last + 1

    return result
