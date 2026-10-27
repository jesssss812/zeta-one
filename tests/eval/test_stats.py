import pytest

from eval import stats


def test_wilson_known_values():
    low, high = stats.wilson(85, 100)
    assert low == pytest.approx(0.7672, abs=1e-3)
    assert high == pytest.approx(0.9069, abs=1e-3)


def test_wilson_edges():
    low, high = stats.wilson(10, 10)
    assert low == pytest.approx(0.7225, abs=1e-3)
    assert high == pytest.approx(1.0)
    assert stats.wilson(0, 10)[0] == 0.0
    assert stats.wilson(0, 0) == (0.0, 1.0)


def test_wilson_about_twelve_points_at_thirty():
    low, high = stats.wilson(26, 30)
    assert (high - low) / 2 == pytest.approx(0.12, abs=0.02)


def test_discordant_table():
    table = stats.discordant([True, True, False, False, True], [True, False, True, False, False])
    assert table == {"both": 1, "only_a": 2, "only_b": 1, "neither": 1}


def test_discordant_needs_same_cases():
    with pytest.raises(ValueError):
        stats.discordant([True], [True, False])


def test_mcnemar_known_values():
    assert stats.mcnemar_exact(0, 0) == 1.0
    assert stats.mcnemar_exact(5, 5) == 1.0
    assert stats.mcnemar_exact(0, 10) == pytest.approx(2 / 1024)
    assert stats.mcnemar_exact(2, 8) == pytest.approx(0.109375)
    assert stats.mcnemar_exact(8, 2) == stats.mcnemar_exact(2, 8)


def test_pooled_mcnemar_sums_before_testing():
    tables = [{"only_a": 0, "only_b": 4}, {"only_a": 1, "only_b": 5}]
    pooled = stats.pooled_mcnemar(tables)
    assert (pooled["only_a"], pooled["only_b"]) == (1, 9)
    assert pooled["p"] == pytest.approx(stats.mcnemar_exact(1, 9))


def test_kappa_known_values():
    a = ["x"] * 20 + ["x"] * 5 + ["y"] * 10 + ["y"] * 15
    b = ["x"] * 20 + ["y"] * 5 + ["x"] * 10 + ["y"] * 15
    assert stats.cohen_kappa(a, b) == pytest.approx(0.4)


def test_kappa_perfect_and_undefined():
    assert stats.cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    assert stats.cohen_kappa(["a", "a"], ["a", "a"]) is None
    assert stats.cohen_kappa([], []) is None


def test_kappa_bootstrap_brackets_the_estimate_and_is_seeded():
    a = ["allow", "challenge", "block"] * 14
    b = list(a)
    for i in range(0, 42, 7):
        b[i] = "block" if a[i] != "block" else "allow"
    result = stats.kappa_bootstrap(a, b, resamples=500, seed=3)
    assert result["low"] <= result["kappa"] <= result["high"]
    assert result["n"] == 42
    assert stats.kappa_bootstrap(a, b, resamples=500, seed=3) == result


def test_percentile():
    assert stats.percentile([1, 2, 3, 4], 50) == 2.5
    assert stats.percentile([5], 95) == 5
    assert stats.percentile([], 50) is None
    assert stats.percentile(list(range(101)), 95) == 95
