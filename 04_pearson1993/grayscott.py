"""
Gray-Scott reaction-diffusion model as simulated by Pearson (1993):

    dU/dt = Du lap(U) - U V^2 + F (1 - U)
    dV/dt = Dv lap(V) + U V^2 - (F + k) V

on a periodic 2.5 x 2.5 square, Du = 2e-5, Dv = 1e-5, a 256 x 256 mesh, the five-point
Laplacian and forward Euler with time step 1.
"""
import numpy as np
from scipy.ndimage import convolve

SIZE, MESH, DU, DV = 2.5, 256, 2e-5, 1e-5
FIVE_POINT = np.array([[0.0, 1.0, 0.0], [1.0, -4.0, 1.0], [0.0, 1.0, 0.0]])


def laplacian(a, h):
    return convolve(a, FIVE_POINT, mode="wrap") / h ** 2


def initial_state(rng, mesh=MESH, square=20, noise=0.01):
    """U = 1, V = 0 except for a central square of 20 x 20 mesh points at U = 1/2,
    V = 1/4; then +-1 % random noise (multiplicative) to break the square symmetry."""
    u, v = np.ones((mesh, mesh)), np.zeros((mesh, mesh))
    lo = (mesh - square) // 2
    u[lo:lo + square, lo:lo + square] = 0.5
    v[lo:lo + square, lo:lo + square] = 0.25
    u *= 1 + rng.uniform(-noise, noise, u.shape)
    v *= 1 + rng.uniform(-noise, noise, v.shape)
    return u, v


class GrayScott:
    def __init__(self, F, k, u, v, size=SIZE, dt=1.0):
        self.F, self.k, self.u, self.v, self.dt = F, k, u, v, dt
        self.h = size / u.shape[0]
        self.t = 0.0

    def step(self, n=1):
        F, k, h, dt = self.F, self.k, self.h, self.dt
        for _ in range(n):
            u, v = self.u, self.v
            uvv = u * v * v
            self.u = u + dt * (DU * laplacian(u, h) - uvv + F * (1 - u))
            self.v = v + dt * (DV * laplacian(v, h) + uvv - (F + k) * v)
        self.t += n * dt
