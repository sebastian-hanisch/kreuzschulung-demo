"""Bedienung: Min-Schnitt gruppiert gegen Aufzählung, Hand-Instanz, Komponenten, abgeschlossene Teilmengen, Teilqualifikation, LP, Tagesfluss."""

import numpy as np
import pytest

import kzs_designs as DS
import kzs_flow as FL
from kzs_rng import SplitMix64


def zufalls_entwurf(n, rng, p=0.3):
    q = []
    for j in range(n):
        m = 1 << j
        for i in range(n):
            if i != j and rng.uniform() < p:
                m |= 1 << i
        q.append(m)
    return tuple(q)


def test_hand_instance_chain_a_b_c(kette3):
    q, S, D, erwartet = kette3
    assert np.allclose(FL.bedient_gruppiert(D, S, q), erwartet)
    assert np.allclose(FL.bedient_aufzaehlung(D, S, q), erwartet)


def test_components_of_pairs_ring_and_dedicated():
    assert sorted(FL.komponenten(DS.ketten(6, 2), 6)) == [0b000011, 0b001100, 0b110000]
    assert FL.komponenten(DS.ring(6, 1), 6) == [0b111111]
    assert sorted(FL.komponenten(DS.ring(4, 0), 4)) == [1, 2, 4, 8]
    q = (0b0011, 0b0010, 0b0100, 0b1100)       # {0,1} und {2,3}
    assert sorted(FL.komponenten(q, 4)) == [0b0011, 0b1100]


def test_closed_subsets_of_the_hand_chain():
    """Kette A -> B -> C: Anbieter von A sind {A}, von B {A, B}, von C {B, C}. T ist abgeschlossen, wenn jede Station, deren Anbieter alle zu
    den Gruppen gehören, die T berühren, schon in T liegt. Von Hand: {} ja; {A} ja; {B} nein (berührt A und B, damit ist auch A bedient);
    {C} ja (berührt B und C, A und B haben den Anbieter A); {A, B} ja; {A, C} nein (berührt A, B, C: B fehlt); {B, C} nein (A fehlt);
    {A, B, C} ja. Es sind genau fünf."""
    q = (0b011, 0b110, 0b100)
    (sts, notin, gr, hit), = FL.struktur(q, 3)
    mengen = {frozenset(sts[a] for a in range(len(sts)) if notin[z, a] == 0) for z in range(len(notin))}
    assert mengen == {frozenset(), frozenset({0}), frozenset({2}), frozenset({0, 1}), frozenset({0, 1, 2})}
    assert len(notin) == 5


def test_grouped_min_cut_equals_full_enumeration_on_random_designs():
    rng = SplitMix64(2024)
    for inst in range(120):
        n = 2 + inst % 11
        q = zufalls_entwurf(n, rng, p=[0.1, 0.3, 0.6][inst % 3])
        S = np.array([round(rng.uniform() * 30, 1) for _ in range(n)])
        D = np.array([[rng.randint(0, 40) for _ in range(n)] for _ in range(5)], dtype=float)
        assert np.allclose(FL.bedient_gruppiert(D, S, q), FL.bedient_aufzaehlung(D, S, q), atol=1e-9), (n, q)


def test_grouped_rows_are_fewer_than_all_subsets_for_ring_and_pairs():
    assert FL.zeilen(DS.ketten(12, 2), 12) == 12
    assert FL.zeilen(DS.ring(12, 0), 12) == 24
    assert FL.zeilen(DS.voll(12), 12) == 2
    assert FL.zeilen(DS.ring(12, 1), 12) < 4096


def test_bounds_and_order_of_the_service():
    rng = SplitMix64(7)
    for inst in range(40):
        n = 2 + inst % 7
        q = zufalls_entwurf(n, rng)
        q2 = tuple(m | (1 << rng.randint(0, n - 1)) for m in q)
        S = np.full(n, 20.0)
        D = np.array([[rng.randint(0, 40) for _ in range(n)] for _ in range(20)], dtype=float)
        a, b = FL.bedient_gruppiert(D, S, q), FL.bedient_gruppiert(D, S, q2)
        d0 = np.minimum(D, S).sum(1)
        assert (b >= a - 1e-9).all()
        assert (a >= d0 - 1e-9).all() and (a <= np.minimum(D.sum(1), S.sum()) + 1e-9).all()


def test_partial_qualification_edges_q_zero_is_dedicated_and_q_one_is_the_design():
    rng = SplitMix64(11)
    D = np.array([[rng.randint(0, 40) for _ in range(6)] for _ in range(50)], dtype=float)
    q = DS.ring(6, 1)
    d0 = np.minimum(D, 20.0).sum(1)
    assert np.allclose(FL.bedient(D, 20.0, q, anteil=1e-12), d0, atol=1e-6)
    assert np.allclose(FL.bedient(D, 20.0, q, anteil=1.0), FL.bedient_gruppiert(D, np.full(6, 20.0), q))
    vals = [FL.bedient(D, 20.0, q, anteil=a) for a in (0.1, 0.3, 0.5, 0.75, 1.0)]
    for lo, hi in zip(vals, vals[1:]):
        assert (hi >= lo - 1e-9).all()


def test_partial_qualification_equals_the_2n_group_formulation_by_hand():
    """Hand: zwei Stationen, Ring; S = 10, q = 0,5: Eigenkapazität 5 je Gruppe, geschulter Teil 5. Bedarf (20, 0): Eigen min(20, 5) = 5,
    Rest 15 gegen geschulte 5 von Gruppe 0 plus geschulte 5 von Gruppe 1 (kann Station 0): 10 -> bedient 15."""
    D = np.array([[20.0, 0.0]])
    assert FL.bedient(D, 10.0, DS.ring(2, 1), anteil=0.5)[0] == pytest.approx(15.0)
    # ohne Teilung hätte der Ring 20 bedient
    assert FL.bedient(D, 10.0, DS.ring(2, 1))[0] == pytest.approx(20.0)


def test_closed_form_of_full_flexibility_with_efficiency_matches_lp_and_the_chain_counter_example():
    rng = SplitMix64(5)
    for _ in range(40):
        n = 2 + rng.randint(0, 5)
        S = np.array([round(rng.uniform() * 30, 1) for _ in range(n)])
        D = np.array([[rng.randint(0, 40) for _ in range(n)] for _ in range(6)], dtype=float)
        g = [0.5, 0.8, 0.9][rng.randint(0, 2)]
        assert np.allclose(FL.f_geschlossen(D, S, g), FL.batch_lp(D, S, DS.voll(n), g), atol=1e-7)


def test_batch_lp_equals_single_lps_and_the_hand_counter_example():
    """A kann A und B, B kann B und C, S = (10, 10, 0), D = (0, 10, 10), g = 0,8: LP 16,4 (A liefert 8 an B, B nutzt 2 für sich und 8 auf C: 6,4)."""
    q = (DS.bits(0, 1), DS.bits(1, 2), DS.bits(2))
    out = FL.batch_lp(np.array([[0.0, 10.0, 10.0]]), np.array([10.0, 10.0, 0.0]), q, 0.8)
    assert out[0] == pytest.approx(16.4, abs=1e-7)
    rng = SplitMix64(9)
    D = np.array([[rng.randint(0, 30) for _ in range(4)] for _ in range(6)], dtype=float)
    qq = DS.ring(4, 1)
    batch = FL.batch_lp(D, np.full(4, 15.0), qq, 0.8)
    single = [FL.batch_lp(D[k:k + 1], np.full(4, 15.0), qq, 0.8)[0] for k in range(6)]
    assert np.allclose(batch, single, atol=1e-7)
    assert FL.batch_lp(D, np.full(4, 15.0), qq, 1.0) == pytest.approx(FL.bedient_gruppiert(D, np.full(4, 15.0), qq), abs=1e-7)


def test_day_flow_value_equals_min_cut_and_respects_capacities(kette3):
    q, S, D, erwartet = kette3
    for d, e in zip(D, erwartet):
        wert, fluss, served = FL.tagesfluss(d, 10.0, q)
        assert wert == pytest.approx(e, abs=1e-6)
        assert (fluss.sum(axis=1) <= 10.0 + 1e-6).all()
        assert (served <= d + 1e-6).all()
        assert all(fluss[j, i] == 0 or (q[j] >> i) & 1 for j in range(3) for i in range(3))
        cut, T, grp = FL.kritische_menge(d, S, q)
        assert cut == pytest.approx(e, abs=1e-9)
        # Der Schnitt ist ein Zertifikat: Bedarf außerhalb von T plus Kapazität der Gruppen, die T berühren
        assert sum(d[i] for i in range(3) if i not in T) + 10.0 * len([j for j in range(3) if any((q[j] >> i) & 1 for i in T)]) == pytest.approx(e)
        assert grp == [j for j in range(3) if any((q[j] >> i) & 1 for i in T)]


def test_day_flow_with_partial_qualification_and_efficiency():
    D = np.array([20.0, 0.0])
    wert, fluss, served = FL.tagesfluss(D, 10.0, DS.ring(2, 1), anteil=0.5)
    assert wert == pytest.approx(15.0, abs=1e-6)
    assert fluss[0, 0] == pytest.approx(10.0, abs=1e-6)       # eigene ungeschulte 5 plus geschulte 5
    w2, _, _ = FL.tagesfluss(D, 10.0, DS.ring(2, 1), anteil=1.0, g=0.8)
    assert w2 == pytest.approx(10.0 + 0.8 * 10.0, abs=1e-6)


def test_day_flow_serves_the_right_stations_by_hand():
    """Bedarf (0, 10, 10) auf der Kette A -> B -> C mit Kapazität 10: Station B bekommt 10 (von A), Station C 10 (von B), Station A nichts (Bedarf 0)."""
    q = (DS.bits(0, 1), DS.bits(1, 2), DS.bits(2))
    wert, fluss, served = FL.tagesfluss(np.array([0.0, 10.0, 10.0]), 10.0, q)
    assert served.tolist() == pytest.approx([0.0, 10.0, 10.0], abs=1e-6)
    # Bedarf nur an Station A: nur Gruppe A kann sie bedienen
    wert, fluss, served = FL.tagesfluss(np.array([30.0, 0.0, 0.0]), 10.0, q)
    assert served.tolist() == pytest.approx([10.0, 0.0, 0.0], abs=1e-6)
    cut, T, grp = FL.kritische_menge(np.array([30.0, 0.0, 0.0]), np.full(3, 10.0), q)
    assert cut == 10.0 and 0 in T and grp[0] == 0
