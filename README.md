# Swarm and evolutionary computation: paper reproductions

Classic papers from swarm robotics and evolutionary computation, each re-implemented from the
paper alone and run again. Each folder has its own README that compares the published results with
the ones measured here, including the parts that did **not** reproduce.

| | Paper | Status |
|---|---|---|
| [01_beeclust](01_beeclust/) | Bodi et al. (2009), *Robustness of two interacting robot swarms using the BEECLUST algorithm*: Kilobot aggregation in ARGoS (C) | Fig. 5 and Fig. 7 (N_S = 0) reproduced, shadow-finder experiments not yet; sensitivity runs paused |
| [02_vicsek1995](02_vicsek1995/) | Vicsek et al. (1995), *Novel type of phase transition in a system of self-driven particles* | simulation and figures done, write-up pending |
| [03_neat2002](03_neat2002/) | Stanley & Miikkulainen (2002), *Evolving neural networks through augmenting topologies* | XOR reproduced qualitatively (0/100 failures); about 35 % more evaluations than the paper |
| [04_pearson1993](04_pearson1993/) | Pearson (1993), *Complex patterns in a simple system* (Gray–Scott) | phase diagram and pattern figures reproduced |

More reproductions, in artificial life (Lenia, Flow-Lenia, Physarum, Kuramoto, MAP-Elites, Turing
patterns, …), are in [EvoMaxx](https://github.com/EmreErturk-3/evomaxx/tree/main/reproductions).
