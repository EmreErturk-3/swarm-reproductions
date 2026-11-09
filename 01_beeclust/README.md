# BEECLUST aggregation with Kilobots

> **Status: paused.** The calibration was redone with 40 runs per time scale
> (6 were too noisy) and gives k = 35. The k = 35 sweep is complete
> (`scripts/analyze.py k35`) and agrees qualitatively with the k = 30 results
> below. Still to do: the sensitivity runs, then update the sections "Time scale"
> and "Results". Resume with `scripts/reproduce_all.sh`; completed runs are skipped.

Reproduction of the swarm-size experiment of Bodi et al. (2009) in ARGoS with
simulated Kilobots. Robots running BEECLUST move randomly, stop when they meet
another robot, and wait for a time that grows with the local illuminance. No
robot senses a gradient, yet the swarm gathers in the brightest part of the
arena. The paper reports that this works best at an intermediate swarm size
(9 robots, 80 % in the target zone), because small swarms meet too rarely and
large swarms jam.

**Reproduced:** Fig. 5 (fraction aggregated vs. swarm size, light finders only)
and the aggregation times of Fig. 7 for N_S = 0.
**Not reproduced:** the experiments with a second ("shadow finder") swarm
(Figs. 6–9 with N_S > 0).

## Source

M. Bodi, R. Thenius, T. Schmickl, K. Crailsheim (2009). *Robustness of two
interacting robot swarms using the BEECLUST algorithm.* Proc. MATHMOD 2009,
Vienna, pp. 904–912. [Open-access PDF](https://www.eurosim.info/fileadmin/user_upload_argesim/ARGESIM_Publications_OA/MATHMOD_Publications_OA/MATHMOD_2009_AR34_35/full_papers/495.pdf)

BEECLUST was introduced by T. Schmickl et al. (2009), *Get in touch: cooperative
decision making based on robot-to-robot collisions*, Autonomous Agents and
Multi-Agent Systems 18(1):133–155. Bodi et al. is used here because it is open
access and states the full waiting-time model and its constants.

## Model taken from the paper

| Element | Paper | Here |
|---|---|---|
| Controller | Fig. 1: move; on a wall, turn randomly; on a robot, wait w(e), then turn randomly | [src/beeclust.c](src/beeclust.c) |
| Sensor value | Eq. 1: e = θE, saturating at e_max | same |
| Waiting time | Eq. 2: w = w_max / (1 + exp(−(e − o)σ)) | same |
| Constants | Table 1: w_max = 60 s, e_max = 180, E_max = 1000 lux, θ = 0.18, o = 147, σ = 0.5 | same |
| Environment | 500 lux ambient, light spot of 1000 lux, shadow spot of 0 lux (Fig. 4) | fitted field, see below |
| Target zone | 600–1000 lux | same |
| Protocol | 12 swarm sizes from 2 to 120, 6 runs of 4 min each | same |
| FA | fraction of robots waiting in the target zone, last minute | same |
| TA50 | time until 50 % of robots aggregated in the target zone | same |

**Erratum.** Eq. 2 is printed with exponent −(e + o)σ, which gives a constant
w ≈ w_max. Fig. 3, where waiting starts near 800 lux (e ≈ o), shows that
−(e − o)σ is meant. The latter is used.

**Light field.** The paper gives the field only as a figure. The sensor profile
of Fig. 4B was digitized ([data/bodi2009_fig4b.csv](data/bodi2009_fig4b.csv)) and
fitted with [scripts/fit_light_field.py](scripts/fit_light_field.py). An
exponential spot profile fits best (RMSE 2.8 sensor units, 1.6 % of the range):

E = clip(500 + 731.6 · (exp(−d_L / 6.23) − exp(−d_S / 6.23)), 0, 1000) lux,

with d_L and d_S the distances in patches to the light spot (x = −14) and the
shadow spot (x = +14). The arena interior is 48 × 27 patches (Fig. 4A).

## Adaptations to the Kilobot

The Jasmine III robots of the paper have directional infrared proximity sensors
and a light sensor. Kilobots have neither proximity sensing nor message bearing,
so the following choices were made. Each is a single named constant in the code.

| Paper (Jasmine III) | Kilobot | Constant |
|---|---|---|
| Robot vs. wall told apart by the robot's IR emission | Robot contact: a neighbour's message received from ≤ 52 mm (see below). Wall contact: a virtual sensor, sent as an overhead-controller message when a wall is ahead within 5 mm of the body, as ARK does for physical Kilobots | `CONTACT_DISTANCE_MM`, `WALL_SENSING_GAP` |
| Light sensor | Virtual sensor written into `get_ambientlight()`, 1 count = 1 lux | `LUX_PER_COUNT` |
| Directional proximity sensing | Kilobot messages are omnidirectional, so a robot leaving a partner would sense it again at once. After waiting, contacts are ignored until the robot has driven one body length | `ESCAPE_DISTANCE_MM` |
| One patch ≈ one robot body | One patch = one Kilobot diameter (33 mm); arena 1.584 m × 0.891 m | `--footprint` |
| Robot speed (not reported) | Kilobot speed 11.3 mm/s; time is rescaled, see below | `BEECLUST_TIME_SCALE` |

The ARGoS Kilobot light sensor is not used: it models a lamp at robot height,
is directional and is shadowed by neighbours, whereas BEECLUST assumes an
overhead illuminance field.

**Reference point of the Kilobot model.** The ARGoS Kilobot's position (its
origin anchor) lies on the leg axis, 9.2 mm behind the centre of the round body,
and message distances are measured between these points. Two touching robots
therefore measure 15–51 mm depending on their headings, and the contact
threshold is set to 52 mm so that every contact is detected. Light, walls and
target-zone membership use the body centre. A two-robot test (robots placed
head-on in the light spot) confirmed that both detect the contact and wait.

**Waiting state.** The loop functions classify a robot as waiting by its LED
colour (blue waiting, red driving, as in Fig. 2), as an overhead camera would.

## Time scale

The speed of the paper's simulated robots is not reported. Kilobots are slow
(about 1 cm/s), so all durations are multiplied by one factor k: the maximum
waiting time, the run length and the measurement window. Space is scaled by
robot size, so swarm densities match the paper.

k is the only fitted parameter. It is calibrated on a single data point, the
aggregation time of 9 robots (TA50 = 20 s, Fig. 7). All other values are then
predictions: FA for all 12 swarm sizes, the optimum swarm size, and TA50 for
the other sizes.

| k | 10 | 20 | **30** | 40 | 60 |
|---|--:|--:|--:|--:|--:|
| TA50 at N = 9 [paper s], median of 6 runs | 54.6 | 24.9 | **19.0** | 13.3 | 11.3 |

k = 30 is used. It implies that the robots simulated in the paper moved about
30 times faster than a Kilobot (≈ 34 cm/s, ≈ 10 body lengths per second).

## Layout

```
src/beeclust.c                     Kilobot controller (kilolib C)
src/beeclust_loop_functions.cpp    environment: virtual sensors, measurements
src/beeclust_protocol.h            message types and LED colours shared by both
experiments/beeclust.argos.in      ARGoS experiment template
data/                              values digitized from the paper
scripts/fit_light_field.py         fit of the light field to Fig. 4B
scripts/run_experiments.py         builds and runs the experiments of one configuration
scripts/analyze.py                 FA and TA50, comparison with the paper
scripts/reproduce_all.sh           all runs and analyses reported below
scripts/install_argos.sh, env.sh   ARGoS installation without root rights
```

## Running

```bash
sudo apt install build-essential cmake git pkg-config \
  libfreeimage-dev libfreeimageplus-dev qtbase5-dev libqt5opengl5-dev \
  freeglut3-dev libxi-dev libxmu-dev liblua5.3-dev lua5.3 python3-matplotlib
scripts/install_argos.sh                 # ARGoS 3.0.0-beta59 + Kilobot plugin
scripts/reproduce_all.sh                 # every run and analysis below (≈ 2 h, 16 cores)

source scripts/env.sh                    # watch one run in the ARGoS GUI
scripts/run_experiments.py --time-scale 30 --robots 9 --visualize
```

A configuration is named by its parameters, e.g. `k30` (baseline) or
`k25_f1.2` (time scale 25, footprint 1.2). Each run writes
`results/<configuration>/robots<N>_run<i>.csv`, one row per simulated second
with the columns `time_s`, `waiting`, `waiting_in_zone`, `in_zone` and
`robots`. `build/` is generated. ARGoS cannot open configuration paths that
contain spaces, so the runner starts it from the configuration's directory.

## Results

Time scale k = 30, 6 runs per swarm size (72 runs). FA as median [Q1, Q3];
TA50 as median in paper seconds (240 = not reached).

| N | FA paper | FA Kilobot | TA50 paper | TA50 Kilobot |
|--:|:--|:--|--:|--:|
| 2 | 0.16 [0.00, 0.37] | 0.00 [0.00, 0.00] | 240 | 120 |
| 3 | 0.21 [0.17, 0.49] | 0.46 [0.07, 0.69] | 240 | 166 |
| 6 | 0.63 [0.60, 0.68] | 0.87 [0.71, 0.89] | 25 | 25 |
| 9 | 0.80 [0.76, 0.84] | 0.86 [0.83, 0.91] | 20 | 19 (calibrated) |
| 12 | 0.75 [0.65, 0.80] | 0.92 [0.89, 0.94] | – | 22 |
| 18 | 0.75 [0.73, 0.78] | 0.97 [0.95, 0.98] | 25 | 13 |
| 24 | 0.72 [0.67, 0.73] | 0.93 [0.92, 0.95] | – | 13 |
| 33 | 0.65 [0.63, 0.70] | 0.93 [0.93, 0.94] | 30 | 21 |
| 42 | 0.64 [0.62, 0.66] | 0.91 [0.91, 0.91] | – | 13 |
| 60 | 0.49 [0.48, 0.50] | 0.84 [0.84, 0.86] | – | 18 |
| 100 | 0.33 [0.32, 0.34] | 0.68 [0.67, 0.69] | – | 27 |
| 120 | 0.28 [0.27, 0.29] | 0.62 [0.61, 0.63] | – | 46 |

![FA vs. swarm size](results/fig5_k30.png)

**Reproduced (qualitatively).**
- BEECLUST aggregates a swarm in the bright zone without gradient sensing.
- Aggregation fails for very small swarms and rises steeply up to N = 6–9.
- There is an optimal swarm size, beyond which aggregation declines as density
  grows.
- Aggregation times of 6–33 robots lie within 20–30 paper seconds as in Fig. 7,
  except N = 18 (13 s vs. 25 s).

**Not reproduced (quantitatively).**
- The optimum lies at N = 18 (FA = 0.97) instead of N = 9 (FA = 0.80).
- Kilobots aggregate more completely at every N ≥ 6 (by 0.06 to 0.35).
- The decline at large N is about half as steep: FA = 0.62 at N = 120 vs. 0.28.
- Swarms of 2 and 3 robots reach TA50 within the run in some cases, while the
  paper reports no aggregation for them.

**Possible causes (not tested).** Each would shift the curve towards the
paper's, but none has been checked here:
1. *Robot footprint.* One patch is assumed to equal one robot body. If the
   Jasmine III occupied more than one patch in SMARS (Fig. 2 suggests about
   1.1–1.2 patches), its swarms were denser, jammed earlier and peaked at a
   smaller N.
2. *Contact range.* The 52 mm threshold makes some near misses count as
   contacts, which raises the encounter rate and favours aggregation.
3. *Collision physics.* Kilobots in ARGoS push each other aside. SMARS is a
   NetLogo model whose collision handling is not described, and could jam more
   strongly.

Separating these would require a sensitivity analysis over the robot footprint
and the contact threshold.
