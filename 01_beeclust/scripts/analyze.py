#!/usr/bin/env python3
"""
Compare the Kilobot runs with Bodi et al. (2009), Figs. 5 and 7 (N_S = 0).

Measures, as defined in Sec. 2 of the paper, with times in paper seconds:
  FA    fraction of robots waiting inside the target zone, averaged over the
        last minute of a run (Fig. 5);
  TA50  first time at which at least half of the robots wait inside the target
        zone, 240 if this never happens (Fig. 7).

Usage:
  scripts/analyze.py k30                        # table and figure for one configuration
  scripts/analyze.py k30 k25_f1.2 k20_f1.5      # FA of several configurations, overlaid
  scripts/analyze.py --calibration              # TA50 at N = 9 for each time scale
"""
import argparse
import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
REFERENCE = ROOT / "data" / "bodi2009_fig5_fig7.csv"
RUN_LENGTH_S = 240
WINDOW_S = 60
CALIBRATION_ROBOTS, CALIBRATION_TA50_S = 9, 20.0  # Fig. 7, N_L = 9, N_S = 0


def time_scale(label):
    """Time scale k encoded in a results label such as 'k25_f1.2' or 'calibration/k30'."""
    return float(re.match(r"k([0-9.]+)", Path(label).name).group(1))


def read_run(path, k):
    """Return (robots, FA, TA50) of one run, with times converted to paper seconds."""
    with open(path) as f:
        rows = [(int(r["time_s"]) / k, int(r["waiting_in_zone"]), int(r["robots"]))
                for r in csv.DictReader(f)]
    robots = rows[0][2]
    last_minute = [w / robots for t, w, _ in rows if t > RUN_LENGTH_S - WINDOW_S]
    ta50 = next((t for t, w, _ in rows if 2 * w >= robots), RUN_LENGTH_S)
    return robots, statistics.fmean(last_minute), ta50


def read_results(label):
    """Map swarm size -> list of (FA, TA50) over the runs of one configuration."""
    runs = defaultdict(list)
    for path in sorted((RESULTS / label).glob("robots*_run*.csv")):
        robots, fa, ta50 = read_run(path, time_scale(label))
        runs[robots].append((fa, ta50))
    if not runs:
        raise SystemExit(f"No results in results/{label}")
    return runs


def read_reference():
    with open(REFERENCE) as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        return {int(r["robots"]): r for r in rows}


def fa_summary(runs):
    """Rows (N, median, Q1, Q3) of FA."""
    rows = []
    for robots in sorted(runs):
        fa = [r[0] for r in runs[robots]]
        q1, median, q3 = (statistics.quantiles(fa, n=4, method="inclusive")
                          if len(fa) > 1 else (fa[0],) * 3)
        rows.append((robots, median, q1, q3))
    return rows


def compare(label):
    runs, reference = read_results(label), read_reference()
    print(f"{label}: FA as median [Q1, Q3]; TA50 as median, paper seconds\n")
    print("| N | runs | FA paper | FA Kilobot | TA50 paper | TA50 Kilobot |")
    print("|--:|--:|:--|:--|--:|--:|")
    summary = fa_summary(runs)
    for robots, median, q1, q3 in summary:
        ta50 = statistics.median(r[1] for r in runs[robots])
        ref = reference.get(robots)
        fa_paper = f"{ref['fa_median']} [{ref['fa_q1']}, {ref['fa_q3']}]" if ref else "-"
        ta50_paper = ref["ta50_s"] if ref and ref["ta50_s"] else "-"
        print(f"| {robots} | {len(runs[robots])} | {fa_paper} | {median:.2f} [{q1:.2f}, {q3:.2f}] "
              f"| {ta50_paper} | {ta50:.0f} |")
    best = max(summary, key=lambda s: s[1])
    print(f"\nHighest median FA: N = {best[0]} (FA = {best[1]:.2f}); paper: N = 9 (FA = 0.80)")
    plot({f"Kilobot ({label})": summary}, reference, RESULTS / f"fig5_{label}.png")


def overlay(labels):
    reference = read_reference()
    summaries = {label: fa_summary(read_results(label)) for label in labels}
    print("Median FA\n")
    print("| N | paper | " + " | ".join(labels) + " |")
    print("|--:|--:|" + "--:|" * len(labels))
    for robots in sorted(reference):
        cells = []
        for label in labels:
            row = next((s for s in summaries[label] if s[0] == robots), None)
            cells.append(f"{row[1]:.2f}" if row else "-")
        print(f"| {robots} | {reference[robots]['fa_median']} | " + " | ".join(cells) + " |")
    print("\nSum of squared deviations from the paper's medians:")
    for label in labels:
        sse = sum((median - float(reference[n]["fa_median"])) ** 2
                  for n, median, _, _ in summaries[label] if n in reference)
        best = max(summaries[label], key=lambda s: s[1])
        print(f"  {label:12s} {sse:.3f}   optimum N = {best[0]} (FA = {best[1]:.2f})")
    plot(summaries, reference, RESULTS / "fig5_sensitivity.png")


def plot(summaries, reference, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping the figure")
        return
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    paper = [(n, float(r["fa_median"]), float(r["fa_q1"]), float(r["fa_q3"]))
             for n, r in sorted(reference.items())]
    series = [("Bodi et al. (2009), Jasmine III", paper, "black")]
    series += [(label, rows, None) for label, rows in summaries.items()]
    for label, rows, colour in series:
        n, median, q1, q3 = zip(*rows)
        ax.errorbar(n, median, yerr=[[m - a for m, a in zip(median, q1)],
                                     [b - m for m, b in zip(median, q3)]],
                    marker="o", markersize=3.5, capsize=2, linewidth=1.2,
                    color=colour, label=label)
    ax.set_xlabel("number of light finders $N_L$")
    ax.set_ylabel("fraction waiting in target zone")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    print(f"Figure written to {path.relative_to(ROOT)}")


def calibration():
    print(f"TA50 at N = {CALIBRATION_ROBOTS} in paper seconds (paper: {CALIBRATION_TA50_S:g} s, "
          f"median of 6 runs)\n")
    print("| k | runs | TA50 median | TA50 [Q1, Q3] |")
    print("|--:|--:|--:|:--|")
    labels = sorted((f"calibration/{d.name}" for d in (RESULTS / "calibration").glob("k*")),
                    key=time_scale)
    for label in labels:
        ta50 = [r[1] for r in read_results(label).get(CALIBRATION_ROBOTS, [])]
        q1, median, q3 = statistics.quantiles(ta50, n=4, method="inclusive")
        print(f"| {time_scale(label):g} | {len(ta50)} | {median:.1f} | [{q1:.1f}, {q3:.1f}] |")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("labels", nargs="*", help="results directories, e.g. k30")
    parser.add_argument("--calibration", action="store_true")
    args = parser.parse_args()
    if args.calibration:
        calibration()
    elif len(args.labels) == 1:
        compare(args.labels[0])
    elif args.labels:
        overlay(args.labels)
    else:
        parser.error("give one or more results labels, or --calibration")


if __name__ == "__main__":
    main()
