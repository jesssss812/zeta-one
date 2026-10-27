"""Statistics for the evaluation, standard library only: Wilson intervals, the discordant table,
pooled exact McNemar and Cohen's kappa with a bootstrap interval."""

import math
import random
from collections.abc import Sequence

Z95 = 1.959963984540054


def wilson(successes: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for a proportion. With n = 0 it is the uninformative (0, 1)."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def rate(successes: int, n: int) -> dict:
    low, high = wilson(successes, n)
    return {"k": successes, "n": n, "rate": successes / n if n else None, "low": low, "high": high}


def discordant(correct_a: Sequence[bool], correct_b: Sequence[bool]) -> dict[str, int]:
    """Counts over the same cases: both right, only A right, only B right, both wrong."""
    if len(correct_a) != len(correct_b):
        raise ValueError("the two configurations must cover the same cases")
    table = {"both": 0, "only_a": 0, "only_b": 0, "neither": 0}
    for a, b in zip(correct_a, correct_b):
        table["both" if a and b else "only_a" if a else "only_b" if b else "neither"] += 1
    return table


def mcnemar_exact(only_a: int, only_b: int) -> float:
    """Two-sided exact McNemar p-value: a binomial test of the discordant pairs against 1/2."""
    n = only_a + only_b
    if n == 0:
        return 1.0
    k = min(only_a, only_b)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def pooled_mcnemar(tables: Sequence[dict[str, int]]) -> dict:
    """Sum the discordant counts of several categories, then test once."""
    only_a = sum(t["only_a"] for t in tables)
    only_b = sum(t["only_b"] for t in tables)
    return {"only_a": only_a, "only_b": only_b, "p": mcnemar_exact(only_a, only_b)}


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    """Cohen's kappa; None when chance agreement is 1 and kappa is undefined."""
    if len(a) != len(b):
        raise ValueError("the two label lists must be the same length")
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    expected = sum((a.count(label) / n) * (b.count(label) / n) for label in set(a) | set(b))
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def kappa_bootstrap(a: Sequence[str], b: Sequence[str], resamples: int = 2000, seed: int = 0) -> dict:
    """Kappa with a percentile 95% interval over resampled cases; raw agreement alongside."""
    n = len(a)
    rng = random.Random(seed)
    values = []
    for _ in range(resamples):
        picks = [rng.randrange(n) for _ in range(n)]
        kappa = cohen_kappa([a[i] for i in picks], [b[i] for i in picks])
        if kappa is not None:
            values.append(kappa)
    values.sort()
    low = values[int(0.025 * len(values))] if values else None
    high = values[min(len(values) - 1, int(0.975 * len(values)))] if values else None
    return {
        "n": n,
        "agreement": sum(x == y for x, y in zip(a, b)) / n if n else None,
        "kappa": cohen_kappa(a, b),
        "low": low,
        "high": high,
        "resamples": resamples,
        "seed": seed,
    }


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear-interpolation percentile, q in [0, 100]."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)
