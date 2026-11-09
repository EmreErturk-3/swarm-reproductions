#!/usr/bin/env python3
"""
The two benchmarks of Stanley & Miikkulainen (2002) with full NEAT:

  xor   Sec. 4.2: 100 runs; paper: 32 generations, 4,755 evaluations (s.d. 2,553),
        2.35 hidden nodes (s.d. 1.11), 7.48 enabled connections, no failure,
        worst run 13,459 evaluations, one hidden node in 22 of 100 runs.
  dpv   Sec. 4.3.2, double pole balancing with velocities: 120 runs;
        paper: 3,600 evaluations (s.d. 2,704), 24 generations, 0-4 hidden nodes.

Each run writes one line to results/<task>.csv; finished runs are skipped.

  ./experiments.py xor
  ./experiments.py dpv
"""
import argparse
import csv
import math
import os
import statistics
from multiprocessing import Pool
from pathlib import Path

from neat import Parameters, evolve, minimal_genome

ROOT = Path(__file__).resolve().parent
RUNS = {"xor": 100, "dpv": 120}
MAX_GENERATIONS = 1000

# ------------------------------------------------------------------------------ XOR

XOR_CASES = [((0.0, 0.0), 0.0), ((0.0, 1.0), 1.0), ((1.0, 0.0), 1.0), ((1.0, 1.0), 0.0)]


def xor_fitness(network):
    """Sec. 4.2: fitness (4 - summed error)^2; solved if every output is on the right
    side of 0.5 (C++ xor_evaluate)."""
    outputs = [network.activate([a, b, 1.0])[0] for (a, b), _ in XOR_CASES]
    error = sum(abs(o - t) for o, (_, t) in zip(outputs, XOR_CASES))
    solved = all((o >= 0.5) == (t == 1.0) for o, (_, t) in zip(outputs, XOR_CASES))
    return (4.0 - error) ** 2, solved


# ------------------------------------------------------------- double pole balancing

class DoublePole:
    """Cart with two poles (Wieland 1991), as in the C++ release (CartPole):
    RK4 with step 0.01 s, a force every 0.02 s in [-10, 10] N, half-lengths 0.5 m and
    0.05 m, masses 0.1 kg and 0.01 kg, cart 1 kg, track +-2.4 m, failure beyond 36 deg."""
    GRAVITY, CART_MASS, MUP = -9.8, 1.0, 0.000002   # pole hinge friction; no cart friction
    POLES = ((0.5, 0.1), (0.05, 0.01))   # (half-length, mass)
    TAU, FORCE, TRACK, FAILURE = 0.01, 10.0, 2.4, 0.628329
    LONG_POLE_START = math.radians(1.0)  # Sec. 4.3.1 (the C++ release uses 0.07 rad)

    def __init__(self):
        self.state = [0.0, 0.0, self.LONG_POLE_START, 0.0, 0.0, 0.0]

    def derivatives(self, s, force):
        x_acc_num, mass = force, self.CART_MASS
        terms = []
        for (half, m), theta, omega in zip(self.POLES, s[2::2], s[3::2]):
            ml = half * m
            friction = self.MUP * omega / ml
            g_sin = self.GRAVITY * math.sin(theta)
            cos = math.cos(theta)
            x_acc_num += ml * omega * omega * math.sin(theta) + 0.75 * m * cos * (friction + g_sin)
            mass += m * (1 - 0.75 * cos * cos)
            terms.append((half, cos, g_sin, friction))
        x_acc = x_acc_num / mass
        d = [s[1], x_acc]
        for (half, cos, g_sin, friction), omega in zip(terms, s[3::2]):
            d += [omega, -0.75 * (x_acc * cos + g_sin + friction) / half]
        return d

    def step(self, output):
        force = (output - 0.5) * self.FORCE * 2
        for _ in range(2):  # two RK4 steps of 0.01 s per action
            s = self.state
            k1 = self.derivatives(s, force)
            k2 = self.derivatives([a + self.TAU / 2 * b for a, b in zip(s, k1)], force)
            k3 = self.derivatives([a + self.TAU / 2 * b for a, b in zip(s, k2)], force)
            k4 = self.derivatives([a + self.TAU * b for a, b in zip(s, k3)], force)
            self.state = [a + self.TAU / 6 * (b + 2 * c + 2 * d + e)
                          for a, b, c, d, e in zip(s, k1, k2, k3, k4)]

    def failed(self):
        x, _, t1, _, t2, _ = self.state
        return abs(x) > self.TRACK or abs(t1) > self.FAILURE or abs(t2) > self.FAILURE


DPV_STEPS = 100_000  # 30 min of simulated time


def dpv_fitness(network):
    """Sec. 4.3.2: fitness is the number of steps both poles stay up; solved at 100,000.
    Inputs are scaled as in the C++ release; its bias input is 0.5."""
    cart = DoublePole()
    for step in range(1, DPV_STEPS + 1):
        x, v, t1, w1, t2, w2 = cart.state
        cart.step(network.activate([x / 4.8, v / 2, t1 / 0.52, w1 / 2, t2 / 0.52, w2 / 2, 0.5])[0])
        if cart.failed():
            return float(step), False
    return float(DPV_STEPS), True


# --------------------------------------------------------------------------- runner

TASKS = {"xor": (xor_fitness, 3), "dpv": (dpv_fitness, 7)}


def run(task_and_seed):
    task, seed = task_and_seed
    fitness, n_inputs = TASKS[task]
    solver, generation, evaluations = evolve(minimal_genome(n_inputs), fitness, Parameters(),
                                             MAX_GENERATIONS, seed)
    if solver is None:
        return seed, False, generation, evaluations, "", ""
    return seed, True, generation, evaluations, len(solver.hidden), len(solver.enabled())


def summarise(task, path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    solved = [r for r in rows if r["solved"] == "True"]
    evaluations = [int(r["evaluations"]) for r in solved]
    hidden = [int(r["hidden_nodes"]) for r in solved]
    print(f"\n{task}: {len(rows)} runs, {len(rows) - len(solved)} failures "
          f"(no solution within {MAX_GENERATIONS} generations)")
    if not solved:
        return
    print(f"  generations       mean {statistics.fmean(int(r['generation']) for r in solved):.1f}")
    print(f"  evaluations       mean {statistics.fmean(evaluations):,.0f}  "
          f"s.d. {statistics.stdev(evaluations):,.0f}  worst {max(evaluations):,}")
    print(f"  hidden nodes      mean {statistics.fmean(hidden):.2f}  s.d. {statistics.stdev(hidden):.2f}"
          f"  range {min(hidden)}-{max(hidden)}  one hidden node: {hidden.count(1)} runs")
    print(f"  enabled connections mean "
          f"{statistics.fmean(int(r['enabled_connections']) for r in solved):.2f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task", choices=TASKS)
    parser.add_argument("--processes", type=int, default=os.cpu_count())
    args = parser.parse_args()

    path = ROOT / "results" / f"{args.task}.csv"
    path.parent.mkdir(exist_ok=True)
    done = set()
    if path.exists():
        with open(path) as f:
            done = {int(r["seed"]) for r in csv.DictReader(f)}
    seeds = [s for s in range(RUNS[args.task]) if s not in done]
    new_file = not path.exists()
    with open(path, "a", newline="") as f, Pool(args.processes) as pool:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["seed", "solved", "generation", "evaluations", "hidden_nodes",
                             "enabled_connections"])
        for row in pool.imap_unordered(run, [(args.task, s) for s in seeds]):
            writer.writerow(row)
            f.flush()
    summarise(args.task, path)


if __name__ == "__main__":
    main()
