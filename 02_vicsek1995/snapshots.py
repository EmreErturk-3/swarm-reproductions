#!/usr/bin/env python3
"""
Fig. 1 of Vicsek et al. (1995): velocities (arrows) and the last 20 positions (trails)
of N = 300 particles in four regimes, and an animation of the ordering transition.

The paper does not state the time of panels b-d; 2000 steps are used here.

  ./snapshots.py            # results/fig1.png and results/vicsek.mp4
"""
from pathlib import Path

import numpy as np

from vicsek import VicsekModel

ROOT = Path(__file__).resolve().parent
TRAIL = 20
PANELS = [  # (title, box, noise, steps), caption of Fig. 1
    ("(a) t = 0, L = 7, η = 2.0", 7.0, 2.0, 0),
    ("(b) L = 25, η = 0.1", 25.0, 0.1, 2000),
    ("(c) L = 7, η = 2.0", 7.0, 2.0, 2000),
    ("(d) L = 5, η = 0.1", 5.0, 0.1, 2000),
]


def run_with_trail(box, noise, steps, seed=1, n=300):
    model = VicsekModel(n, box, noise, seed=seed)
    trail = [model.position.copy()]
    for _ in range(steps):
        model.step()
        trail = (trail + [model.position.copy()])[-TRAIL:]
    return model, np.array(trail)


def draw(ax, model, trail):
    for k in range(model.n):
        path = trail[:, k]
        # Split the trail where it wraps around the periodic boundary.
        jumps = np.flatnonzero(np.abs(np.diff(path, axis=0)).max(axis=1) > model.box / 2) + 1
        for segment in np.split(path, jumps):
            ax.plot(segment[:, 0], segment[:, 1], "-", color="0.6", linewidth=0.6)
    ax.quiver(model.position[:, 0], model.position[:, 1], np.cos(model.angle),
              np.sin(model.angle), angles="xy", scale_units="xy",
              scale=1.0 / (0.04 * model.box), width=0.004, color="black")
    ax.set(xlim=(0, model.box), ylim=(0, model.box), aspect="equal", xticks=[], yticks=[])


def figure_one(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(8, 8))
    for ax, (title, box, noise, steps) in zip(axes.flat, PANELS):
        draw(ax, *run_with_trail(box, noise, steps))
        ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def animation(path, n=1000, box=16.0, steps=1500, every=3):
    """Ordering at low noise, from random initial conditions."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FFMpegWriter
    model = VicsekModel(n, box, noise=0.5, speed=0.05, seed=2)
    fig, ax = plt.subplots(figsize=(5, 5))
    arrows = ax.quiver(model.position[:, 0], model.position[:, 1], np.cos(model.angle),
                       np.sin(model.angle), model.angle, cmap="twilight", clim=(-np.pi, np.pi),
                       angles="xy", scale_units="xy", scale=1 / 0.35, width=0.004)
    ax.set(xlim=(0, box), ylim=(0, box), aspect="equal", xticks=[], yticks=[])
    label = ax.set_title("")
    fig.tight_layout()
    writer = FFMpegWriter(fps=30)
    with writer.saving(fig, path, dpi=120):
        for t in range(steps):
            model.step()
            if t % every == 0:
                arrows.set_offsets(model.position)
                arrows.set_UVC(np.cos(model.angle), np.sin(model.angle), model.angle)
                label.set_text(f"N = {n}, η = 0.5, t = {t}, $v_a$ = {model.order_parameter():.2f}")
                writer.grab_frame()


if __name__ == "__main__":
    (ROOT / "results").mkdir(exist_ok=True)
    figure_one(ROOT / "results" / "fig1.png")
    animation(ROOT / "results" / "vicsek.mp4")
    print("results/fig1.png, results/vicsek.mp4")
