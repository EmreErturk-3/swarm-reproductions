#!/usr/bin/env python3
"""
Run the light-finder experiments of Bodi et al. (2009) with Kilobots in ARGoS.

A run simulates N light finders for 240 paper seconds, i.e. 240 * k Kilobot
seconds for time scale k, and writes one CSV per run to results/<label>/, where
the label encodes the configuration (k30, k25_f1.2, k30_c60, ...). Completed
runs are skipped, so an interrupted sweep can be resumed.

Examples (after `source scripts/env.sh`):
  scripts/run_experiments.py --time-scale 30 --calibration         # 40 runs, N = 9
  scripts/run_experiments.py --time-scale 30                       # full sweep
  scripts/run_experiments.py --time-scale 25 --footprint 1.2       # sensitivity
  scripts/run_experiments.py --time-scale 30 --robots 9 --visualize
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "experiments" / "beeclust.argos.in"

# Bodi et al. (2009), Sec. 2 and Figs. 4-5.
PAPER_RUN_LENGTH_S = 240
PAPER_ROBOTS = (2, 3, 6, 9, 12, 18, 24, 33, 42, 60, 100, 120)
PAPER_REPETITIONS = 6
ARENA_PATCHES = (48, 27)

# Calibration of the time scale on TA50 at N = 9 (Fig. 7). Single runs vary
# widely, so the median is estimated from more runs than the paper's six.
CALIBRATION_ROBOTS = 9
CALIBRATION_REPETITIONS = 40

KILOBOT_DIAMETER = 0.033  # m
WALL_THICKNESS = 0.02     # m
DEFAULT_CONTACT_MM = 52

VISUALIZATION = """<visualization>
    <qt-opengl>
      <camera>
        <placements>
          <placement index="0" position="0, 0, 1.9" look_at="0, 0, 0" up="0, 1, 0"
                     lens_focal_length="20" />
        </placements>
      </camera>
    </qt-opengl>
  </visualization>"""


@dataclass(frozen=True)
class Configuration:
    time_scale: float                     # Kilobot seconds per paper second
    footprint: float = 1.0                # robot bodies per patch of the paper's arena
    contact_mm: int = DEFAULT_CONTACT_MM  # message distance counted as contact

    @property
    def build_label(self):
        """Controller parameters, compiled into the robot program."""
        label = f"k{self.time_scale:g}"
        return label if self.contact_mm == DEFAULT_CONTACT_MM else f"{label}_c{self.contact_mm}"

    @property
    def label(self):
        """All parameters; names the results directory."""
        label = f"k{self.time_scale:g}"
        if self.footprint != 1.0:
            label += f"_f{self.footprint:g}"
        if self.contact_mm != DEFAULT_CONTACT_MM:
            label += f"_c{self.contact_mm}"
        return label

    def arena(self):
        """Geometry fields of the experiment template, in metres."""
        patch = KILOBOT_DIAMETER / self.footprint
        half_x, half_y = (n * patch / 2 for n in ARENA_PATCHES)
        margin = KILOBOT_DIAMETER / 2 + 0.005
        return dict(
            patch=f"{patch:.5f}",
            arena_x=f"{2 * (half_x + WALL_THICKNESS) + 0.1:.4f}",
            arena_y=f"{2 * (half_y + WALL_THICKNESS) + 0.1:.4f}",
            wall=f"{WALL_THICKNESS}",
            wall_x=f"{half_x + WALL_THICKNESS / 2:.4f}",
            wall_y=f"{half_y + WALL_THICKNESS / 2:.4f}",
            wall_length_x=f"{2 * (half_x + WALL_THICKNESS):.4f}",
            wall_length_y=f"{2 * half_y:.4f}",
            spawn_x=f"{half_x - margin:.4f}",
            spawn_y=f"{half_y - margin:.4f}")


def build(config):
    """Configure and build the controller and loop functions."""
    build_dir = ROOT / "build" / config.build_label
    subprocess.run(["cmake", "-S", ROOT, "-B", build_dir,
                    f"-DBEECLUST_TIME_SCALE={config.time_scale:g}",
                    f"-DBEECLUST_CONTACT_DISTANCE_MM={config.contact_mm}"],
                   check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["cmake", "--build", build_dir, "--parallel"],
                   check=True, stdout=subprocess.DEVNULL)
    return build_dir


def write_config(path, build_dir, config, robots, seed, output, visualize):
    text = TEMPLATE.read_text().format(
        length_s=round(PAPER_RUN_LENGTH_S * config.time_scale),
        seed=seed,
        behavior=build_dir / "beeclust",
        loop_functions=build_dir / "libbeeclust_loop_functions",
        output=output,
        robots=robots,
        visualization=VISUALIZATION if visualize else "",
        **config.arena())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def argos(config_path, **kwargs):
    """Run ARGoS on a configuration file. ARGoS splits the file argument at
    spaces, so it is passed relative to the file's own directory."""
    return subprocess.run(["argos3", "-c", config_path.name], cwd=config_path.parent, **kwargs)


def run(build_dir, results_dir, config, robots, repetition):
    """Run one experiment; its CSV appears only once the run has completed."""
    name = f"robots{robots:03d}_run{repetition}"
    output = results_dir / f"{name}.csv"
    if output.exists():
        return
    partial = output.with_suffix(".partial")
    config_path = build_dir / "configs" / config.label / f"{name}.argos"
    seed = 1000 * robots + repetition + 1
    write_config(config_path, build_dir, config, robots, seed, partial, visualize=False)
    result = argos(config_path, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"{config.label}/{name} failed:\n{result.stderr}")
    partial.replace(output)
    print(f"done {config.label}/{name}", flush=True)


def show(build_dir, config, robots):
    """Open one run in the ARGoS GUI; its measurements are not kept."""
    config_path = build_dir / "configs" / config.label / f"robots{robots:03d}_gui.argos"
    write_config(config_path, build_dir, config, robots, seed=1,
                 output=build_dir / "gui_run.csv", visualize=True)
    argos(config_path, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--time-scale", type=float, required=True,
                        help="Kilobot seconds per paper second (README, 'Time scale')")
    parser.add_argument("--footprint", type=float, default=1.0,
                        help="robot bodies per patch of the paper's arena (default 1)")
    parser.add_argument("--contact-mm", type=int, default=DEFAULT_CONTACT_MM,
                        help=f"message distance counted as contact (default {DEFAULT_CONTACT_MM})")
    parser.add_argument("--robots", type=int, nargs="+")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--calibration", action="store_true",
                        help=f"calibration runs: N = {CALIBRATION_ROBOTS}, "
                             f"{CALIBRATION_REPETITIONS} repetitions, stored in results/calibration/")
    parser.add_argument("--jobs", type=int, default=os.cpu_count())
    parser.add_argument("--visualize", action="store_true",
                        help="open the ARGoS GUI for one run of the first --robots value")
    args = parser.parse_args()
    if args.calibration:
        robots = args.robots or [CALIBRATION_ROBOTS]
        repetitions = args.repetitions or CALIBRATION_REPETITIONS
    else:
        robots = args.robots or PAPER_ROBOTS
        repetitions = args.repetitions or PAPER_REPETITIONS

    config = Configuration(args.time_scale, args.footprint, args.contact_mm)
    build_dir = build(config)
    if args.visualize:
        show(build_dir, config, robots[0])
        return

    results_dir = ROOT / "results" / ("calibration" if args.calibration else "") / config.label
    results_dir.mkdir(parents=True, exist_ok=True)
    # Largest swarms first, so that the slowest runs do not end up last.
    jobs = [(n, r) for n in sorted(robots, reverse=True) for r in range(repetitions)]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in [pool.submit(run, build_dir, results_dir, config, n, r) for n, r in jobs]:
            future.result()


if __name__ == "__main__":
    main()
