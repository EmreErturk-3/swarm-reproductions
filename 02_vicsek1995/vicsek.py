"""
The self-driven particle model of Vicsek, Czirók, Ben-Jacob, Cohen & Shochet (1995),
Phys. Rev. Lett. 75:1226, as described in the paper (arXiv cond-mat/0611743).

N point particles move with constant speed v in a square box of side L with periodic
boundaries. At every time step (dt = 1) each particle takes the mean direction of all
particles within distance r of it, itself included, plus a noise angle drawn uniformly
from [-eta/2, eta/2] (Eq. 2). Positions advance with the velocity of the previous step,
x(t+1) = x(t) + v(t) (Eq. 1), the so-called backward update of the original model.
"""
import numpy as np
from scipy.spatial import cKDTree


class VicsekModel:

    def __init__(self, n, box, noise, speed=0.03, radius=1.0, seed=None):
        self.n, self.box, self.noise, self.speed, self.radius = n, box, noise, speed, radius
        self.rng = np.random.default_rng(seed)
        self.position = self.rng.uniform(0.0, box, (n, 2))
        self.angle = self.rng.uniform(-np.pi, np.pi, n)

    def step(self):
        cos, sin = np.cos(self.angle), np.sin(self.angle)
        # Eq. 2: mean direction of the neighbours within r, the particle itself included.
        tree = cKDTree(self.position, boxsize=self.box)
        i, j = tree.query_pairs(self.radius, output_type="ndarray").T
        sum_cos = cos + np.bincount(i, cos[j], self.n) + np.bincount(j, cos[i], self.n)
        sum_sin = sin + np.bincount(i, sin[j], self.n) + np.bincount(j, sin[i], self.n)
        noise = self.rng.uniform(-self.noise / 2, self.noise / 2, self.n)
        new_angle = np.arctan2(sum_sin, sum_cos) + noise
        # Eq. 1: the move uses the velocity of time t.
        self.position = np.mod(self.position + self.speed * np.column_stack((cos, sin)), self.box)
        self.position[self.position >= self.box] = 0.0  # guard against rounding to L
        self.angle = new_angle

    def order_parameter(self):
        """Eq. 3: v_a = |sum of velocities| / (N v), between 0 and 1."""
        return np.abs(np.exp(1j * self.angle).mean())

    def add_particles(self, count):
        """Add particles at random positions with random directions."""
        self.position = np.vstack((self.position, self.rng.uniform(0.0, self.box, (count, 2))))
        self.angle = np.concatenate((self.angle, self.rng.uniform(-np.pi, np.pi, count)))
        self.n += count


def block_means(model, steps, block):
    """Advance the model; return the mean v_a of each consecutive block of steps."""
    va = np.empty(steps)
    for t in range(steps):
        model.step()
        va[t] = model.order_parameter()
    return va.reshape(-1, block).mean(axis=1)


def order_parameter_series(n, box, noise, steps, block, seed):
    """One simulation from random initial conditions: block means of v_a."""
    return block_means(VicsekModel(n, box, noise, seed=seed), steps, block)


def noise_sweep(n, box, noises, steps, block, seed):
    """The protocol of Fig. 2a: one continuing simulation in which the noise is decreased
    step by step ("we gradually decreased the amount of noise"); block means of v_a for
    every noise value."""
    model = VicsekModel(n, box, noises[0], seed=seed)
    stages = []
    for noise in noises:
        model.noise = noise
        stages.append(block_means(model, steps, block))
    return stages


def density_sweep(box, counts, noise, steps, block, seed):
    """Fig. 2b as a continuing simulation in which the density is increased by adding
    particles; block means of v_a for every particle number."""
    model = VicsekModel(counts[0], box, noise, seed=seed)
    stages = []
    for count in counts:
        model.add_particles(count - model.n)
        stages.append(block_means(model, steps, block))
    return stages
