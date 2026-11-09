#!/usr/bin/env python3
"""
Simulate every point of the phase map of Pearson (1993), Fig. 3 (data/pearson1993_fig3.csv),
for 200,000 time steps from the initial condition of the paper.

For each point results/map/<k>_<F>.npz holds U at t = 195,000, 199,750 and 200,000, and
the time at which the initial disturbance first reaches the edge of the box (V > 0.01 on
the outermost mesh rows and columns). Finished points are skipped.

  ./run_map.py [--processes N]
"""
import argparse
import csv
import os
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from grayscott import GrayScott, initial_state

ROOT = Path(__file__).resolve().parent
STEPS, CHUNK = 200_000, 250
SNAPSHOTS = (195_000, 199_750, 200_000)


def path_for(k, F):
    return ROOT / "results" / "map" / f"k{k:.4f}_F{F:.3f}.npz"


def simulate(point):
    index, k, F = point
    model = GrayScott(F, k, *initial_state(np.random.default_rng(index)))
    snapshots, t_edge = {}, np.nan
    while model.t < STEPS:
        model.step(CHUNK)
        v = model.v
        if np.isnan(t_edge) and max(v[0].max(), v[-1].max(), v[:, 0].max(), v[:, -1].max()) > 0.01:
            t_edge = model.t
        if model.t in SNAPSHOTS:
            snapshots[f"u{int(model.t)}"] = model.u.astype(np.float32)
    np.savez_compressed(path_for(k, F), t_edge=t_edge, **snapshots)
    return k, F, t_edge


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--processes", type=int, default=os.cpu_count())
    args = parser.parse_args()
    (ROOT / "results" / "map").mkdir(parents=True, exist_ok=True)
    with open(ROOT / "data" / "pearson1993_fig3.csv") as f:
        points = [(i, float(r["k"]), float(r["F"])) for i, r in enumerate(csv.DictReader(f))]
    todo = [p for p in points if not path_for(p[1], p[2]).exists()]
    print(f"{len(todo)} of {len(points)} points to simulate", flush=True)
    with Pool(args.processes) as pool:
        for k, F, t_edge in pool.imap_unordered(simulate, todo):
            print(f"k = {k:.4f}  F = {F:.3f}  disturbance reached the edge at t = {t_edge:g}",
                  flush=True)


if __name__ == "__main__":
    main()
