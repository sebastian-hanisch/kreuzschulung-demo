"""Rechenpfad: Selbst-Reproduktion von Zellen der Messreihe, Invarianten, Zweig-Test, Teilkurve, Stufen, Eigener Entwurf, O bei n = 4."""

import dataclasses
import sys
from pathlib import Path

import numpy as np
import pytest

import kzs_constants as C
import kzs_designs as DS
import kzs_flow as FL
import kzs_pipeline as PL
import kzs_results as R

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import reproduce_messreihe as RM  # noqa: E402

TOL = 1e-11


@pytest.mark.parametrize("kw,teil", [(dict(n=6, mu=20), False), (dict(n=12, mu=20, imb=("block", 0.5)), False), (dict(n=12, mu=20, disp=4), False),
                                     (dict(n=6, mu=20, disp=4, korr=0.5), False), (dict(n=6, mu=20, g=0.8), False), (dict(n=6, mu=20), True),
                                     (dict(n=12, mu=5, r=0.9), False)])
def test_live_path_reproduces_cells_of_the_measurement_series(kw, teil):
    c = R.cell(teil=teil, **kw)
    assert c is not None
    key = R.schluessel(teil=teil, **kw)
    zahl, abw = RM.vergleiche_zelle(key, c)
    assert zahl > 20
    assert max(abw.values()) < TOL, abw


def test_settings_are_keyword_only_and_hashable():
    with pytest.raises(TypeError):
        PL.Settings(6, 20)
    s = PL.Settings(n=8, mu=5)
    assert hash(s) == hash(PL.Settings(n=8, mu=5))
    assert dataclasses.replace(s, seed=7).seed == 7


def test_settings_derived_values():
    s = PL.Settings(n=12, mu=20, r=1.1, dist="k4_korr", struct="alt50", eff=0.8)
    assert (s.disp, s.korr, s.imb, s.g, s.N) == (4, 0.5, ("alt", 0.5), 0.8, 800)
    assert s.S1 == pytest.approx(22.0) and s.n_ziehungen == 4
    assert PL.Settings(n=12).n_ziehungen == 12 and PL.Settings(n=8).n_ziehungen == 24 and PL.Settings().N == 20000
    assert PL.Settings(n=3).own_masks is None
    assert PL.Settings(n=3, own=((1,), (), ())).own_masks == (0b011, 0b010, 0b100)
    assert PL.Settings(n=3, own=((), (), ())).own_masks is None


def test_cell_key_matches_the_stored_format():
    s = PL.Settings(n=12, mu=20, struct="block50")
    assert PL.mess_schluessel(s) == "n=12|mu=20|disp=None|korr=0.0|r=1.0|g=1.0|imb=('block', 0.5)|teil=False"
    assert PL.mess_schluessel(s) in R.cells()


def test_cell_key_keeps_capacity_and_efficiency_apart():
    s = PL.Settings(n=6, mu=20, r=0.9, eff=0.8, dist="k10_korr", struct="alt25")
    assert PL.mess_schluessel(s, teil=True) == "n=6|mu=20|disp=10|korr=0.5|r=0.9|g=0.8|imb=('alt', 0.25)|teil=True"
    assert PL.zellen_schluessel(12, 5, 4, 0.0, 1.1, 1.0, None, False) == "n=12|mu=5|disp=4|korr=0.0|r=1.1|g=1.0|imb=None|teil=False"


def test_selection_of_the_best_design_runs_on_its_own_scenarios(monkeypatch):
    """Gewinnerfluch: Auswahl und Bewertung dürfen nicht auf denselben Szenarien laufen (eigener Block mit 3.000 Szenarien)."""
    gesehen = []
    echt = FL.bedient

    def spion(D, S1, q, anteil=1.0, g=1.0):
        gesehen.append(D.shape[0])
        return echt(D, S1, q, anteil, g)

    monkeypatch.setattr(PL.FL, "bedient", spion)
    PL.bester_entwurf(PL.Settings(n=4, mu=20))
    assert gesehen.count(C.N_AUSWAHL) == 27 and gesehen.count(C.N_SZENARIEN) >= 1
    assert not np.array_equal(PL.szenarien(PL.Settings(n=4), N=100, block=C.AUSWAHL_BLOCK), PL.szenarien(PL.Settings(n=4), N=100, block=0))


def test_basic_cell_numbers_and_order_of_the_chain():
    s1 = PL.stufe1(PL.Settings())
    d = s1["designs"]
    a = {k: v["anteil"] for k, v in d.items()}
    assert a["D0"] == pytest.approx(0.0) and a["F"] == pytest.approx(1.0)
    assert 0.495 < a["P"] < 0.502 and 0.66 < a["A"] < 0.67 and a["D1"] > 0.9999
    assert d["D1"]["bogen"] == 6 and d["P"]["bogen"] == 6 and d["A"]["bogen"] == 5 and d["F"]["bogen"] == 30
    assert s1["gewinn_punkte"] == pytest.approx(5.25, abs=0.01) and s1["gewinn_pt"] == pytest.approx(6.29, abs=0.01)
    assert a["D0"] <= a["A"] <= a["D1"] <= a["D2"] + 1e-9 <= a["F"] + 2e-9


def test_every_neighbour_in_the_chain_differs_somewhere_branch_test():
    """Zweig-Test (Nullspalten sind Bug-Signale): Nachbarn der Kette D0, A, D1, D2, D3, D4, F weichen auf mindestens einer Instanz ab."""
    n = 6
    kette = [DS.ring(n, 0), DS.offene_kette(n), DS.ring(n, 1), DS.ring(n, 2), DS.ring(n, 3), DS.ring(n, 4), DS.voll(n)]
    S = np.full(n, 20.0)
    gebaut = np.zeros(len(kette) - 1, dtype=bool)
    for i in range(n):
        Dk = np.zeros((1, n))
        Dk[0, i] = 200.0
        rk = np.array([FL.bedient_gruppiert(Dk, S, q)[0] for q in kette])
        assert np.allclose(rk, [20.0, 20.0 if i == 0 else 40.0, 40.0, 60.0, 80.0, 100.0, 120.0])
        gebaut |= np.abs(np.diff(rk)) > 1e-9
    assert gebaut.all()
    d = PL.stufe1(PL.Settings(n=6, mu=20, dist="k4", struct="block50"))["designs"]
    for a, b in (("D1", "P"), ("D1", "C3"), ("P", "C3"), ("D1", "R")):
        assert abs(d[a]["anteil"] - d[b]["anteil"]) > 1e-3


def test_expected_equalities_for_two_and_three_stations():
    d2 = PL.stufe1(PL.Settings(n=2))["designs"]
    assert d2["D1"]["sg"] == pytest.approx(d2["F"]["sg"], abs=1e-12) and d2["D1"]["anteil"] == pytest.approx(1.0)
    d3 = PL.stufe1(PL.Settings(n=3))["designs"]
    assert "D2" not in d3
    D = np.array([[60.0, 0.0, 0.0]])
    r = [FL.bedient_gruppiert(D, np.full(3, 20.0), q)[0] for q in (DS.ring(3, 1), DS.ring(3, 2), DS.voll(3))]
    assert r == [40.0, 60.0, 60.0]


def test_stage_two_streuung_matches_the_measurement_series_draws():
    s = PL.Settings(n=6, mu=20)
    s2 = PL.stufe2(s)
    c = R.cell_fuer(s)
    assert s2["R"]["mittel"] == pytest.approx(c["zufall"]["R"]["anteil_mittel"], abs=1e-11)
    assert s2["R1"]["sd"] == pytest.approx(c["zufall"]["R1"]["anteil_sd"], abs=1e-11)
    assert s2["R"]["ziehungen"] == 24
    assert "R" not in PL.stufe2(PL.Settings(n=2))


def test_teil_curve_has_the_stored_values_and_is_monotone():
    s = PL.Settings(n=6, mu=20)
    s3 = PL.stufe3(s)
    ct = R.cell(6, 20, teil=True)
    for q, (a, _) in zip(C.Q_OPTIONS, s3["D1"]):
        assert a == pytest.approx(ct["teil"]["ring_q%s" % q]["anteil"], abs=1e-11)
    vals = [a for a, _ in s3["D1"]]
    assert all(b >= a - 1e-9 for a, b in zip(vals, vals[1:]))
    assert vals[-1] == pytest.approx(PL.stufe1(s)["designs"]["D1"]["anteil"], abs=1e-11)


def test_q_for_goal_interpolates_from_the_origin():
    anteile = [0.2, 0.4, 0.6, 0.7, 0.9, 1.0, 1.0]       # bei q = 0,05; 0,1; 0,2; 0,3; 0,5; 0,75; 1
    assert PL.q_fuer_ziel(anteile, 0.4) == pytest.approx(0.1)
    assert PL.q_fuer_ziel(anteile, 0.8) == pytest.approx(0.4)
    assert PL.q_fuer_ziel([0.1] * 7, 0.8) is None
    assert PL.q_fuer_ziel(anteile, 0.2) == pytest.approx(0.05)


def test_own_design_row_equals_the_same_fixed_design():
    ring_auswahl = DS.vorlage("ring", 6, [1.0] * 6)
    s = PL.Settings(n=6, mu=20, own=ring_auswahl)
    d = PL.stufe1(s)["designs"]
    assert d["E"]["anteil"] == pytest.approx(d["D1"]["anteil"], abs=1e-12) and d["E"]["bogen"] == 6
    assert "E" not in PL.stufe1(PL.Settings(n=6, mu=20))["designs"]


def test_every_controller_changes_some_figure():
    base = PL.stufe1(PL.Settings(n=6, mu=20))
    for kw in (dict(n=8), dict(mu=5), dict(r=0.9), dict(dist="k4"), dict(struct="block50"), dict(eff=0.8), dict(q=0.3), dict(seed=4)):
        s = PL.stufe1(PL.Settings(**{**dict(n=6, mu=20), **kw}))
        diff = any(abs((s["designs"][k]["anteil"] or 0) - (base["designs"][k]["anteil"] or 0)) > 1e-6 for k in base["designs"] if k in s["designs"]) \
            or abs(s["gewinn_punkte"] - base["gewinn_punkte"]) > 1e-6
        assert diff, kw


def test_best_design_at_n_equals_4_is_the_ring_up_to_renaming():
    o = PL.bester_entwurf(PL.Settings(n=4, mu=20))
    assert o["klassen"] == 27 and o["ist_ring"] and o["bogen"] == 4
    d1 = PL.stufe1(PL.Settings(n=4, mu=20))["designs"]["D1"]["anteil"]
    assert abs(o["anteil"] - d1) < 0.01
    assert PL.bester_entwurf(PL.Settings(n=6)) is None and PL.bester_entwurf(PL.Settings(n=4, struct="block50")) is None
    assert PL.bester_entwurf(PL.Settings(n=4, eff=0.8)) is None


def test_example_day_checks_min_cut_against_max_flow():
    s = PL.Settings(n=6, mu=20, struct="block50")
    for tag in (0, 1, 17, 19999):
        t = PL.beispieltag(s, DS.ring(6, 1), tag)
        assert t["schnitt"] == pytest.approx(t["wert"], abs=1e-2)
        assert t["unterdeckung"].sum() == pytest.approx(t["bedarf_summe"] - t["wert"], abs=1e-6)
        assert (t["unterdeckung"] >= -1e-9).all()
    t = PL.beispieltag(PL.Settings(n=6, eff=0.8), DS.ring(6, 1), 12345)
    assert t["tag"] == 12345 % 800 and t["schnitt"] is None
    t = PL.beispieltag(PL.Settings(n=6, q=0.3), DS.ring(6, 1), 5)
    assert t["schnitt"] == pytest.approx(t["wert"], abs=1e-2)


def test_the_number_of_classes_of_four_arc_sets_for_n_equals_4():
    kl = PL.klassen(4, 4)
    assert len(kl) == 27 and sum(m for _, m in kl) == 495
