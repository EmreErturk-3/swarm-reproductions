# NEAT: NeuroEvolution of Augmenting Topologies

Reproduction of K. O. Stanley and R. Miikkulainen (2002). *Evolving neural networks
through augmenting topologies.* Evolutionary Computation 10(2):99–127.
[PDF](https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf)

NEAT evolves both the weights and the structure of neural networks. It starts from
networks with no hidden nodes and adds nodes and connections by mutation. It relies on
three mechanisms:

- historical markings (innovation numbers), which line up genes for crossover;
- speciation, which protects new structure until its weights are tuned;
- minimal initial structure, which keeps solutions small.

The paper tests NEAT on XOR and on double pole balancing.

## Implementation

[neat.py](neat.py) implements Secs. 3 and 4.1 of the paper. Values the paper does not
state are taken from `test.ne` and the source of Stanley's C++ release, and are marked
"C++" in the code. [experiments.py](experiments.py) contains the two benchmarks.

| Element | Value |
|---|---|
| Population | 150 |
| Compatibility | δ = E + D + 0.4 W̄ (N = 1), threshold δt = 3.0; each species is represented by a random member of the previous generation |
| Selection | explicit fitness sharing; the top 20 % of each species reproduce; the champion of each species with more than five members is copied unchanged |
| Stagnation | no offspring for a species that has not improved in 15 generations; only the top two species reproduce after 20 generations without improvement of the population |
| Reproduction | 25 % mutation only, otherwise crossover (interspecies 0.001); 20 % of crossover offspring are not mutated |
| Mutation | add node 0.03, else add connection 0.05, else 80 % chance of weight mutation: each weight perturbed uniformly in ±2.5 (90 %) or replaced (10 %), clipped to ±8 |
| Activation | 1 / (1 + e^(−4.924273 x)) |

### Differences from the C++ release

The paper is followed where the two differ:

- **Weight mutation.** The paper scheme is used. The C++ code mutates weights with
  probability 0.9 and sometimes uses a "severe" variant. Running XOR with 0.9 gave
  6,405 evaluations against 6,463.
- **Species representative.** The paper uses a random member. The C++ code compares
  new genomes with the previous champion of each species.
- **Champion copy.** The paper copies the champion if the species has more than five
  members. The C++ code copies it if the species gets more than five offspring.
- **Population stagnation.** Here only the top two species reproduce, by normal
  reproduction. The C++ code instead gives them half of the population each as
  clones of their champions, with mutated weights.
- **Species penalties.** The C++ code applies the stagnation penalty one generation
  early, and every 30 generations it also penalises the worst species older than 20
  generations. Neither is done here.
- **Network evaluation.** Networks are evaluated in topological order. The C++ code
  instead updates all nodes synchronously, repeated as often as the network is deep.
  Both give the same output for feed-forward networks.
- **Counting evaluations.** The C++ code counts a solver by its index within its
  species' offspring, not within the population. Its counts can therefore be lower,
  by less than one generation (150).

**One C++ rule the paper does not state is used:** a connection from the bias is never
split by an add-node mutation. Without this rule, early node additions often create a
hidden node fed only by the constant bias. That made XOR about 30 % slower (table
below).

## Results

### XOR (Sec. 4.2)

The paper setup:

- 2 inputs and a bias (1.0), each connected to 1 output.
- Fitness (4 − Σ|error|)².
- Solved when every output is on the correct side of 0.5.
- 100 runs.

| | Paper | Here | Here, bias connections split |
|---|---|---|---|
| Failures | 0 / 100 | 0 / 100 | 0 / 100 |
| Evaluations, mean (s.d.) | 4,755 (2,553) | 6,463 (4,259) | 8,525 (4,782) |
| Generations, mean | 32 | 43.6 | 57.3 |
| Worst run, evaluations | 13,459 | 24,188 | 23,316 |
| Hidden nodes, mean (s.d.) | 2.35 (1.11) | 3.88 (2.24) | 4.26 (2.75) |
| Enabled connections, mean | 7.48 | 14.13 | 15.84 |
| Runs with one hidden node | 22 | 10 | 11 |

The qualitative result is reproduced:

- NEAT solves XOR in every run.
- It starts from no hidden nodes and finds small networks.

The quantitative gap is clear. Here NEAT needs about 35 % more evaluations than the
paper (the standard error of the mean is about 430), and its networks are larger. Some
of the size difference follows from the longer runs: hidden nodes are added at about
the same rate per generation as in the paper (0.09 against 0.07).

None of the documented differences above closes the gap:

- the C++ weight mutation rate (0.9) changed nothing;
- the C++ choice of species representative, the previous champion, made results
  worse: 11,070 evaluations, measured before the bias rule was adopted.

The remaining difference therefore lies in a detail neither the paper nor this reading
of the C++ source identifies.

### Double pole balancing with velocities (Sec. 4.3.2)

| | Paper | Here |
|---|---|---|
| Failures | 0 / 120 | 0 / 120 |
| Evaluations, mean (s.d.) | 3,600 (2,704) | 3,542 (2,828) |
| Generations, mean | 24 | 24.2 |
| Worst run, evaluations | not reported | 17,295 |
| Hidden nodes, mean (range) | not reported | 1.73 (0–8) |

Reproduced. The mean number of evaluations is within 2 % of the paper's, well inside
one standard error (about 260). It is the harder of the two benchmarks, yet this one
matches and XOR does not. That suggests the XOR gap comes from a detail specific to
XOR rather than from the core algorithm.

The setup:

- The cart and poles follow the C++ release: Runge–Kutta with 0.01 s steps and a
  force every 0.02 s; the poles are 1 m and 0.1 m long, with masses 0.1 kg and
  0.01 kg.
- The long pole starts at 1° as stated in Sec. 4.3.1. The C++ release uses 0.07 rad.
- Inputs are scaled as in the C++ release, with a bias of 0.5.
- A network solves the task when it balances for 100,000 steps (30 min).

## Running

```bash
./experiments.py xor    # 100 runs, about 1 min on 4 cores; results/xor.csv
./experiments.py dpv    # 120 runs, about 40 min on 4 cores; results/dpv.csv
```

Runs that are already in the CSV are skipped. Seeds are the run numbers 0–99 (XOR) and
0–119 (DPV). Requires only Python 3.
