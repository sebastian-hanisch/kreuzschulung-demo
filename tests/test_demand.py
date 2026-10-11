"""Bedarfsszenarien: Verteilungen gegen scipy.stats, gemeinsame Schwankung, Struktur, gepaarte Ströme, Präfix-Eigenschaft."""

import itertools
import math

import numpy as np
import pytest

import kzs_demand as DM
from kzs_rng import seed_aus, uniformen  # noqa: F401


def test_poisson_moments_and_chi_square_against_scipy():
    stats = pytest.importorskip("scipy.stats")
    for mu in (0.5, 5, 20, 50):
        u = uniformen(seed_aus("t2p", mu), 60000)
        x = DM.poisson_inversion(u, float(mu))
        assert abs(x.mean() - mu) < 5 * math.sqrt(mu / len(x))
        assert abs(x.var() / mu - 1) < 0.05
        ks = np.arange(0, int(x.max()) + 1)
        erw = stats.poisson.pmf(ks, mu) * len(x)
        beob = np.bincount(x.astype(int), minlength=len(ks))
        m = erw >= 10
        chi2 = ((beob[m] - erw[m]) ** 2 / erw[m]).sum()
        assert chi2 < m.sum() + 5 * math.sqrt(2 * m.sum())


def test_gamma_poisson_has_the_negative_binomial_moments():
    for mu, k in ((5, 10), (20, 4), (50, 4)):
        D = DM.bedarf(3, mu, k, 0.0, N=40000, block=9, schluessel="t2nb")
        x = D[:, 0]
        var = mu + mu * mu / k
        assert abs(x.mean() - mu) < 5 * math.sqrt(var / len(x))
        assert abs(x.var() / var - 1) < 0.06
        assert abs(np.corrcoef(D[:, 0], D[:, 1])[0, 1]) < 0.03


def test_common_fluctuation_keeps_the_marginals_and_gives_the_theoretical_correlation():
    for mu, k in ((20, 10), (20, 4)):
        D = DM.bedarf(4, mu, k, 0.5, N=60000, block=3, schluessel="t2c")
        var = mu + mu * mu / k
        assert abs(D[:, 0].mean() - mu) < 5 * math.sqrt(var / D.shape[0])
        assert abs(D[:, 0].var() / var - 1) < 0.06
        rho = np.mean([np.corrcoef(D[:, a], D[:, b])[0, 1] for a, b in itertools.combinations(range(4), 2)])
        assert abs(rho - 0.5 * (mu / k) / (1 + mu / k)) < 0.015


def test_common_fluctuation_needs_overdispersion_and_even_shape():
    with pytest.raises(ValueError):
        DM.bedarf(3, 20, None, 0.5, N=10)
    with pytest.raises(ValueError):
        DM.bedarf(3, 20, 5, 0.5, N=10)


def test_the_first_rows_of_a_smaller_count_are_the_same_scenarios():
    for disp, korr, imb in ((None, 0.0, None), (10, 0.0, None), (4, 0.5, None), (None, 0.0, ("block", 0.5))):
        sk = DM.skala_aus(6, imb)
        a = DM.bedarf(6, 20, disp, korr, N=3000, skala=sk)
        b = DM.bedarf(6, 20, disp, korr, N=300, skala=sk)
        assert np.array_equal(a[:300], b)


def test_streams_are_deterministic_and_blocks_differ():
    a = DM.bedarf(4, 10, 4, 0.0, N=200, block=0)
    assert np.array_equal(a, DM.bedarf(4, 10, 4, 0.0, N=200, block=0))
    assert not np.array_equal(a, DM.bedarf(4, 10, 4, 0.0, N=200, block=1))


def test_demand_does_not_depend_on_capacity_or_design_key():
    """Die Strömen fehlen r, g und der Entwurf im Schlüssel: gleiche Argumente ergeben dieselben Szenarien (Paarung)."""
    import inspect
    assert "r" not in inspect.signature(DM.bedarf).parameters and "g" not in inspect.signature(DM.bedarf).parameters


def test_structure_hand_values_and_total_demand_is_kept():
    assert DM.skala_aus(6, ("block", 0.5)) == [1.5, 1.5, 1.5, 0.5, 0.5, 0.5]
    assert DM.skala_aus(6, ("alt", 0.25)) == [1.25, 0.75, 1.25, 0.75, 1.25, 0.75]
    assert DM.skala_aus(4, None) == [1.0] * 4
    for n in (2, 3, 4, 6, 8, 12):
        for imb in (("block", 0.25), ("block", 0.5), ("alt", 0.25), ("alt", 0.5)):
            assert sum(DM.skala_aus(n, imb)) == pytest.approx(n)
    assert DM.skala_aus(3, ("block", 0.5)) == [1.5, 1.0, 0.5]
    assert DM.skala_aus(3, ("alt", 0.5)) == [1.5, 0.5, 1.0]


def test_structure_shifts_the_station_means():
    D = DM.bedarf(6, 20, None, 0.0, N=20000, skala=DM.skala_aus(6, ("block", 0.5)))
    m = D.mean(axis=0)
    assert m[:3].mean() == pytest.approx(30, rel=0.01) and m[3:].mean() == pytest.approx(10, rel=0.02)
