def along(a: tuple, b: tuple, r: float, limited: bool = True) -> tuple:
    """ Return a point a distance r from a to b"""
    d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    θ = r / d
    if limited:
        θ = min(1.0, max(0.0, θ))
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


def closed_shape(coords: list[tuple], radius) -> list[tuple]:
    # We find all corners and round them off
    # In this simple version a corner is 2 consecutive lines formign a corner p,q,r

    result = []
    n = len(coords)

    for idx, q in enumerate(coords):
        p = coords[(idx + n - 1) % n]
        r = coords[(idx + 1) % n]
        if len(p) == len(q) == len(r) == 2:
            pq = along(q, p, radius)
            qr = along(q, r, radius)
            result.append(pq)
            result.append((q[0], q[1], q[0], q[1], qr[0], qr[1]))
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
