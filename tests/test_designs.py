"""Entwürfe als Bitmasken: Ring, Ketten, offene Kette, Zufall, Eigener Entwurf, Vorlagen, Reihenfolge heiß neben kalt."""

import pytest

import kzs_designs as DS
from kzs_rng import SplitMix64


def test_ring_zero_is_dedicated_and_ring_n_minus_1_is_full():
    for n in (2, 3, 6, 12):
        assert DS.ring(n, 0) == tuple(1 << j for j in range(n))
        assert DS.ring(n, n - 1) == DS.voll(n)
        assert DS.ring(n, 99) == DS.voll(n)


def test_ring_with_k_has_k_times_n_arcs_and_wraps_around():
    assert DS.ring(4, 1) == (0b0011, 0b0110, 0b1100, 0b1001)
    for n, k in ((6, 1), (6, 2), (12, 3)):
        assert DS.zahl_bogen(DS.ring(n, k)) == n * k


def test_chains_of_length_two_are_disjoint_pairs_and_length_n_is_the_ring():
    assert DS.ketten(4, 2) == (0b0011, 0b0011, 0b1100, 0b1100)
    assert DS.ketten(6, 6) == DS.ring(6, 1)
    assert DS.ketten(6, 3) == (0b000011, 0b000110, 0b000101, 0b011000, 0b110000, 0b101000)
    with pytest.raises(ValueError):
        DS.ketten(6, 4)


def test_open_chain_has_n_minus_1_arcs_and_the_last_group_has_no_extra_station():
    q = DS.offene_kette(4)
    assert q == (0b0011, 0b0110, 0b1100, 0b1000)
    assert DS.zahl_bogen(q) == 3


def test_full_has_n_times_n_minus_1_arcs():
    assert DS.zahl_bogen(DS.voll(5)) == 20


def test_random_arcs_are_n_distinct_arcs_without_own_station_and_deterministic():
    q = DS.zufall_bogen(6, SplitMix64(1))
    assert DS.zahl_bogen(q) == 6
    assert all((q[j] >> j) & 1 for j in range(6))
    assert q == DS.zufall_bogen(6, SplitMix64(1))
    assert q != DS.zufall_bogen(6, SplitMix64(2))


def test_random_per_group_gives_each_group_exactly_one_extra_station():
    for seed in range(20):
        q = DS.zufall_je_gruppe(6, SplitMix64(seed))
        assert [bin(m).count("1") for m in q] == [2] * 6
        assert all((q[j] >> j) & 1 for j in range(6))


def test_draw_number_is_the_seed_of_the_app():
    a = DS.zufall_ziehung(6, "R", 3)
    assert a == DS.zufall_bogen(6, SplitMix64(DS.seed_aus("R", 6, 3)))
    assert DS.zufall_ziehung(6, "R1", 3) == DS.zufall_je_gruppe(6, SplitMix64(DS.seed_aus("R1", 6, 3)))


def test_own_design_always_keeps_the_own_station_and_drops_invalid_entries():
    q = DS.eigener_entwurf(4, ((1, 2), (), (0,), (3, 9, -1)))
    assert q == (0b0111, 0b0010, 0b0101, 0b1000)
    assert DS.auswahl_aus_entwurf(q) == ((1, 2), (), (0,), ())
    assert DS.zahl_bogen(q) == 3


def test_sets_available_per_n():
    names = lambda n: list(DS.entwurfssatz(n, 3))   # noqa: E731
    assert names(2) == ["D0", "A", "D1", "F"]
    assert names(3) == ["D0", "A", "D1", "R", "R1", "F"]
    assert names(4) == ["D0", "A", "D1", "D2", "P", "R", "R1", "F"]
    assert names(6) == ["D0", "A", "D1", "D2", "D3", "P", "C3", "R", "R1", "F"]
    assert names(8) == ["D0", "A", "D1", "D2", "D3", "P", "C4", "R", "R1", "F"]
    assert names(12) == ["D0", "A", "D1", "D2", "D3", "P", "C3", "C4", "C6", "R", "R1", "F"]
    assert "E" in DS.entwurfssatz(6, 3, DS.ring(6, 1))


def test_hot_next_to_cold_alternates_highest_and_lowest():
    assert DS.heiss_neben_kalt([1.5, 0.5, 1.5, 0.5, 1.5, 0.5]) == [0, 5, 2, 3, 4, 1]
    # Block: heiße 0 bis 2, kalte 3 bis 5
    order = DS.heiss_neben_kalt([1.5, 1.5, 1.5, 0.5, 0.5, 0.5])
    assert order == [0, 5, 1, 4, 2, 3]
    assert sorted(order) == list(range(6))
    # gleicher Bedarf: nach Index, abwechselnd erste und letzte
    assert DS.heiss_neben_kalt([1.0] * 4) == [0, 3, 1, 2]


def test_ring_in_order_chains_consecutive_stations_cyclically():
    q = DS.ring_in_reihenfolge([0, 5, 1, 4, 2, 3])
    assert DS.auswahl_aus_entwurf(q) == ((5,), (4,), (3,), (0,), (2,), (1,))
    assert DS.zahl_bogen(q) == 6


def test_templates_and_their_availability():
    assert DS.vorlage_verfuegbar("paare", 6) and not DS.vorlage_verfuegbar("paare", 3) and not DS.vorlage_verfuegbar("paare", 2)
    assert DS.vorlage("leer", 4, [1.0] * 4) == ((),) * 4
    assert DS.vorlage("ring", 4, [1.0] * 4) == ((1,), (2,), (3,), (0,))
    assert DS.vorlage("kette", 4, [1.0] * 4) == ((1,), (2,), (3,), ())
    assert DS.vorlage("paare", 4, [1.0] * 4) == ((1,), (0,), (3,), (2,))
    zuf = DS.vorlage("zufall", 6, [1.0] * 6, zufalls_seed=3, zaehler=1)
    assert sum(len(a) for a in zuf) == 6
    hk = DS.vorlage("heiss_kalt", 6, [1.5, 1.5, 1.5, 0.5, 0.5, 0.5])
    assert sum(len(a) for a in hk) == 6
