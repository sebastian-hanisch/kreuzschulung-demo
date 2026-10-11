"""Orakel-Tests: Kernroutinen gegen einen ANDEREN Rechenweg (ORACLE-PLAYBOOK, DEMO-PLAYBOOK §12).

Gruppierter Min-Schnitt gegen Edmonds-Karp (reines Python), scipy.maximum_flow, Linearprogramm und vollständige Aufzählung aller ganzzahligen
Zuordnungen (n bis 4); geschlossene Extreme D0, F und Paare bei Poisson gegen scipy.stats; bester Entwurf bei n = 4 durch vollständige Aufzählung
aller 495 Mengen mit exakter Erwartung über das Poisson-Raster; Wirkungsgrad gegen eine unabhängig formulierte LP (gelieferte Menge als Variable);
Teilqualifikation gegen die 2n-Gruppen-Fassung. Verglichen werden bediente Mengen, Servicegrad und Anteil, nie Zwischenstrukturen oder Tie-Breaks."""

import itertools
import math

import numpy as np
import pytest

import kzs_designs as DS
import kzs_flow as FL
import kzs_pipeline as PL
from kzs_rng import SplitMix64, seed_aus

scipy = pytest.importorskip("scipy")
from scipy.optimize import linprog  # noqa: E402
from scipy.sparse import csr_matrix  # noqa: E402
from scipy.sparse.csgraph import maximum_flow  # noqa: E402
from scipy.stats import poisson  # noqa: E402


# --- Referenzen (ohne kzs_flow) -------------------------------------------------------------------------------------------------------

def edmonds_karp(Dv, Sv, q):
    n = len(Dv)
    V = 2 * n + 2
    s, t = 0, 2 * n + 1
    c = [[0.0] * V for _ in range(V)]
    inf = float(sum(Sv) + sum(Dv) + 1)
    for j in range(n):
        c[s][1 + j] = float(Sv[j])
        for i in range(n):
            if (q[j] >> i) & 1:
                c[1 + j][1 + n + i] = inf
        c[1 + n + j][t] = float(Dv[j])
    fluss = 0.0
    while True:
        vor = [-1] * V
        vor[s] = s
        reihe = [s]
        for u in reihe:
            for v in range(V):
                if vor[v] < 0 and c[u][v] > 1e-12:
                    vor[v] = u
                    reihe.append(v)
        if vor[t] < 0:
            return fluss
        w, v = inf, t
        while v != s:
            w = min(w, c[vor[v]][v])
            v = vor[v]
        v = t
        while v != s:
            c[vor[v]][v] -= w
            c[v][vor[v]] += w
            v = vor[v]
        fluss += w


def scipy_flow(Dv, Sv, q):
    n = len(Dv)
    V, s, t = 2 * n + 2, 0, 2 * n + 1
    gross = int(sum(Sv) + sum(Dv) + 1)
    A = np.zeros((V, V), dtype=np.int32)
    for j in range(n):
        A[s, 1 + j] = int(Sv[j])
        for i in range(n):
            if (q[j] >> i) & 1:
                A[1 + j, 1 + n + i] = gross
        A[1 + n + j, t] = int(Dv[j])
    return maximum_flow(csr_matrix(A), s, t).flow_value


def lp_flow(Dv, Sv, q):
    """Fluss als LP in anderer Form: Variablen x_ji, maximiere die Summe, Zeilen je Gruppe und Station."""
    n = len(Dv)
    arcs = [(j, i) for j in range(n) for i in range(n) if (q[j] >> i) & 1]
    A = np.zeros((2 * n, len(arcs)))
    for a, (j, i) in enumerate(arcs):
        A[j, a] = 1
        A[n + i, a] = 1
    res = linprog(-np.ones(len(arcs)), A_ub=A, b_ub=np.concatenate([np.asarray(Sv, float), np.asarray(Dv, float)]), bounds=(0, None), method="highs")
    return -res.fun


def brute_force(Dv, Sv, q):
    """Größte bediente Menge durch Aufzählung aller ganzzahligen Zuordnungen von Einheiten (kein Fluss, kein LP)."""
    n = len(Dv)
    ziele = [[i for i in range(n) if (q[j] >> i) & 1] for j in range(n)]

    def verteilungen(einheiten, z):
        if len(z) == 1:
            for a in range(einheiten + 1):
                yield (a,)
            return
        for a in range(einheiten + 1):
            for rest in verteilungen(einheiten - a, z[1:]):
                yield (a,) + rest

    best = 0

    def rek(j, erhalten):
        nonlocal best
        if j == n:
            best = max(best, sum(min(erhalten[i], Dv[i]) for i in range(n)))
            return
        for a in verteilungen(int(Sv[j]), ziele[j]):
            neu = list(erhalten)
            for z, x in zip(ziele[j], a):
                neu[z] += x
            rek(j + 1, neu)

    rek(0, [0] * n)
    return best


def zufalls_entwurf(n, rng, p=0.4):
    q = []
    for j in range(n):
        m = 1 << j
        for i in range(n):
            if i != j and rng.uniform() < p:
                m |= 1 << i
        q.append(m)
    return tuple(q)


def bedient(Dv, Sv, q):
    return float(FL.bedient_gruppiert(np.array([Dv], float), np.array(Sv, float), q)[0])


# --- Min-Schnitt gegen Fluss, LP und Brute Force --------------------------------------------------------------------------------------

def test_hand_example_is_known_before_it_serves_as_oracle():
    q = (DS.bits(0, 1), DS.bits(1, 2), DS.bits(2))
    assert edmonds_karp([0, 10, 10], [10, 10, 10], q) == 20 and brute_force([0, 2, 2], [2, 2, 2], q) == 4
    assert scipy_flow([30, 0, 0], [10, 10, 10], q) == 10 and lp_flow([0, 30, 0], [10, 10, 10], q) == pytest.approx(20)


def test_min_cut_equals_edmonds_karp_scipy_and_lp_on_integer_and_real_capacities():
    rng = SplitMix64(seed_aus("o4"))
    for inst in range(150):
        n = rng.randint(2, 8)
        q = zufalls_entwurf(n, rng)
        Sv = [rng.randint(0, 15) for _ in range(n)]
        Dv = [rng.randint(0, 30) for _ in range(n)]
        v = bedient(Dv, Sv, q)
        assert v == pytest.approx(edmonds_karp(Dv, Sv, q), abs=1e-9)
        assert v == pytest.approx(scipy_flow(Dv, Sv, q), abs=1e-9)
        assert v == pytest.approx(lp_flow(Dv, Sv, q), abs=1e-7)
    for inst in range(40):
        n = rng.randint(2, 7)
        q = zufalls_entwurf(n, rng)
        Sv = [round(rng.uniform() * 40, 3) for _ in range(n)]
        Dv = [rng.randint(0, 40) for _ in range(n)]
        assert bedient(Dv, Sv, q) == pytest.approx(edmonds_karp(Dv, Sv, q), abs=1e-9)
        assert bedient(Dv, Sv, q) == pytest.approx(lp_flow(Dv, Sv, q), abs=1e-7)


def test_min_cut_equals_brute_force_on_small_instances():
    rng = SplitMix64(seed_aus("o5"))
    for inst in range(90):
        n = 3 if inst < 70 else 2 if inst < 80 else 4
        q = zufalls_entwurf(n, rng, 0.5)
        smax = 4 if n < 4 else 2
        Sv = [rng.randint(0, smax) for _ in range(n)]
        Dv = [rng.randint(0, 6) for _ in range(n)]
        assert bedient(Dv, Sv, q) == brute_force(Dv, Sv, q), (n, q, Sv, Dv)


def test_closed_form_extremes_for_poisson_on_the_fixed_scenarios():
    """D0 = sum E[min(S, D_i)], F = E[min(sum S, sum D)] mit sum D ~ Poisson(n mu), Paare = Summe über E[min(S_a + S_b, Poisson(2 mu))]; die Szenarien
    sind fest, also ist die Prüfung deterministisch (|z| < 4,5 bei 40 Instanzen)."""
    rng = SplitMix64(seed_aus("o3"))
    zs = []
    for inst in range(40):
        n = [2, 4, 6][inst % 3]
        mu = [5, 20, 50][rng.randint(0, 2)]
        S = np.array([round(mu * (0.8 + 0.4 * rng.uniform()), 1) for _ in range(n)])
        from kzs_demand import bedarf
        D = bedarf(n, mu, None, 0, N=4000, block=inst, schluessel="t3")

        def e_min(Sv, m):
            x = np.arange(0, int(m + 14 * math.sqrt(m) + 60))
            return float((poisson.pmf(x, m) * np.minimum(Sv, x)).sum())

        for gemessen, exakt in ((FL.bedient_gruppiert(D, S, DS.ring(n, 0)), sum(e_min(S[j], mu) for j in range(n))),
                                (FL.bedient_gruppiert(D, S, DS.voll(n)), e_min(S.sum(), n * mu)),
                                (FL.bedient_gruppiert(D, S, DS.ketten(n, 2)), sum(e_min(S[a] + S[a + 1], 2 * mu) for a in range(0, n, 2)))):
            sd = gemessen.std(ddof=1)
            zs.append((gemessen.mean() - exakt) / (sd / math.sqrt(len(gemessen))))
    zs = np.array(zs)
    assert np.abs(zs).max() < 4.5 and 0.5 < (zs ** 2).mean() < 1.6


def exakte_erwartung(n, mu, S1, entwuerfe, dmax):
    """Exakte Erwartung des bedienten Bedarfs über das abgeschnittene Poisson-Raster, mit der Aufzählung aller 2^n Teilmengen (ohne kzs_flow)."""
    grid = np.array(list(itertools.product(range(dmax + 1), repeat=n)), float)
    w = np.prod(poisson.pmf(grid, mu), axis=1)
    t = np.arange(1 << n)
    notin = (1.0 - ((t[:, None] >> np.arange(n)[None, :]) & 1)).astype(float)
    dt = grid @ notin.T
    out = []
    for q in entwuerfe:
        cap = np.zeros(1 << n)
        for j in range(n):
            cap += S1 * ((t & q[j]) != 0)
        out.append(float((dt + cap[None, :]).min(axis=1) @ w) / float(w.sum()))
    return np.array(out)


def test_best_design_for_four_stations_by_complete_enumeration_is_the_ring():
    n, mu = 4, 2.0
    S1 = mu * 1.0
    bogen = [(j, i) for j in range(n) for i in range(n) if i != j]
    alle = [tuple(c) for c in itertools.combinations(bogen, n)]
    assert len(alle) == 495
    ents = [DS.aus_bogen(n, b) for b in alle]
    ex = exakte_erwartung(n, mu, S1, ents, dmax=int(mu * 5 + 8))
    # Klassen-Invarianz: je Umbenennung gleicher Wert
    gruppen = {}
    for b, e in zip(alle, ex):
        gruppen.setdefault(PL.kanonisch(n, b), []).append(e)
    assert len(gruppen) == 27 and max(max(v) - min(v) for v in gruppen.values()) < 1e-9
    d0, f, ring, paare = exakte_erwartung(n, mu, S1, [DS.ring(n, 0), DS.voll(n), DS.ring(n, 1), DS.ketten(n, 2)], dmax=int(mu * 5 + 8))
    best = ex.max()
    assert abs(best - ring) < 1e-9                        # der Ring ist der beste (bis auf Umbenennung)
    assert best <= f + 1e-9 and best >= d0
    ring_kan = PL.kanonisch(n, [(j, i) for j in range(n) for i in range(n) if i != j and (DS.ring(n, 1)[j] >> i) & 1])
    assert ring_kan in gruppen and abs(gruppen[ring_kan][0] - best) < 1e-9
    # die exakten Anteile gegen die simulierten (App, 20.000 Szenarien) innerhalb von vier Standardfehlern
    s = PL.Settings(n=4, mu=2, r=1.0)
    d = PL.stufe1(s)["designs"]
    for nm, exakt in (("D1", (ring - d0) / (f - d0)), ("P", (paare - d0) / (f - d0))):
        assert abs(d[nm]["anteil"] - exakt) < 4 * d[nm]["se"] + 1e-4, nm
    o = PL.bester_entwurf(s)
    assert o["ist_ring"] and abs(o["anteil"] - (ring - d0) / (f - d0)) < 4 * o["se"] + 1e-4


# --- Wirkungsgrad und Teilqualifikation --------------------------------------------------------------------------------------------

def lp_wirkungsgrad(Dv, Sv, q, g):
    """Unabhängige Formulierung: Variable y_ji = GELIEFERTE Menge der Gruppe j an Station i; verbraucht y/gewinn Kapazität."""
    n = len(Dv)
    arcs = [(j, i) for j in range(len(Sv)) for i in range(n) if (q[j] >> i) & 1]
    gew = [1.0 if j % n == i else g for (j, i) in arcs]
    A = np.zeros((len(Sv) + n, len(arcs)))
    for a, (j, i) in enumerate(arcs):
        A[j, a] = 1.0 / gew[a]
        A[len(Sv) + i, a] = 1.0
    res = linprog(-np.ones(len(arcs)), A_ub=A, b_ub=np.concatenate([np.asarray(Sv, float), np.asarray(Dv, float)]), bounds=(0, None), method="highs")
    return -res.fun


def test_efficiency_lp_and_closed_form_equal_an_independent_formulation_and_the_counter_example():
    q = (DS.bits(0, 1), DS.bits(1, 2), DS.bits(2))
    assert lp_wirkungsgrad([0, 10, 10], [10, 10, 0], q, 0.8) == pytest.approx(16.4, abs=1e-7)
    assert FL.batch_lp(np.array([[0.0, 10.0, 10.0]]), np.array([10.0, 10.0, 0.0]), q, 0.8)[0] == pytest.approx(16.4, abs=1e-7)
    # die naheliegende Näherung „eigene Station zuerst“ liefert hier nur 10 (Regressionstest der Planung)
    eigen = sum(min(a, b) for a, b in zip([0, 10, 10], [10, 10, 0]))
    assert eigen == 10
    rng = SplitMix64(seed_aus("o7"))
    for inst in range(40):
        n = rng.randint(2, 6)
        q = zufalls_entwurf(n, rng)
        S = [round(rng.uniform() * 30, 2) for _ in range(n)]
        D = [[rng.randint(0, 40) for _ in range(n)] for _ in range(3)]
        g = [0.5, 0.8, 0.9][rng.randint(0, 2)]
        batch = FL.batch_lp(np.array(D, float), np.array(S), q, g)
        for d, b in zip(D, batch):
            assert b == pytest.approx(lp_wirkungsgrad(d, S, q, g), abs=1e-6)
        voll = FL.f_geschlossen(np.array(D, float), np.array(S), g)
        for d, v in zip(D, voll):
            assert v == pytest.approx(lp_wirkungsgrad(d, S, DS.voll(n), g), abs=1e-6)


def test_partial_qualification_equals_the_2n_group_formulation():
    """Fassung der Messreihe: 2n Gruppen, ungeschulter Rest (1-q)*S nur für die eigene Station, geschulter Teil q*S für alle Stationen der Gruppe."""
    rng = SplitMix64(seed_aus("o6"))
    for inst in range(20):
        n = rng.randint(2, 6)
        q = zufalls_entwurf(n, rng)
        S1 = float(rng.randint(5, 25))
        a = [0.1, 0.3, 0.5, 0.75][rng.randint(0, 3)]
        D = np.array([[rng.randint(0, 40) for _ in range(n)] for _ in range(4)], float)
        gruppen_q = tuple(1 << j for j in range(n)) + tuple(q)
        kap = np.concatenate([np.full(n, (1 - a) * S1), np.full(n, a * S1)])
        # Min-Schnitt mit 2n Gruppen als volle Aufzählung (ohne die Reduktion)
        t = np.arange(1 << n)
        notin = (1.0 - ((t[:, None] >> np.arange(n)[None, :]) & 1)).astype(float)
        cap = np.zeros(1 << n)
        for j in range(2 * n):
            cap += kap[j] * ((t & gruppen_q[j]) != 0)
        ref = (D @ notin.T + cap[None, :]).min(axis=1)
        assert np.allclose(FL.bedient(D, S1, q, anteil=a), ref, atol=1e-9)
    # mit Wirkungsgrad: LP in der 2n-Gruppen-Fassung gegen Eigenkapazität zuerst + LP
    n = 3
    q = (DS.bits(0, 1), DS.bits(1, 2), DS.bits(2))
    D = np.array([[0.0, 10.0, 10.0]])
    live = FL.bedient(D, 10.0, q, anteil=0.5, g=0.8)[0]
    ref = lp_wirkungsgrad(D[0], np.concatenate([np.full(3, 5.0), np.full(3, 5.0)]), tuple(1 << j for j in range(3)) + q, 0.8)
    assert live == pytest.approx(ref, abs=1e-7)


def test_every_displayed_share_is_between_the_reference_points_order_and_ratio():
    """Auch die angezeigten Kennzahlen: Anteil = (SG - SG(D0)) / (SG(F) - SG(D0)) aus den angezeigten Servicegraden."""
    d = PL.stufe1(PL.Settings(n=6, mu=20, struct="block25", dist="k10"))["designs"]
    for nm, v in d.items():
        erwartet = (v["sg"] - d["D0"]["sg"]) / (d["F"]["sg"] - d["D0"]["sg"])
        assert v["anteil"] == pytest.approx(erwartet, abs=1e-12), nm
        assert 0.0 - 1e-12 <= v["anteil"] <= 1.0 + 1e-12
