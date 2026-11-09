#!/usr/bin/env python3
"""
Run the simulations behind Figs. 2a and 2b of Vicsek et al. (1995), with two protocols:

  fig2a, fig2b       an independent run from random initial conditions for every point;
                     block means of v_a over 12,000 steps (blocks of 500)
  anneal2a, grow2b   the paper's protocol: one continuing run per system in which the
                     noise is gradually decreased (Fig. 2a), or the density increased by
                     adding particles (Fig. 2b); 2,000 steps per value, blocks of 100

Rows are appended to results/<sweep>.csv as runs finish; finished runs are skipped
when the script is restarted.

  ./run_experiments.py                 # all four
  ./run_experiments.py anneal2a        # one
"""
import argparse
import csv
import os
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from vicsek import density_sweep, noise_sweep, order_parameter_series

ROOT = Path(__file__).resolve().parent
STEPS, BLOCK = 12000, 500
STAGE, STAGE_BLOCK = 2000, 100     # protocol sweeps: steps per value, block length
SWEEPS = ["fig2a", "fig2b", "anneal2a", "grow2b"]


def runs(n):
    """Independent runs per point: 5 as in the paper near the transition, 2 for the two
    largest systems, whose order parameter fluctuates little between runs."""
    return 5 if n <= 400 else 2

# Fig. 2a: v_a versus noise at density 4 for five system sizes (caption of Fig. 2).
FIG2A_SIZES = [(40, 3.1), (100, 5.0), (400, 10.0), (4000, 31.6), (10000, 50.0)]
FIG2A_NOISE = np.round(np.r_[np.arange(0.0, 2.0, 0.2), np.arange(2.0, 3.6, 0.1),
                             np.arange(3.6, 5.01, 0.2)], 2)
# Fig. 2b: v_a versus density at noise 2.0 in a box of size 20.
FIG2B_BOX, FIG2B_NOISE = 20.0, 2.0
FIG2B_DENSITY = np.round(np.r_[np.arange(0.2, 3.3, 0.2), np.arange(4.0, 9.7, 0.8)], 2)


def jobs(sweep):
    if sweep == "fig2a":
        for n, box in FIG2A_SIZES:
            for eta in FIG2A_NOISE:
                yield n, box, float(eta)
    else:
        for rho in FIG2B_DENSITY:
            yield int(round(rho * FIG2B_BOX ** 2)), FIG2B_BOX, FIG2B_NOISE


def simulate(task):
    sweep, n, box, eta, run = task
    seed = np.random.SeedSequence([SWEEPS.index(sweep), n, round(eta * 1000), run])
    return task, order_parameter_series(n, box, eta, STEPS, BLOCK, seed)


def simulate_protocol(task):
    """Rows (n, box, eta, run, t_end, va) of one continuing sweep."""
    sweep, n, box, run = task
    seed = np.random.SeedSequence([SWEEPS.index(sweep), n, run])
    rows = []
    if sweep == "anneal2a":
        noises = [float(e) for e in FIG2A_NOISE[::-1]]          # from 5.0 down to 0
        for eta, blocks in zip(noises, noise_sweep(n, box, noises, STAGE, STAGE_BLOCK, seed)):
            rows += [(n, box, eta, run, k * STAGE_BLOCK, va) for k, va in enumerate(blocks, 1)]
    else:
        counts = [int(round(rho * FIG2B_BOX ** 2)) for rho in FIG2B_DENSITY]
        for count, blocks in zip(counts, density_sweep(FIG2B_BOX, counts, FIG2B_NOISE, STAGE,
                                                        STAGE_BLOCK, seed)):
            rows += [(count, box, FIG2B_NOISE, run, k * STAGE_BLOCK, va) for k, va in enumerate(blocks, 1)]
    return task, rows


def run_protocol(sweep, processes):
    path = ROOT / "results" / f"{sweep}.csv"
    done = set()
    if path.exists():
        with open(path) as f:
            done = {(float(r["box"]), int(r["run"])) for r in csv.DictReader(f)}
    systems = FIG2A_SIZES if sweep == "anneal2a" else [(FIG2B_DENSITY[-1] * FIG2B_BOX ** 2, FIG2B_BOX)]
    repeats = lambda n: 5 if sweep == "grow2b" else runs(n)     # the density sweep is cheap
    tasks = [(sweep, int(n), box, run) for n, box in systems for run in range(repeats(n))
             if (box, run) not in done]
    tasks.sort(key=lambda t: -t[1])
    print(f"{sweep}: {len(tasks)} sweeps to do", flush=True)
    new_file = not path.exists()
    with open(path, "a", newline="") as f, Pool(processes) as pool:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["n", "box", "eta", "run", "t_end", "va"])
        for _, rows in pool.imap_unordered(simulate_protocol, tasks):
            writer.writerows((n, box, eta, run, t, f"{va:.5f}") for n, box, eta, run, t, va in rows)
            f.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sweeps", nargs="*", choices=SWEEPS, help="default: all")
    parser.add_argument("--processes", type=int, default=os.cpu_count())
    args = parser.parse_args()

    (ROOT / "results").mkdir(exist_ok=True)
    for sweep in args.sweeps or SWEEPS:
        if sweep in ("anneal2a", "grow2b"):
            run_protocol(sweep, args.processes)
            continue
        path = ROOT / "results" / f"{sweep}.csv"
        done = set()
        if path.exists():
            with open(path) as f:
                done = {(int(r["n"]), float(r["box"]), float(r["eta"]), int(r["run"]))
                        for r in csv.DictReader(f)}
        tasks = [(sweep, n, box, eta, run) for n, box, eta in jobs(sweep) for run in range(runs(n))
                 if (n, box, eta, run) not in done]
        tasks.sort(key=lambda t: -t[1])  # largest systems first
        print(f"{sweep}: {len(tasks)} runs to do", flush=True)
        new_file = not path.exists()
        with open(path, "a", newline="") as f, Pool(args.processes) as pool:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["n", "box", "eta", "run", "t_end", "va"])
            for (_, n, box, eta, run), blocks in pool.imap_unordered(simulate, tasks):
                for k, va in enumerate(blocks, start=1):
                    writer.writerow([n, box, eta, run, k * BLOCK, f"{va:.5f}"])
                f.flush()


if __name__ == "__main__":
    main()
