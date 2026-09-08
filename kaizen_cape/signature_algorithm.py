"""CAPE-Loop integer experiment-allocation reference contract."""

from itertools import product


def allocate_experiments(values, costs, budget, *, min_replicates=0, max_replicates=3, balance_tolerance=1):
    if len(values) != len(costs) or not values:
        raise ValueError("values and costs must have equal non-zero length")
    best = None
    for allocation in product(range(min_replicates, max_replicates + 1), repeat=len(values)):
        cost = sum(a * c for a, c in zip(allocation, costs))
        if cost > budget or max(allocation) - min(allocation) > balance_tolerance:
            continue
        value = sum(a * v for a, v in zip(allocation, values))
        row = {"allocations": allocation, "cost": cost, "information_value": value}
        if best is None or (value, -cost, allocation) > (best["information_value"], -best["cost"], best["allocations"]):
            best = row
    return best


def ablation(values, costs, budget, **kwargs):
    """Remove the balanced-allocation constraint for a declared ablation."""
    kwargs["balance_tolerance"] = max(len(values), 1)
    return allocate_experiments(values, costs, budget, **kwargs)


def sensitivity(values, costs, budget, multiplier=1.0, **kwargs):
    return allocate_experiments(values, costs, budget * float(multiplier), **kwargs)
