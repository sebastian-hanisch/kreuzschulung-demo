"""Abdeckung (data/kzs_coverage.json): vollständig, stimmt an den Messpunkten mit der Messreihe überein, bei Stichproben mit der Live-Rechnung."""

import itertools

import pytest

import kzs_constants as C
import kzs_pipeline as PL
import kzs_results as R


@pytest.fixture(scope="module")
def cov():
    c = R.load_coverage()
    assert c is not None
    return c


def test_all_2700_combinations_are_present_once(cov):
    erwartet = {R.abdeckung_schluessel(n, mu, r, d, s, e) for n, mu, r, d, s, e in
                itertools.product(C.N_OPTIONS, C.MU_OPTIONS, C.R_OPTIONS, C.DIST_ORDER, C.STRUCT_ORDER, C.EFF_OPTIONS)}
    assert len(erwartet) == C.N_KOMBINATIONEN == 2700
    assert set(cov["rows"]) == erwartet
    assert cov["meta"]["kombinationen"] == 2700


def test_measurement_points_are_138_of_2700_and_inside_the_coverage(cov):
    mp = R.messpunkte()
    assert len(mp) == 138
    for n, mu, r, d, s, e in mp:
        assert R.abdeckung_schluessel(n, mu, r, d, s, e) in cov["rows"]


def test_statements_on_measurement_points_equal_the_measurement_series_counts(cov):
    z = R.abdeckung_zusammenfassung()
    assert z["gemessen"] == R.aussagen_messreihe()["zaehlung"]
    assert z["kombinationen"] == 2700
    for a in R.AUSSAGEN:
        for k, v in z["alle"][a].items():
            assert v == z["gemessen"][a].get(k, 0) + z["ungemessen"][a].get(k, 0)


def test_every_record_is_complete_and_the_ring_never_exceeds_full_flexibility(cov):
    for key, rec in cov["rows"].items():
        e = rec["entwuerfe"]
        n = int(key.split("|")[0][2:])
        assert rec["gewinn_punkte"] > 0.5 and rec["gewinn_pt"] > 0, key
        assert e["A"]["anteil"] is not None and e["D1"]["anteil"] is not None, key
        assert e["D1"]["anteil"] <= 1.0 + 1e-6, key
        assert ("P" in e) == (n % 2 == 0 and n >= 4), key
        assert ("R" in rec) == (n >= 3), key
        assert len(rec["teil"]["D1"]) == len(C.Q_OPTIONS)
        assert all(b >= a - 1e-6 for a, b in zip(rec["teil"]["D1"], rec["teil"]["D1"][1:])), key
        assert rec["teil"]["D1"][-1] == pytest.approx(e["D1"]["anteil"], abs=1e-5), key


@pytest.mark.parametrize("kombi", [(6, 20, 1.0, "poisson", "gleich", 1.0), (12, 20, 1.1, "k4_korr", "block50", 0.8), (8, 5, 0.9, "k10", "alt25", 1.0),
                                   (3, 50, 1.0, "k4", "block25", 1.0), (4, 5, 1.1, "poisson", "alt50", 0.8), (2, 20, 0.9, "k10_korr", "gleich", 1.0)])
def test_coverage_row_equals_the_live_computation(cov, kombi):
    n, mu, r, dist, struct, eff = kombi
    s = PL.Settings(n=n, mu=mu, r=r, dist=dist, struct=struct, eff=eff)
    rec = cov["rows"][R.abdeckung_schluessel(*kombi)]
    live = PL.abdeckung_satz(s)
    for nm, e in live["entwuerfe"].items():
        assert rec["entwuerfe"][nm]["anteil"] == pytest.approx(e["anteil"], abs=2e-6), nm
        assert rec["entwuerfe"][nm]["se"] == pytest.approx(e["se"], abs=2e-6), nm
    assert rec["gewinn_punkte"] == pytest.approx(live["gewinn_punkte"], abs=2e-6)
    if "R" in live:
        assert rec["R"]["mittel"] == pytest.approx(live["R"]["mittel"], abs=2e-6)
    for nm in live["teil"]:
        assert rec["teil"][nm] == pytest.approx(live["teil"][nm], abs=2e-6)


def test_the_hook_holds_on_the_smooth_surface_and_fails_elsewhere(cov):
    glatt = [k for k in cov["rows"] if "dist=poisson|struct=gleich|eff=1.0" in k and not k.startswith("n=2") and "|mu=5|" not in k]
    assert len(glatt) == 30
    assert min(R.abdeckung_ring(cov["rows"][k]) for k in glatt) >= 99.5
    # der Hook ist außerhalb der glatten Fläche die Ausnahme: A1 gilt in weniger als der Hälfte der Kombinationen
    z = R.abdeckung_zusammenfassung()["alle"]["A1"]
    assert z["gilt"] < 0.5 * 2700 and z["gilt nicht"] > 0.5 * 2700


def test_state_of_a_setting_against_the_measurement_series():
    assert R.zustand(PL.Settings()) == "gemessen"
    assert R.zustand(PL.Settings(q=0.3)) == "gemessen"                      # Teil-Zelle n = 6, mu = 20 vorhanden
    assert R.zustand(PL.Settings(n=4, mu=20, q=0.3)) == "bedingt"          # Messpunkt, aber keine Teil-Zelle
    assert R.zustand(PL.Settings(n=8, mu=50)) == "gemessen" and R.zustand(PL.Settings(n=8, mu=50, dist="k4")) == "nicht gemessen"
    assert R.zustand(PL.Settings(n=6, struct="block25", dist="k4")) == "nicht gemessen"


def test_random_beats_ring_statement_a5_is_true_exactly_where_the_mean_of_the_draws_is_above_the_ring():
    z = R.aussagen_messreihe()["zaehlung"]["A5"]
    mehr = [k for k, c in R.basiszelle_zeilen().items() if "R" in c["zufall"] and R.zufall_mittel(c) > R.ring(c)]
    assert z["gilt"] == len(mehr) == 2 and z["gilt nicht"] == 127 and z["n/a"] == 9
    assert R.aussagen(50.0, 0.1, None, 0, None, 0, 60.0)["A5"] == "gilt" and R.aussagen(50.0, 0.1, None, 0, None, 0, 40.0)["A5"] == "gilt nicht"
