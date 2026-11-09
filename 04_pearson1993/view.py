#!/usr/bin/env python3
"""
Watch the Gray-Scott model live at one of the twelve patterns of Pearson (1993), Fig. 2,
from the paper's initial condition. Colours as in the paper: red U = 1, blue U = 0.2.

  ./view.py kappa               # any Greek letter of analyze.KEY
  ./view.py --F 0.02 --k 0.059  # any point
  ./view.py epsilon --speed 50

Keys: space pause, n step, + / - speed, s screenshot, q quit.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "alife" / "common"))
from viewer import colorize, show                             # noqa: E402
from analyze import KEY                                       # noqa: E402
from grayscott import GrayScott, initial_state                # noqa: E402


class GrayScottView:
    def __init__(self, F, k, seed=0):
        self.model = GrayScott(F, k, *initial_state(np.random.default_rng(seed)))

    def step(self):
        self.model.step()

    def render(self):
        return colorize(self.model.u, 0.2, 1.0)

    def caption(self):
        return f"F = {self.model.F}, k = {self.model.k}   t = {self.model.t:,.0f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pattern", nargs="?", choices=list(KEY), default="kappa")
    parser.add_argument("--F", type=float)
    parser.add_argument("--k", type=float)
    parser.add_argument("--scale", type=int, default=3)
    parser.add_argument("--speed", type=int, default=25, help="time steps per frame")
    args = parser.parse_args()
    k, F = KEY[args.pattern]
    F, k = args.F if args.F is not None else F, args.k if args.k is not None else k
    show(GrayScottView(F, k), f"Gray-Scott F={F} k={k}", args.speed, args.scale, fps=60)


if __name__ == "__main__":
    main()
