"""Meldungen in drei Zuständen je Abschnitt (mit künstlichen Kennzahlen, jede Schwelle kippt an ihrer Stelle), Diagnose, Tabelle, Formatierung."""

import pytest

import kzs_constants as C
import kzs_evaluation as E
import kzs_pipeline as PL


def fake_s1(anteile, gewinn=5.0, gewinn_pt=6.0, bogen=None):
    """Stufe 1 mit vorgegebenen Anteilen (Prozent) je Entwurf; Standardfehler 0,1 Punkte."""
    bogen = bogen or {}
    d = {"D0": {"anteil": 0.0, "se": 0.0, "sg": 0.9, "unterdeckung": 10.0, "bogen": 0, "masken": (1, 2, 4, 8, 16, 32)},
         "F": {"anteil": 1.0, "se": 0.0, "sg": 0.95, "unterdeckung": 4.0, "bogen": 30, "masken": (63,) * 6}}
    for nm, a in anteile.items():
        d[nm] = {"anteil": None if a is None else a / 100.0, "se": 0.001, "sg": 0.92, "unterdeckung": 7.0, "bogen": bogen.get(nm, 6),
                 "masken": (3, 6, 12, 24, 48, 33)}
    return {"designs": d, "gewinn_punkte": gewinn, "gewinn_pt": gewinn_pt, "bedarf_mittel": 120.0, "kapazitaet": 120.0, "N": 20000, "sekunden": 0.1}


S = PL.Settings(n=6, mu=20)


def test_ring_message_three_states_and_the_95_and_80_thresholds():
    assert E.meldung_ring(S, fake_s1({"D1": 99.9, "D2": 100.0}))["level"] == "success"
    assert E.meldung_ring(S, fake_s1({"D1": 95.25, "D2": 100.0}))["level"] == "success"      # 95,25 - 2 * 0,1 >= 95
    assert E.meldung_ring(S, fake_s1({"D1": 95.15, "D2": 100.0}))["level"] == "info"         # 95,15 - 0,2 < 95: unklar
    m = E.meldung_ring(S, fake_s1({"D1": 94.9, "D2": 100.0}))
    assert m["level"] == "info" and "94,9" in m["text"] and "100,0" in m["text"]
    assert E.meldung_ring(S, fake_s1({"D1": 80.3, "D2": 90.0}))["level"] == "info"
    assert E.meldung_ring(S, fake_s1({"D1": 79.9, "D2": 90.0}))["level"] == "info"            # 79,9 + 0,2 >= 80: noch nicht Zustand 3
    assert E.meldung_ring(S, fake_s1({"D1": 79.7, "D2": 90.0}))["level"] == "warning"
    m = E.meldung_ring(S, fake_s1({"D1": 37.3, "D2": 73.7, "D3": 97.9}))
    assert m["level"] == "warning" and "37,3" in m["text"] and "73,7" in m["text"] and "97,9" in m["text"]


def test_ring_message_for_two_stations_and_for_a_tiny_gain():
    assert "Konstruktion" in E.meldung_ring(PL.Settings(n=2), fake_s1({"D1": 100.0}))["text"]
    m = E.meldung_ring(S, fake_s1({"D1": 50.0}, gewinn=0.2))
    assert m["level"] == "info" and "nicht gezeigt" in m["text"]


def test_arrangement_message_three_states():
    s1 = fake_s1({"D1": 100.0, "P": 49.9, "R": 51.0})
    s2 = {"R": {"mittel": 0.51, "sd": 0.08, "ziehungen": 24, "min": 0.4, "max": 0.7}}
    assert E.meldung_anordnung(S, s1, s2)["level"] == "success"
    s1b = fake_s1({"D1": 98.1, "P": 83.5, "R": 41.0})
    assert E.meldung_anordnung(S, s1b, {"R": {"mittel": 0.41, "sd": 0.1, "ziehungen": 12, "min": 0.3, "max": 0.6}})["level"] == "info"
    s1c = fake_s1({"D1": 37.3, "P": 0.5, "R": 46.0})
    m = E.meldung_anordnung(S, s1c, {"R": {"mittel": 0.45, "sd": 0.18, "ziehungen": 12, "min": 0.2, "max": 0.7}})
    assert m["level"] == "warning" and "schlägt" in m["text"]
    # Zufall genau auf dem Ring: kein Zustand 3 (Standardfehler-Bedingung)
    m = E.meldung_anordnung(S, fake_s1({"D1": 50.0, "P": 10.0, "R": 50.0}), {"R": {"mittel": 0.5001, "sd": 0.1, "ziehungen": 12, "min": 0.3, "max": 0.7}})
    assert m["level"] != "warning"
    # ohne Paare (n ungerade) wird gegen den Zufall verglichen
    m = E.meldung_anordnung(PL.Settings(n=3), fake_s1({"D1": 100.0, "R": 56.0}), None)
    assert "zufällige Verteilung" in m["text"]


def test_arrangement_threshold_of_20_points_with_standard_error():
    s1 = fake_s1({"D1": 70.0, "P": 50.0, "R": 40.0})                 # Abstand 20 minus 2 Standardfehler: unter der Schwelle
    assert E.meldung_anordnung(S, s1)["level"] == "info"
    s1 = fake_s1({"D1": 70.5, "P": 50.0, "R": 40.0})
    assert E.meldung_anordnung(S, s1)["level"] == "success"


def test_diagnosis_states_single_cause_multiple_causes_and_ring_enough():
    ok = E.meldung_diagnose(S, fake_s1({"D1": 99.9, "D2": 100.0}))
    assert ok["level"] == "success" and "reicht der Ring" in ok["text"] and "37,3" in ok["text"]
    one = E.meldung_diagnose(PL.Settings(n=12, struct="block50"), fake_s1({"D1": 37.3, "D2": 73.7, "D3": 97.9}))
    assert one["level"] == "warning" and "Block" in one["text"] and "D3" in one["text"] and "97,9" in one["text"]
    many = E.meldung_diagnose(PL.Settings(n=12, dist="k4", eff=0.8), fake_s1({"D1": 78.0, "D2": 91.0, "D3": 97.0}))
    assert many["level"] == "warning" and many["text"].startswith("Mehrere Ursachen zugleich")
    none = E.meldung_diagnose(PL.Settings(n=6), fake_s1({"D1": 90.0, "D2": 91.0, "D3": 92.0}))
    assert "ohne dass ein einzelner Gegenfall" in none["text"] and "Auch D3 holt noch keine 95" in none["text"]
    teil = E.meldung_diagnose(PL.Settings(n=6, q=0.3), fake_s1({"D1": 83.0, "D2": 96.0}))
    assert "Teil jeder Gruppe" in teil["text"] and "D2" in teil["text"]


def test_causes_follow_the_controls():
    assert E.ursachen(PL.Settings()) == []
    assert E.ursachen(PL.Settings(struct="alt50")) == []                      # abwechselnd schwächt den Ring kaum
    assert E.ursachen(PL.Settings(struct="block25")) == ["struktur"]
    assert E.ursachen(PL.Settings(dist="k10_korr")) == ["streuung"]
    assert E.ursachen(PL.Settings(eff=0.8)) == ["wirkungsgrad"]
    assert E.ursachen(PL.Settings(n=8, mu=5)) == ["klein"] and E.ursachen(PL.Settings(n=6, mu=5)) == []
    assert E.ursachen(PL.Settings(q=0.5)) == ["schulung"]


def test_own_design_message_states():
    base = {"D1": 100.0, "E": 100.0}
    assert E.meldung_eigener(S, fake_s1({"D1": 100.0}))["level"] == "info"            # kein E: Hinweis
    m = E.meldung_eigener(S, fake_s1(base, bogen={"D1": 6, "E": 6}))
    assert m["level"] == "success"
    m = E.meldung_eigener(S, fake_s1({"D1": 100.0, "E": 60.0}, bogen={"D1": 6, "E": 8}))
    assert m["level"] == "warning" and "holt der Ring mehr" in m["text"]
    m = E.meldung_eigener(S, fake_s1({"D1": 100.0, "E": 96.0}, bogen={"D1": 6, "E": 5}))
    assert m["level"] == "success" and "weniger aufwand" in m["text"].lower()
    m = E.meldung_eigener(S, fake_s1({"D1": 100.0, "E": 60.0}, bogen={"D1": 6, "E": 3}))
    assert m["level"] == "info" and "Weniger Aufwand, weniger Nutzen" in m["text"]


def test_training_message_states():
    s1 = fake_s1({"D1": 100.0})
    kurve_gut = {"D1": [(0.22, 0.0), (0.4, 0), (0.66, 0), (0.83, 0), (0.97, 0), (0.998, 0), (1.0, 0)]}
    m = E.meldung_schulung(S, s1, kurve_gut)
    assert m["level"] == "success" and "28 %" in m["text"]
    kurve_viel = {"D1": [(0.1, 0.0), (0.18, 0), (0.34, 0), (0.47, 0), (0.68, 0), (0.84, 0), (0.93, 0)]}
    m = E.meldung_schulung(S, s1, kurve_viel)
    assert m["level"] == "info" and "Viele müssen lernen" in m["text"]
    kurve_nie = {"D1": [(0.05, 0.0), (0.1, 0), (0.2, 0), (0.3, 0), (0.37, 0), (0.37, 0), (0.373, 0)]}
    m = E.meldung_schulung(S, s1, kurve_nie)
    assert m["level"] == "warning" and "ändert nichts" in m["text"] and "37,3" in m["text"]
    # der Eigene Entwurf wird bevorzugt
    both = dict(kurve_gut, E=kurve_nie["D1"])
    assert "Dein Entwurf" in E.meldung_schulung(S, s1, both)["text"]


def test_training_threshold_at_40_percent():
    s1 = fake_s1({"D1": 100.0})

    def kurve(a30, a50):
        return {"D1": [(0.2, 0), (0.4, 0), (0.6, 0), (a30, 0), (a50, 0), (0.95, 0), (1.0, 0)]}

    assert E.meldung_schulung(S, s1, kurve(0.7, 0.9))["level"] == "success"       # 80 % genau bei q = 0,40
    assert E.meldung_schulung(S, s1, kurve(0.7, 0.88))["level"] == "info"         # 80 % erst bei q = 0,41


def test_cake_message_states():
    assert E.meldung_kuchen(S, fake_s1({"D1": 100.0}, gewinn=2.9, gewinn_pt=1.7))["level"] == "warning"
    assert E.meldung_kuchen(S, fake_s1({"D1": 100.0}, gewinn=3.0, gewinn_pt=1.7))["level"] == "info"
    m = E.meldung_kuchen(PL.Settings(n=3), fake_s1({"D1": 100.0}, gewinn=3.8, gewinn_pt=2.3))
    assert m["level"] == "info" and "D2 = F per Konstruktion" in m["text"]
    m = E.meldung_kuchen(PL.Settings(n=2), fake_s1({"D1": 100.0}, gewinn=3.8, gewinn_pt=2.3))
    assert "Ring = F per Konstruktion" in m["text"]
    m = E.meldung_kuchen(S, fake_s1({"D1": 100.0}, gewinn=5.25, gewinn_pt=6.29))
    assert "Preis der Schulung ist nicht modelliert" in m["text"] and "6,29" in m["text"]


def test_table_rows_hide_the_share_for_a_tiny_gain_and_carry_the_spread_of_random_designs():
    s1 = fake_s1({"A": 66.5, "D1": 100.0, "P": 49.9, "R": 51.0, "R1": 60.0})
    s2 = {"R": {"mittel": 0.514, "sd": 0.086, "ziehungen": 24, "min": 0.4, "max": 0.7}, "R1": {"mittel": 0.66, "sd": 0.1, "ziehungen": 24, "min": 0.4, "max": 0.9}}
    rows = {r["Kürzel"]: r for r in E.tabelle(S, s1, s2)}
    assert list(rows)[:3] == ["D0", "A", "P"] and rows["R"]["Ziehungen"] == 24 and rows["R"]["Mittel der Ziehungen %"] == pytest.approx(51.4)
    assert rows["P"]["± 2 SE"] == pytest.approx(0.2)
    assert all(r["Anteil %"] is None for r in E.tabelle(S, fake_s1({"D1": 100.0}, gewinn=0.1), None))
    assert E.belegschaft_mit_zusatz((3, 2, 4, 8), 0.5) == pytest.approx(0.125)


def test_number_formatting_uses_decimal_comma_and_thousands_dot_only_on_numbers():
    assert E.de(1234.567, 1) == "1234,6" and E.de(None) == "–" and E.de(0.5, 1, True) == "+0,5"
    assert E.thou(20000) == "20.000" and E.thou(912) == "912"
    assert E.pct(0.5) == 50.0 and E.pct(None) is None


def test_time_hint_only_for_the_slow_corner():
    assert E.zeithinweis(PL.Settings(n=12, eff=0.8)) is not None
    assert E.zeithinweis(PL.Settings(n=12)) is None and E.zeithinweis(PL.Settings(n=8, eff=0.8)) is None
