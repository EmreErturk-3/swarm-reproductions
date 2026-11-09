#!/usr/bin/env python3
"""
Fit the illuminance field of Bodi et al. (2009) to the sensor profile of Fig. 4B.

Model, with distances d_L and d_S (in patches) to the light and shadow spot:
    E = clip(E_ambient + b * (g(d_L) - g(d_S)), 0, E_max),   e = min(theta * E, e_max)
The spot centres (x = -14 and +14 patches, y = 0) are read off Fig. 4. Three
kernels g are compared; the best one is used in src/beeclust_loop_functions.cpp.
"""
import csv
import math
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "bodi2009_fig4b.csv"

THETA, E_SENSOR_MAX = 0.18, 180.0  # Table 1
E_AMBIENT, E_MAX = 500.0, 1000.0   # Sec. 2
X_LIGHT, X_SHADOW = -14.0, 14.0

KERNELS = {
    "exponential": lambda d, c: math.exp(-d / c),
    "gaussian": lambda d, c: math.exp(-d * d / (2.0 * c * c)),
    "inverse": lambda d, c: c / (d + c),
}


def load_points():
    with open(DATA) as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        return [(float(r["x_patches"]), float(r["sensor_value"])) for r in rows]


def sensor_value(x, b, c, kernel):
    lux = E_AMBIENT + b * (kernel(abs(x - X_LIGHT), c) - kernel(abs(x - X_SHADOW), c))
    lux = min(max(lux, 0.0), E_MAX)
    return min(THETA * lux, E_SENSOR_MAX)


def rmse(points, b, c, kernel):
    return math.sqrt(sum((sensor_value(x, b, c, kernel) - e) ** 2 for x, e in points) / len(points))


def fit(points, kernel):
    """Coarse-to-fine grid search over amplitude b [lux] and length scale c [patches]."""
    b_lo, b_hi, c_lo, c_hi = 10.0, 5000.0, 0.1, 20.0
    for _ in range(6):
        grid = [(b_lo + i * (b_hi - b_lo) / 40, c_lo + j * (c_hi - c_lo) / 40)
                for i in range(41) for j in range(41)]
        b, c = min(grid, key=lambda p: rmse(points, p[0], p[1], kernel))
        db, dc = (b_hi - b_lo) / 20, (c_hi - c_lo) / 20
        b_lo, b_hi, c_lo, c_hi = max(b - db, 1.0), b + db, max(c - dc, 0.01), c + dc
    return b, c, rmse(points, b, c, kernel)


def main():
    points = load_points()
    for name, kernel in KERNELS.items():
        b, c, error = fit(points, kernel)
        print(f"{name:12s} b = {b:7.1f} lux   c = {c:5.2f} patches   RMSE = {error:4.2f}")


if __name__ == "__main__":
    main()
