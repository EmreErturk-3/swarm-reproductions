#!/usr/bin/env python3
"""
Compare the simulations with Vicsek et al. (1995), Figs. 2 and 3.

v_a of a run is the mean order parameter over a measurement window (default: the
second half of the run); points are averaged over runs. The critical exponents follow
the paper's procedure: for each system size the critical value eta_c(L) (or rho_c(L))
is chosen such that log v_a against log[(eta_c - eta)/eta_c] is straightest, and the
slope of the fitted line is the exponent. The same procedure is applied to the
digitized data of the paper as a check of the procedure.

  ./analyze.py                       # figures and summary in results/
  ./analyze.py --window 1000 3000    # use steps 1000-3000 as the measurement window
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RESULTS, DATA = ROOT / "results", ROOT / "data"
SIZES = [(40, 3.1), (100, 5.0), (400, 10.0), (4000, 31.6), (10000, 50.0)]
PAPER = {"beta": (0.45, 0.07), "delta": (0.35, 0.06), "eta_c_inf": (2.9, 0.05)}


def read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def load_runs(sweep):
    """Map (n, box, eta) -> array (runs, blocks) of block means, and the block end times."""
    series = defaultdict(lambda: defaultdict(dict))
    for r in read_csv(RESULTS / f"{sweep}.csv"):
        key = (int(r["n"]), float(r["box"]), float(r["eta"]))
        series[key][int(r["run"])][int(r["t_end"])] = float(r["va"])
    runs = {}
    for key, by_run in series.items():
        times = sorted(next(iter(by_run.values())))
        runs[key] = np.array([[by_run[run][t] for t in times] for run in sorted(by_run)])
    return runs, np.array(times)


def windowed(runs, times, window):
    """Map key -> (mean, standard deviation over runs) of v_a in the window (t0, t1]."""
    mask = (times > window[0]) & (times <= window[1])
    return {key: (blocks[:, mask].mean(axis=1).mean(), blocks[:, mask].mean(axis=1).std())
            for key, blocks in runs.items()}


def straightest_fit(control, va, candidates, reduced, min_points=6):
    """Critical value maximising R^2 of log v_a against log(reduced distance), and slope."""
    best = None
    for critical in candidates:
        x = reduced(control, critical)
        ok = (x > 0) & (va > 0)
        if ok.sum() < min_points:
            continue
        slope, intercept = np.polyfit(np.log(x[ok]), np.log(va[ok]), 1)
        r2 = np.corrcoef(np.log(x[ok]), np.log(va[ok]))[0, 1] ** 2
        if best is None or r2 > best[0]:
            best = (r2, critical, slope)
    return best


BETA_SIZES = (4000, 10000)      # the two systems of the paper's Fig. 3a
ETA_C_CANDIDATES = np.arange(2.0, 4.5, 0.01)


def noise_exponent(curves):
    """curves: n -> (eta array, v_a array). Returns eta_c(L) for every size whose
    straightest line is well defined (enough points, eta_c inside the candidate range;
    small systems have no sharp transition), and beta pooled over BETA_SIZES."""
    reduced = lambda eta, c: np.where(eta < c, (c - eta) / c, -1.0)
    critical, xs, ys = {}, [], []
    for n, (eta, va) in curves.items():
        fit = straightest_fit(eta, va, ETA_C_CANDIDATES, reduced)
        if fit is None or not ETA_C_CANDIDATES[0] < fit[1] < ETA_C_CANDIDATES[-1]:
            continue
        critical[n] = fit[1]
        if n in BETA_SIZES:
            x = reduced(eta, fit[1])
            ok = (x >= 0.02) & (va > 0)
            xs.append(x[ok]), ys.append(va[ok])
    beta = np.polyfit(np.log(np.concatenate(xs)), np.log(np.concatenate(ys)), 1)[0]
    return critical, beta


def density_exponent(rho, va):
    reduced = lambda r, c: np.where(r > c, (r - c) / c, -1.0)
    _, rho_c, delta = straightest_fit(rho, va, np.arange(0.1, 2.0, 0.01), reduced, min_points=8)
    return rho_c, delta


def plot(fig2a, fig2b, paper2a, paper2b, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    colours = plt.cm.viridis(np.linspace(0, 0.9, len(SIZES)))
    for (n, box), colour in zip(SIZES, colours):
        eta, va = fig2a[n]
        ax1.plot(eta, va, "-", color=colour, label=f"N = {n}")
        ref = [(float(r["eta"]), float(r["va"])) for r in paper2a if int(r["n"]) == n]
        ax1.plot(*zip(*ref), "o", mfc="none", color=colour, markersize=5)
    ax1.set(xlabel=r"noise $\eta$", ylabel=r"$v_a$", ylim=(0, 1.05),
            title="Fig. 2a: lines this work, circles paper")
    ax1.legend(frameon=False, fontsize=8)
    rho, va = fig2b
    ax2.plot(rho, va, "-", color="tab:blue", label="this work")
    ax2.plot([float(r["rho"]) for r in paper2b], [float(r["va"]) for r in paper2b], "o",
             mfc="none", color="black", label="paper")
    ax2.set(xlabel=r"density $\rho$", ylabel=r"$v_a$", ylim=(0, 1),
            title=r"Fig. 2b: $\eta$ = 2, L = 20")
    ax2.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=200)


def plot_windows(runs, times, path):
    """v_a versus noise for N = 10000 measured in successive windows of the run."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    paper = [(float(r["eta"]), float(r["va"])) for r in read_csv(DATA / "vicsek1995_fig2a.csv")
             if int(r["n"]) == 10000]
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for window in [(0, 1000), (1000, 3000), (3000, 6000), (6000, 12000)]:
        means = windowed(runs, times, window)
        eta = sorted(k[2] for k in means if k[0] == 10000)
        ax.plot(eta, [means[(10000, 50.0, e)][0] for e in eta], "-",
                label=f"steps {window[0]}-{window[1]}")
    ax.plot(*zip(*paper), "o", mfc="none", color="black", label="paper")
    ax.set(xlabel=r"noise $\eta$", ylabel=r"$v_a$", xlim=(1.5, 4), ylim=(0, 1),
           title="N = 10000: dependence on the measurement window")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=200)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--window", type=int, nargs=2, default=(6000, 12000),
                        metavar=("FROM", "TO"), help="measurement window in steps")
    args = parser.parse_args()

    runs2a, times2a = load_runs("fig2a")
    runs2b, times2b = load_runs("fig2b")
    means2a, means2b = windowed(runs2a, times2a, args.window), windowed(runs2b, times2b, args.window)
    paper2a = read_csv(DATA / "vicsek1995_fig2a.csv")
    paper2b = read_csv(DATA / "vicsek1995_fig2b.csv")

    fig2a = {}
    for n, box in SIZES:
        eta = np.array(sorted(k[2] for k in means2a if k[0] == n))
        fig2a[n] = (eta, np.array([means2a[(n, box, e)][0] for e in eta]))
    keys2b = sorted(means2b, key=lambda k: k[0])
    fig2b = (np.array([k[0] / k[1] ** 2 for k in keys2b]), np.array([means2b[k][0] for k in keys2b]))

    paper_curves = {n: (np.array([float(r["eta"]) for r in paper2a if int(r["n"]) == n]),
                        np.array([float(r["va"]) for r in paper2a if int(r["n"]) == n]))
                    for n, _ in SIZES}
    critical, beta = noise_exponent(fig2a)
    critical_paper, beta_paper = noise_exponent(paper_curves)
    rho_c, delta = density_exponent(*fig2b)
    rho_c_paper, delta_paper = density_exponent(np.array([float(r["rho"]) for r in paper2b]),
                                                np.array([float(r["va"]) for r in paper2b]))
    box_of = dict(SIZES)

    def extrapolate(crit):            # eta_c(L) linear in 1/L, over the sizes with an eta_c
        sizes = sorted(crit)
        return np.polyfit([1 / box_of[n] for n in sizes], [crit[n] for n in sizes], 1)[1], sizes
    eta_c_inf, sizes_used = extrapolate(critical)
    eta_c_inf_paper, sizes_used_paper = extrapolate(critical_paper)

    print(f"Measurement window: steps {args.window[0]}-{args.window[1]}\n")
    print("| quantity | paper (reported) | procedure on paper's data | this work |")
    print("|---|--:|--:|--:|")
    print(f"| beta | {PAPER['beta'][0]} ± {PAPER['beta'][1]} | {beta_paper:.2f} | {beta:.2f} |")
    print(f"| delta | {PAPER['delta'][0]} ± {PAPER['delta'][1]} | {delta_paper:.2f} | {delta:.2f} |")
    print(f"| rho_c(L = 20) at eta = 2 | – | {rho_c_paper:.2f} | {rho_c:.2f} |")
    show = lambda crit, n: f"{crit[n]:.2f}" if n in crit else "no sharp transition"
    for n, _ in SIZES:
        print(f"| eta_c(L), N = {n} | – | {show(critical_paper, n)} | {show(critical, n)} |")
    print(f"| eta_c(inf), linear in 1/L | {PAPER['eta_c_inf'][0]} ± {PAPER['eta_c_inf'][1]} "
          f"| {eta_c_inf_paper:.2f} (N = {', '.join(map(str, sizes_used_paper))}) "
          f"| {eta_c_inf:.2f} (N = {', '.join(map(str, sizes_used))}) |")

    print("\nFig. 2a, v_a: paper / this work (mean ± s.d. over runs)\n")
    print("| N | eta | paper | this work |")
    print("|--:|--:|--:|--:|")
    for r in paper2a:
        key = (int(r["n"]), float(r["box"]), round(float(r["eta"]), 2))
        if key in means2a:
            mean, sd = means2a[key]
            print(f"| {key[0]} | {key[2]:.1f} | {float(r['va']):.2f} | {mean:.2f} ± {sd:.2f} |")

    window = f"{args.window[0]}-{args.window[1]}"
    plot(fig2a, fig2b, paper2a, paper2b, RESULTS / f"fig2_steps{window}.png")
    plot_windows(runs2a, times2a, RESULTS / "fig2a_windows.png")
    print(f"\nFigures: results/fig2_steps{window}.png, results/fig2a_windows.png")


if __name__ == "__main__":
    main()
