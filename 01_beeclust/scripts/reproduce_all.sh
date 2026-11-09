#!/usr/bin/env bash
#
# Regenerates every result reported in README.md: time-scale calibration,
# the swarm-size sweep at the calibrated k = 35, and the sensitivity analysis.
# Completed runs are skipped, so the script can be resumed.
#
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/env.sh
run=scripts/run_experiments.py

# Calibration of the time scale on TA50 at N = 9 (40 runs per value).
for k in 10 15 20 25 30 35 40 60; do
  $run --time-scale "$k" --calibration
done

# Swarm-size sweep (Fig. 5) at the calibrated time scale.
$run --time-scale 35

# Sensitivity: robot footprint, with k = 35 / footprint so that speeds in
# patches per paper second are unchanged, and contact threshold.
$run --time-scale 28 --footprint 1.25
$run --time-scale 20 --footprint 1.75
$run --time-scale 35 --contact-mm 45
$run --time-scale 35 --contact-mm 60

scripts/analyze.py --calibration
scripts/analyze.py k35
scripts/analyze.py k35 k28_f1.25 k20_f1.75 k35_c45 k35_c60
