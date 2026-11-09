"""
NeuroEvolution of Augmenting Topologies (NEAT), after

  K. O. Stanley and R. Miikkulainen (2002). Evolving neural networks through augmenting
  topologies. Evolutionary Computation 10(2):99-127.

The algorithm follows the paper (Secs. 3 and 4.1). Values the paper does not state are
taken from the parameter file test.ne of Stanley's C++ release (NEAT 1.1, 2002) and are
marked "C++" below. README.md lists where this implementation and the C++ release differ.
"""
import math
import random
from dataclasses import dataclass, field


@dataclass
class Parameters:
    population_size: int = 150
    c1: float = 1.0                       # excess genes
    c2: float = 1.0                       # disjoint genes
    c3: float = 0.4                       # mean weight difference of matching genes
    compatibility_threshold: float = 3.0
    stagnation_generations: int = 15      # no offspring after this many without improvement
    stagnation_penalty: float = 0.01      # C++: fitness factor that implements the above
    refocus_generations: int = 20         # footnote 2: then only the top two species breed
    champion_min_species_size: int = 6    # "more than five networks"
    weight_mutation_prob: float = 0.8
    weight_perturb_prob: float = 0.9      # otherwise the weight is replaced
    weight_power: float = 2.5             # C++ weight_mut_power: perturbations in [-2.5, 2.5]
    weight_cap: float = 8.0               # C++ genome.cpp
    disable_inherited_prob: float = 0.75
    mutation_only_prob: float = 0.25
    interspecies_mating_prob: float = 0.001
    add_node_prob: float = 0.03
    add_link_prob: float = 0.05
    new_link_tries: int = 20              # C++ newlink_tries
    survival_fraction: float = 0.2        # C++ survival_thresh: parents per species
    crossover_average_prob: float = 0.4   # C++ mate_multipoint_avg_prob, else pick a parent's gene
    mate_only_prob: float = 0.2           # C++: crossover offspring left unmutated
    sigmoid_slope: float = 4.924273       # "4.9" in the paper, C++ network.cpp
    recurrent: bool = False


@dataclass
class Connection:
    source: int
    target: int
    weight: float
    enabled: bool
    innovation: int


@dataclass
class Genome:
    inputs: list                          # node ids of inputs, bias last
    outputs: list
    hidden: list = field(default_factory=list)
    connections: dict = field(default_factory=dict)   # innovation -> Connection
    fitness: float = 0.0

    def copy(self):
        return Genome(list(self.inputs), list(self.outputs), list(self.hidden),
                      {k: Connection(**vars(c)) for k, c in self.connections.items()})

    def enabled(self):
        return [c for c in self.connections.values() if c.enabled]


class Innovations:
    """Global innovation numbers. Identical structural mutations within one generation
    receive the same numbers (Sec. 3.2)."""

    def __init__(self, next_node, next_innovation):
        self.next_node, self.next_innovation = next_node, next_innovation
        self.links, self.splits = {}, {}

    def new_generation(self):
        self.links, self.splits = {}, {}

    def link(self, source, target):
        if (source, target) not in self.links:
            self.links[(source, target)] = self.next_innovation
            self.next_innovation += 1
        return self.links[(source, target)]

    def split(self, innovation):
        """Node id and the two connection innovations for splitting a connection."""
        if innovation not in self.splits:
            self.splits[innovation] = (self.next_node, self.next_innovation, self.next_innovation + 1)
            self.next_node += 1
            self.next_innovation += 2
        return self.splits[innovation]


# --------------------------------------------------------------------------- network

class Network:
    """Feed-forward evaluation in topological order. A node without enabled incoming
    connections outputs 0, as in the C++ release, where such a node is never activated."""

    def __init__(self, genome, slope):
        self.inputs, self.outputs, self.slope = genome.inputs, genome.outputs, slope
        incoming = {}
        for c in genome.enabled():
            incoming.setdefault(c.target, []).append((c.source, c.weight))
        self.order = [(node, incoming[node]) for node in topological_order(genome)
                      if node in incoming]

    def activate(self, values):
        activation = dict(zip(self.inputs, values))
        for node, sources in self.order:
            total = sum(activation.get(s, 0.0) * w for s, w in sources)
            activation[node] = 1.0 / (1.0 + math.exp(-self.slope * max(min(total, 60.0), -60.0)))
        return [activation.get(o, 0.0) for o in self.outputs]


def topological_order(genome):
    targets = {}
    for c in genome.enabled():
        targets.setdefault(c.source, []).append(c.target)
    order, seen = [], set()

    def visit(node):
        if node in seen:
            return
        seen.add(node)
        for t in targets.get(node, []):
            visit(t)
        order.append(node)

    for node in genome.inputs + genome.hidden + genome.outputs:
        visit(node)
    return [n for n in reversed(order) if n not in genome.inputs]


def creates_cycle(genome, source, target):
    """Would the connection source -> target close a loop of enabled connections?"""
    if source == target:
        return True
    targets = {}
    for c in genome.connections.values():
        targets.setdefault(c.source, []).append(c.target)
    stack, seen = [target], set()
    while stack:
        node = stack.pop()
        if node == source:
            return True
        if node not in seen:
            seen.add(node)
            stack.extend(targets.get(node, []))
    return False


# --------------------------------------------------------------------------- operators

def compatibility(a, b, p):
    """Eq. 1 with N = 1, as allowed for small genomes and used in the C++ release."""
    ia, ib = sorted(a.connections), sorted(b.connections)
    if not ia or not ib:
        return p.c1 * max(len(ia), len(ib))
    cutoff = min(ia[-1], ib[-1])
    matching = set(ia) & set(ib)
    unmatched = set(ia) ^ set(ib)
    excess = sum(1 for i in unmatched if i > cutoff)
    disjoint = len(unmatched) - excess
    w = (sum(abs(a.connections[i].weight - b.connections[i].weight) for i in matching)
         / len(matching)) if matching else 0.0
    return p.c1 * excess + p.c2 * disjoint + p.c3 * w


def crossover(mother, father, p, rng):
    """Matching genes from either parent (or averaged), disjoint and excess genes from
    the fitter parent; on equal fitness the smaller genome counts as fitter (C++)."""
    if (father.fitness, -len(father.connections)) > (mother.fitness, -len(mother.connections)):
        mother, father = father, mother
    average = rng.random() < p.crossover_average_prob
    child = Genome(list(mother.inputs), list(mother.outputs))
    for innovation, gene in mother.connections.items():
        other = father.connections.get(innovation)
        new = Connection(**vars(gene))
        if other is not None:
            if average:
                new.weight = (gene.weight + other.weight) / 2
            elif rng.random() < 0.5:
                new.weight = other.weight
            disabled = not gene.enabled or not other.enabled
            new.enabled = not (disabled and rng.random() < p.disable_inherited_prob)
        child.connections[innovation] = new
    nodes = {n for c in child.connections.values() for n in (c.source, c.target)}
    child.hidden = sorted(nodes - set(child.inputs) - set(child.outputs))
    return child


def mutate_weights(genome, p, rng):
    for c in genome.connections.values():
        delta = rng.uniform(-p.weight_power, p.weight_power)
        c.weight = c.weight + delta if rng.random() < p.weight_perturb_prob else delta
        c.weight = max(-p.weight_cap, min(p.weight_cap, c.weight))


def mutate_add_node(genome, innovations, rng):
    """Split an enabled connection: in -> new weighted 1, new -> out keeps the weight.
    Connections from the bias are never split (C++ genome.cpp, not stated in the paper)."""
    candidates = [c for c in genome.enabled() if c.source != genome.inputs[-1]]
    if not candidates:
        return
    old = rng.choice(candidates)
    node, first, second = innovations.split(old.innovation)
    if node in genome.hidden:
        return  # this connection was already split the same way
    old.enabled = False
    genome.hidden.append(node)
    genome.connections[first] = Connection(old.source, node, 1.0, True, first)
    genome.connections[second] = Connection(node, old.target, old.weight, True, second)


def mutate_add_link(genome, innovations, p, rng):
    sources = genome.inputs + genome.hidden + (genome.outputs if p.recurrent else [])
    targets = genome.hidden + genome.outputs
    existing = {(c.source, c.target) for c in genome.connections.values()}
    for _ in range(p.new_link_tries):
        source, target = rng.choice(sources), rng.choice(targets)
        if (source, target) in existing:
            continue
        if not p.recurrent and creates_cycle(genome, source, target):
            continue
        innovation = innovations.link(source, target)
        genome.connections[innovation] = Connection(source, target, rng.uniform(-1, 1), True,
                                                    innovation)
        return


def mutate(genome, innovations, p, rng):
    """One structural mutation, or otherwise a possible weight mutation (C++ order)."""
    if rng.random() < p.add_node_prob:
        mutate_add_node(genome, innovations, rng)
    elif rng.random() < p.add_link_prob:
        mutate_add_link(genome, innovations, p, rng)
    elif rng.random() < p.weight_mutation_prob:
        mutate_weights(genome, p, rng)


# --------------------------------------------------------------------------- evolution

@dataclass
class Species:
    representative: Genome
    members: list = field(default_factory=list)
    best_fitness: float = -math.inf
    last_improved: int = 0


class Population:

    def __init__(self, start, params, rng):
        """start: the minimal genome (inputs fully connected to outputs, no hidden nodes)."""
        self.p, self.rng = params, rng
        nodes = start.inputs + start.outputs + start.hidden
        self.innovations = Innovations(max(nodes) + 1, max(start.connections) + 1)
        self.genomes = []
        for _ in range(params.population_size):
            genome = start.copy()
            for c in genome.connections.values():   # C++: random initial weights
                c.weight = rng.uniform(-1.0, 1.0)
            self.genomes.append(genome)
        self.species, self.generation = [], 0
        self.best_fitness, self.best_last_improved = -math.inf, 0

    def speciate(self):
        for s in self.species:
            s.members = []
        for genome in self.genomes:
            for s in self.species:
                if compatibility(genome, s.representative, self.p) < self.p.compatibility_threshold:
                    s.members.append(genome)
                    break
            else:
                self.species.append(Species(genome, [genome], last_improved=self.generation))
        self.species = [s for s in self.species if s.members]

    def evaluate(self, fitness):
        """Evaluate genomes in order; stop at the first that solves the task.
        Returns (solver or None, number of evaluations)."""
        for k, genome in enumerate(self.genomes, start=1):
            genome.fitness, solved = fitness(Network(genome, self.p.sigmoid_slope))
            if solved:
                return genome, k
        return None, len(self.genomes)

    def reproduce(self):
        p, rng = self.p, self.rng
        self.generation += 1
        self.innovations.new_generation()
        self.speciate()

        best = max(self.genomes, key=lambda g: g.fitness).fitness
        if best > self.best_fitness:
            self.best_fitness, self.best_last_improved = best, self.generation
        for s in self.species:
            s.members.sort(key=lambda g: g.fitness, reverse=True)
            if s.members[0].fitness > s.best_fitness:
                s.best_fitness, s.last_improved = s.members[0].fitness, self.generation

        # Explicit fitness sharing; stagnant species are penalised.
        shares = []
        for s in self.species:
            penalty = (p.stagnation_penalty
                       if self.generation - s.last_improved > p.stagnation_generations else 1.0)
            shares.append(sum(max(g.fitness, 0.0) for g in s.members) / len(s.members) * penalty)
        if self.generation - self.best_last_improved > p.refocus_generations:
            top = sorted(range(len(self.species)), key=lambda i: -self.species[i].best_fitness)[:2]
            shares = [shares[i] if i in top else 0.0 for i in range(len(shares))]
            for i in top:  # restart their stagnation clocks, as in the C++ release
                self.species[i].last_improved = self.generation
            self.best_last_improved = self.generation
        offspring = allocate(shares, p.population_size)

        children = []
        for s, count in zip(self.species, offspring):
            if count == 0:
                continue
            if len(s.members) >= p.champion_min_species_size:
                children.append(s.members[0].copy())
                count -= 1
            parents = s.members[:int(p.survival_fraction * len(s.members)) + 1]
            for _ in range(count):
                children.append(self.offspring(parents))
        for s in self.species:
            s.representative = rng.choice(s.members)
        self.species = [s for s, count in zip(self.species, offspring) if count > 0]
        self.genomes = children

    def offspring(self, parents):
        p, rng = self.p, self.rng
        mother = rng.choice(parents)
        if rng.random() < p.mutation_only_prob:
            child = mother.copy()
            mutate(child, self.innovations, p, rng)
            return child
        if rng.random() < p.interspecies_mating_prob and len(self.species) > 1:
            father = rng.choice(self.species).members[0]
        else:
            father = rng.choice(parents)
        child = crossover(mother, father, p, rng)
        if rng.random() > p.mate_only_prob or father is mother:
            mutate(child, self.innovations, p, rng)
        return child


def allocate(shares, total):
    """Offspring per species proportional to the shares, rounded by largest remainder."""
    if sum(shares) <= 0:
        shares = [1.0] * len(shares)
    quotas = [total * s / sum(shares) for s in shares]
    counts = [int(q) for q in quotas]
    for i in sorted(range(len(quotas)), key=lambda i: counts[i] - quotas[i])[:total - sum(counts)]:
        counts[i] += 1
    return counts


def evolve(start, fitness, params=None, max_generations=1000, seed=None):
    """Run NEAT until a network solves the task. Returns (solver or None, generation,
    evaluations): the generation of the solution and the networks evaluated up to it."""
    params, rng = params or Parameters(), random.Random(seed)
    population = Population(start, params, rng)
    evaluations = 0
    for generation in range(1, max_generations + 1):
        solver, count = population.evaluate(fitness)
        evaluations += count
        if solver is not None:
            return solver, generation, evaluations
        population.reproduce()
    return None, max_generations, evaluations


def minimal_genome(n_inputs, n_outputs=1):
    """Inputs (bias last) fully connected to the outputs, no hidden nodes (Sec. 3.4)."""
    inputs, outputs = list(range(n_inputs)), list(range(n_inputs, n_inputs + n_outputs))
    genome = Genome(inputs, outputs)
    innovation = 0
    for o in outputs:
        for i in inputs:
            genome.connections[innovation] = Connection(i, o, 0.0, True, innovation)
            innovation += 1
    return genome
