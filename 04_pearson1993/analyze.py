#!/usr/bin/env python3
"""
Compare the simulated phase map with Fig. 3 of Pearson (1993) and draw Figs. 1-3.

Every simulated point is classified from U at t = 200,000:
  R     uniform red state (U = 1 everywhere),
  B     uniform blue state,
  steady / time-dependent pattern, by the largest change of U over the last 250 steps
        (threshold CHANGE_THRESHOLD, set at the gap in the distribution of that change).
The paper describes patterns alpha, beta, gamma, epsilon, zeta and eta as time-dependent
and delta, iota and lambda as time-independent; theta, kappa and mu are compared with
the steady patterns of Lee et al. (1993) and are counted as steady.

  ./analyze.py        # table; results/fig1.png, results/fig2.png, results/fig3.png
"""
import csv
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
         "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι", "kappa": "κ", "lambda": "λ",
         "mu": "μ", "R": "R", "B": "B"}
TIME_DEPENDENT = {"alpha", "beta", "gamma", "epsilon", "zeta", "eta"}
# The map point shown for each pattern in our version of Fig. 2.
KEY = {"alpha": (0.05, 0.015), "beta": (0.04, 0.015), "gamma": (0.055, 0.025),
       "delta": (0.055, 0.030), "epsilon": (0.0625, 0.025), "zeta": (0.06, 0.025),
       "eta": (0.0625, 0.035), "theta": (0.059, 0.035), "iota": (0.06, 0.050),
       "kappa": (0.0625, 0.045), "lambda": (0.065, 0.040), "mu": (0.065, 0.050)}
CHANGE_THRESHOLD = 0.14      # in the gap between 0.094 (steady theta) and 0.185 (beta)


def paper_class(label):
    if label in ("R", "B"):
        return label
    return "time-dependent" if label in TIME_DEPENDENT else "steady"


def short_change(run):
    """Largest change of U over the last 250 steps. Slowly coarsening defects (the paper's
    "apparently stable defects") barely move over 250 steps; spot division, oscillating
    stripes and phase turbulence change a lot."""
    return np.abs(run["u200000"].astype(float) - run["u199750"]).max()


def classify(run):
    u = run["u200000"]
    if u.min() > 0.99:
        return "R"
    if u.max() - u.min() < 0.01:
        return "B"
    return "time-dependent" if short_change(run) > CHANGE_THRESHOLD else "steady"


def bifurcation_curves(k):
    """Fig. 1. Saddle-node line of the uniform states, F = 4 (F + k)^2, as a closed
    curve (both branches), and Hopf line of the blue state, (F + k)^2 = F sqrt(k), where
    V^2 = k on that state."""
    lower, upper = [], []
    for kk in k:
        disc = (8 * kk - 1) ** 2 - 64 * kk ** 2
        roots = (1 - 8 * kk + np.array([-1, 1]) * np.sqrt(max(disc, 0))) / 8
        lower.append(roots[0] if disc >= 0 else np.nan)
        upper.append(roots[1] if disc >= 0 else np.nan)
    saddle = np.r_[lower, upper[::-1]], np.r_[k, k[::-1]]
    hopf = []
    for kk in k:
        roots = [r.real for r in np.roots([1, 2 * kk - np.sqrt(kk), kk ** 2])
                 if abs(r.imag) < 1e-12 and r.real > 0]
        # keep the root at which V = sqrt(k) is the stable (larger) uniform state
        roots = [F for F in roots if np.sqrt(kk) >= F / (2 * (F + kk))]
        hopf.append(max(roots) if roots else np.nan)
    return saddle, np.array(hopf)


def load():
    with open(ROOT / "data" / "pearson1993_fig3.csv") as f:
        points = [(float(r["k"]), float(r["F"]), r["pattern"]) for r in csv.DictReader(f)]
    runs = {}
    for k, F, _ in points:
        path = ROOT / "results" / "map" / f"k{k:.4f}_F{F:.3f}.npz"
        if path.exists():
            runs[(k, F)] = dict(np.load(path))
    return points, runs


def report(points, runs):
    rows, confusion = [], Counter()
    for k, F, label in points:
        if (k, F) not in runs:
            continue
        ours = classify(runs[(k, F)])
        confusion[(paper_class(label), ours)] += 1
        rows.append((k, F, label, ours))
    agree = sum(n for (a, b), n in confusion.items() if a == b)
    print(f"{agree} of {len(rows)} points agree with the paper's class\n")
    classes = ["R", "B", "steady", "time-dependent"]
    print("| paper \\ here | " + " | ".join(classes) + " |")
    print("|---|" + "---|" * len(classes))
    for a in classes:
        print(f"| {a} | " + " | ".join(str(confusion[(a, b)]) for b in classes) + " |")
    print("\nDisagreements:")
    for k, F, label, ours in rows:
        if paper_class(label) != ours:
            print(f"  k = {k:.4f}  F = {F:.3f}  paper {GREEK[label]} ({paper_class(label)}), "
                  f"here {ours}")
    t_edge = np.array([float(r["t_edge"]) for r in runs.values()])
    t_edge = t_edge[np.isfinite(t_edge)]
    # from the edge of the initial square (0.098) to the edge of the box (1.25)
    speed = (1.25 - 10 * 2.5 / 256) / t_edge
    print(f"\nDisturbance reached the box edge in {len(t_edge)} runs after "
          f"{t_edge.min():.0f}-{t_edge.max():.0f} steps (median {np.median(t_edge):.0f}); "
          f"front speed {speed.min():.1e}-{speed.max():.1e}")
    return rows


def figures(points, runs, rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    image = dict(cmap="jet", vmin=0.2, vmax=1.0, origin="lower")  # red U = 1, blue U = 0.2

    k = np.linspace(0.0, 0.0625, 1251)
    (saddle_F, saddle_k), hopf = bifurcation_curves(k)
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot(saddle_k, saddle_F, "k-", k, hopf, "k:")
    ax.set(xlabel="k", ylabel="F", xlim=(0, 0.08), ylim=(0, 0.3),
           title="Fig. 1: uniform states")
    fig.tight_layout()
    fig.savefig(ROOT / "results" / "fig1.png", dpi=150)

    fig, axes = plt.subplots(3, 4, figsize=(10, 8))
    for ax, (label, point) in zip(axes.flat, KEY.items()):
        ax.imshow(runs[point]["u200000"], **image)
        ax.set_title(f"{GREEK[label]}   k = {point[0]}, F = {point[1]}", fontsize=10)
        ax.set(xticks=[], yticks=[])
    fig.tight_layout()
    fig.savefig(ROOT / "results" / "fig2.png", dpi=120)

    fig, ax = plt.subplots(figsize=(6, 7))
    ax.plot(saddle_k, saddle_F, "k-", k, hopf, "k:", linewidth=0.8)
    for kk, F, label, ours in rows:
        ax.text(kk, F, GREEK[label], ha="center", va="center", fontsize=11,
                color="tab:green" if paper_class(label) == ours else "tab:red")
    ax.set(xlabel="k", ylabel="F", xlim=(0.03, 0.07), ylim=(0, 0.08),
           title="Fig. 3: paper's labels; green = same class here, red = different")
    fig.tight_layout()
    fig.savefig(ROOT / "results" / "fig3.png", dpi=150)

    # all simulated points: one column per k, rows by decreasing F
    columns = sorted({kk for kk, _, _ in points})
    by_column = {c: sorted([p for p in points if p[0] == c], key=lambda p: -p[1]) for c in columns}
    n_rows = max(len(v) for v in by_column.values())
    fig, axes = plt.subplots(n_rows, len(columns), figsize=(1.3 * len(columns), 1.45 * n_rows))
    for ax in axes.flat:
        ax.axis("off")
    for j, c in enumerate(columns):
        for i, (kk, F, label) in enumerate(by_column[c]):
            if (kk, F) in runs:
                axes[i, j].imshow(runs[(kk, F)]["u200000"], **image)
                axes[i, j].set_title(f"{GREEK[label]}  {kk:g}, {F:g}", fontsize=7)
    fig.tight_layout(pad=0.3)
    fig.savefig(ROOT / "results" / "fig3_atlas.png", dpi=110)


if __name__ == "__main__":
    points, runs = load()
    rows = report(points, runs)
    figures(points, runs, rows)
