#!/usr/bin/env python3
"""
Largest Lyapunov exponent of pattern epsilon (F = 0.02, k = 0.059), Fig. 6 of Pearson (1993).

As in the paper, the system is evolved for 20,000 time steps; a copy is perturbed with
noise of order 1e-12 and both are evolved together. D(t) is the space average of
|U - U'|. This is done 20 times (here from 20 independent initial conditions) and the
exponent is the slope of the mean log D(t). Paper: about 1.5e-3, i.e. a Lyapunov time of
660 time steps.

  ./lyapunov.py            # results/lyapunov.npz and results/fig6.png
"""
import os
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from grayscott import GrayScott, initial_state

ROOT = Path(__file__).resolve().parent
F, K = 0.02, 0.059
TRANSIENT, DURATION, EVERY, RUNS = 20_000, 10_000, 50, 20
FIT_FROM = 2_000   # the first ~1,000 steps are a transient before exponential growth


def separation(seed):
    rng = np.random.default_rng(seed)
    a = GrayScott(F, K, *initial_state(rng))
    a.step(TRANSIENT)
    b = GrayScott(F, K, a.u + rng.uniform(-1e-12, 1e-12, a.u.shape),
                  a.v + rng.uniform(-1e-12, 1e-12, a.v.shape))
    distance = [np.abs(a.u - b.u).mean()]
    for _ in range(DURATION // EVERY):
        a.step(EVERY)
        b.step(EVERY)
        distance.append(np.abs(a.u - b.u).mean())
    return np.log10(distance)


def main():
    (ROOT / "results").mkdir(exist_ok=True)
    with Pool(min(RUNS, os.cpu_count())) as pool:
        log_d = np.array(pool.map(separation, range(RUNS)))
    t = np.arange(log_d.shape[1]) * EVERY
    mean, sd = log_d.mean(0), log_d.std(0)
    fit = t >= FIT_FROM
    slope, intercept = np.polyfit(t[fit], mean[fit], 1)
    exponent = slope * np.log(10)
    per_run = np.array([np.polyfit(t[fit], run[fit], 1)[0] for run in log_d]) * np.log(10)
    np.savez(ROOT / "results" / "lyapunov.npz", t=t, log_d=log_d)
    print(f"largest Lyapunov exponent {exponent:.2e} per time unit "
          f"(runs: {per_run.mean():.2e} +- {per_run.std(ddof=1):.1e}); "
          f"Lyapunov time {1 / exponent:.0f}; paper about 1.5e-3 and 660")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    for curve in (mean - sd, mean, mean + sd):
        ax.plot(t, curve, color="black", linewidth=0.8)
    ax.plot(t[fit], intercept + slope * t[fit], "--", color="tab:red",
            label=f"slope: λ = {exponent:.2e}")
    ax.set(xlabel="t", ylabel="log$_{10}$ D", xlim=(0, DURATION), ylim=(-16, -4),
           title=f"Pattern ε (F = {F}, k = {K}), {RUNS} runs")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(ROOT / "results" / "fig6.png", dpi=150)


if __name__ == "__main__":
    main()
