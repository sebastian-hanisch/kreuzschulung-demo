"""Claims-Tests: jede Zahl der README wird aus data/*.json (Messreihe, Abdeckung, Messungen dieses Repos) nachgerechnet und muss in der Zeile
stehen, die die Aussage trägt. Keine Zahl ohne Voraussetzung: die Zelle (n, mittlerer Bedarf, Verteilung) steht in derselben Zeile oder davor."""

import json
import pathlib
import re

import pytest

import kzs_constants as C
import kzs_pipeline as PL
import kzs_results as R

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
DATA = ROOT / "data"


def de(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def thou(n):
    return f"{int(n):,}".replace(",", ".")


def row(prefix):
    """Die Zeile der Befunde-Tabelle, die mit `| prefix |` beginnt."""
    lines = [ln for ln in README.splitlines() if ln.startswith(f"| {prefix} |")]
    assert len(lines) == 1, (prefix, len(lines))
    return lines[0]


def bullet(prefix):
    """Der Aufzählungspunkt (mit Fortsetzungszeilen), der mit `- **prefix` beginnt."""
    lines = README.splitlines()
    idx = [k for k, ln in enumerate(lines) if ln.startswith(f"- **{prefix}")]
    assert len(idx) == 1, (prefix, len(idx))
    out = [lines[idx[0]]]
    for ln in lines[idx[0] + 1:]:
        if ln.startswith("  "):
            out.append(ln.strip())
        else:
            break
    return " ".join(out)


def has_all(line, *numbers):
    missing = [n for n in numbers if n not in line]
    assert not missing, (missing, line)


def j(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_readme_has_no_placeholders_left_except_the_live_link_comment():
    ohne = re.sub(r"<!--.*?-->", "", README, flags=re.S)
    assert "TODO" not in ohne and "@@" not in ohne
    assert "—" not in README                       # keine Gedankenstriche im Fließtext
    assert "Saatwert" not in README and not re.search(r"\b(ae|oe|ue)\b", README)


def test_base_cell_row():
    c = R.cell(6, 20)
    d0, f = c["entwuerfe"]["D0"]["sg"], c["entwuerfe"]["F"]["sg"]
    je = (c["entwuerfe"]["D0"]["unterdeckung"] - c["entwuerfe"]["ring1"]["unterdeckung"]) / 6
    has_all(row("Basiszelle"), de(100 * d0), de(100 * f), de(R.gewinn_punkte(c), 2), de(R.gewinn_pt(c), 2), de(R.ring(c), 3), de(R.se(c, "D1"), 3), de(je, 2),
            f"von {round(c['meta']['sd_bedarf'])}")


def test_arrangement_row():
    c = R.cell(6, 20)
    z = c["zufall"]["R"]
    has_all(row("Anordnung statt Zahl"), de(R.ring(c)), de(R.anteil(c, "C3")), de(R.anteil(c, "A")), de(R.zufall_mittel(c, "R1")), de(R.zufall_mittel(c, "R")),
            de(100 * z["anteil_sd"]), de(100 * z["anteil_min"]), de(100 * z["anteil_max"]), de(R.anteil(c, "P")), de(R.se(c, "P")))
    assert c["entwuerfe"]["ring1"]["bogen"] == c["entwuerfe"]["P"]["bogen"] == c["entwuerfe"]["C3"]["bogen"] == 6 and c["entwuerfe"]["A"]["bogen"] == 5


def test_last_arc_row():
    c, c12 = R.cell(6, 20), R.cell(12, 20)
    a = R.anteil(c, "A")
    has_all(row("Der letzte Bogen schließt"), de(a / 5), de(100 - a), de(R.anteil(c12, "A")), de(R.ring(c12)))
    assert R.ring(c) > 99.99


def test_number_of_stations_row():
    ns = (4, 6, 8, 12)
    cs = [R.cell(n, 20) for n in ns]
    ap = [100 * (1 - 2 ** -0.5) / (1 - n ** -0.5) for n in ns]
    has_all(row("Zahl der Stationen"), *[de(R.anteil(c, "P")) for c in cs], *[de(x) for x in ap], de(100 * (1 - 2 ** -0.5)),
            *[de(R.gewinn_punkte(c), 2) for c in cs], de(R.anteil(cs[3], "C3")), de(R.anteil(cs[3], "C4")), de(R.anteil(cs[3], "C6")), de(R.ring(cs[3])))


def test_block_row():
    c = R.cell(12, 20, imb=("block", 0.5))
    c6 = R.cell(6, 20, imb=("block", 0.5))
    mehr = [k for k, x in R.basiszelle_zeilen().items() if "R" in x["zufall"] and R.zufall_mittel(x) > R.ring(x)]
    has_all(row("Block-Ungleichgewicht"), de(R.ring(c)), de(R.ring2(c)), de(R.anteil(c, "D3")), de(R.anteil(c, "P")), de(R.anteil(c, "A")),
            de(R.zufall_mittel(c)), de(100 * c["zufall"]["R"]["anteil_sd"]), de(R.ring(c6)), de(R.ring2(c6)), f"in {len(mehr)} von {R.aussagen_messreihe()['zellen']} Messpunkten")
    assert len(mehr) == 2 and R.zufall_mittel(c) > R.ring(c)


def test_hot_next_to_cold_row():
    v = {(e["n"], e["struct"]): e for e in R.extras()["verschraenkt"]}
    a, b, c = v[(12, "block50")], v[(6, "block50")], v[(12, "block25")]
    has_all(row("Heiß neben kalt"), de(100 * a["ring"]["anteil"]), de(100 * a["ring"]["se"], 2), de(100 * a["ring_stationsreihenfolge"]["anteil"]),
            de(100 * a["paare"]["anteil"]), de(100 * a["paare_nachbarn"]["anteil"]), de(100 * b["ring"]["anteil"]), de(100 * b["ring_stationsreihenfolge"]["anteil"]),
            de(100 * c["ring"]["anteil"]), de(100 * c["ring_stationsreihenfolge"]["anteil"]))
    assert a["ring"]["bogen"] == a["ring_stationsreihenfolge"]["bogen"] == 12
    # die Ring-Stationsreihenfolge ist die Zelle der Messreihe selbst
    assert a["ring_stationsreihenfolge"]["anteil"] == pytest.approx(R.ring(R.cell(12, 20, imb=("block", 0.5))) / 100, abs=1e-12)


def test_overdispersion_row():
    c6k10, c6k4, c8, c12 = R.cell(6, 20, disp=10), R.cell(6, 20, disp=4), R.cell(8, 20, disp=4), R.cell(12, 20, disp=4)
    k10k, k4k = R.cell(6, 20, disp=10, korr=0.5), R.cell(6, 20, disp=4, korr=0.5)
    has_all(row("Überstreuung"), de(R.ring(c6k10)), de(R.ring(c6k4)), de(R.ring2(c6k4)), de(R.ring(c8)), de(R.ring(c12)), de(R.ring2(c12)),
            de(R.gewinn_punkte(R.cell(6, 20)), 2), de(R.gewinn_punkte(c6k10), 2), de(R.gewinn_punkte(c6k4), 2), de(R.gewinn_punkte(k10k), 2), de(R.gewinn_punkte(k4k), 2))
    assert R.gewinn_punkte(k4k) < 0.55 * R.gewinn_punkte(c6k4) and R.gewinn_punkte(k10k) < 0.6 * R.gewinn_punkte(c6k10)    # „halbiert“


def test_small_demand_row():
    kl = [min(R.ring(R.cell(n, 5, r=r)) for r in C.R_OPTIONS) for n in (3, 4, 6, 8, 12)]
    has_all(row("Kleiner Bedarf"), *[de(x) for x in kl], de(R.ring2(R.cell(12, 5))))
    assert kl == sorted(kl, reverse=True)


def test_efficiency_row():
    c6, c12 = R.cell(6, 20, g=0.8), R.cell(12, 20, g=0.8)
    has_all(row("Wirkungsgrad 0,8"), de(R.ring(c6)), de(R.se(c6, "D1")), de(R.ring(c12)), de(R.ring2(c6)), de(R.ring2(c12)), de(R.anteil(c6, "P")), de(R.anteil(c12, "P")),
            de(R.gewinn_punkte(c6), 2), de(R.gewinn_punkte(R.cell(6, 20)), 2))
    assert c6["meta"]["N"] == c12["meta"]["N"] == 800


def test_few_stations_row():
    c3 = R.cell(3, 20)
    kleinst = min((R.gewinn_punkte(c), k) for k, c in R.cells().items() if c["meta"]["g"] == 1.0)
    assert kleinst[1].startswith("n=2|mu=50|") and "r=0.9" in kleinst[1]
    has_all(row("Wenige Stationen"), de(kleinst[0], 2), de(R.ring(c3)), de(R.zufall_mittel(c3)), de(R.gewinn_punkte(c3), 2), de(R.gewinn_pt(c3), 2))


def test_partial_qualification_row():
    def kurve(n, mu=20, art="ring", **kw):
        c = R.cell(n, mu, teil=True, **kw)
        return [100 * c["teil"]["%s_q%s" % (art, q)]["anteil"] for q in C.Q_OPTIONS], c

    ring6, c6 = kurve(6)
    has_all(row("Teilqualifikation"), de(ring6[1]), de(ring6[2]), de(ring6[3]), de(ring6[4]))
    paare6, _ = kurve(6, art="paar")
    assert paare6[4] == pytest.approx(paare6[-1], abs=0.1) and de(paare6[-1]) in row("Teilqualifikation")
    erwartung = {}
    for lab, (n, mu, kw) in {"n6": (6, 20, {}), "n12": (12, 20, {}), "k4": (6, 20, dict(disp=4)), "mu5": (6, 5, {})}.items():
        ring, _ = kurve(n, mu, **kw)
        erwartung[lab] = [round(100 * PL.q_fuer_ziel([a / 100 for a in ring], z)) for z in (0.5, 0.8, 0.9)]
    assert erwartung == {"n6": [14, 28, 40], "n12": [18, 41, 55], "k4": [33, 69, 91], "mu5": [28, 58, 74]}
    line = row("Teilqualifikation")
    has_all(line, "14 / 28 / 40", "18 / 41 / 55", "33 / 69 / 91", "28 / 58 / 74")


def test_degeneracy_row():
    ent = R.extras()["entartung"]
    zeilen = [(e["mu"], e["disp"]) for e in ent]
    assert zeilen == [(20, None), (5, None), (20, 4), (5, 4)]
    line = row("Poisson ist für den Ring entartet")
    has_all(line, f"in {ent[0]['d1_d2']} Szenario", thou(ent[1]["d1_d2"]), thou(ent[2]["d1_d2"]), thou(ent[3]["d1_d2"]),
            " / ".join(str(e["d2_d3"]) for e in ent), thou(ent[0]["N"]))


def test_statements_row():
    z = R.aussagen_messreihe()["zaehlung"]
    line = row("Aussagen der Messreihe")
    has_all(line, "138", f"gilt in {z['A1']['gilt']}", f"gilt nicht in {z['A1']['gilt nicht']}", f"in {z['A2']['gilt']} / {z['A2']['gilt nicht']} / {z['A2']['unklar']} unklar",
            f"({z['A2']['n/a']} nicht anwendbar)", f"in {z['A3']['gilt']} / {z['A3']['gilt nicht']}", f"({z['A3']['n/a']} nicht anwendbar)",
            f"in {z['A4']['gilt']} / {z['A4']['gilt nicht']} / {z['A4']['unklar']} unklar")
    assert R.aussagen_messreihe()["zellen"] == 138 and len(R.cells()) == 147


def test_coverage_row_and_the_correction_bullet():
    z = R.abdeckung_zusammenfassung()
    a1, a1u = z["alle"]["A1"], z["ungemessen"]["A1"]
    unger = sum(a1u.values())
    glatt = [c for k, c in R.basiszelle_zeilen().items() if c["meta"]["disp"] is None and c["meta"]["imb"] is None and c["meta"]["g"] == 1.0 and c["meta"]["mu"] >= 20]
    assert len(glatt) == 36
    line = row("Abdeckung")
    has_all(line, thou(C.N_KOMBINATIONEN), thou(a1["gilt"]), thou(a1["gilt nicht"]), str(a1["unklar"]), f"({thou(unger)})", thou(a1u["gilt"]), "36",
            de(min(R.ring(c) for c in glatt)))
    b = bullet("Die Abdeckung hat die Planungs-Stichprobe korrigiert")
    has_all(b, thou(a1u["gilt"]), thou(unger), de(100 * a1u["gilt"] / unger), thou(a1["gilt"]), thou(C.N_KOMBINATIONEN))
    assert unger == 2700 - 138


def test_best_design_row():
    oc = [c for c in R.cells().values() if "O" in c["entwuerfe"]]
    diffs = [100 * (c["entwuerfe"]["O"]["anteil"] - c["entwuerfe"]["ring1"]["anteil"]) for c in oc]
    n4 = sum(1 for c in oc if c["meta"]["n"] == 4)
    n6 = sum(1 for c in oc if c["meta"]["n"] == 6)
    exakt = {z["mu"]: z for z in j("kzs_n4_exakt.json")["zellen"]}
    line = row("Bester Entwurf")
    ist = sum(1 for c in oc if c["entwuerfe"]["O"]["auswahl"]["ist_ring"])
    has_all(line, f"in {ist} von {len(oc)} Zellen", f"n = 4: {n4}", f"n = 6: {n6}", de(min(diffs), 2).replace("-", "−"), de(max(diffs), 2),
            de(100 * exakt[3]["ring"]), de(100 * exakt[3]["paare"]), de(100 * exakt[3]["schlechtester"]))
    assert j("kzs_n4_exakt.json")["mengen"] == 495 and ist == len(oc) == 59
    assert exakt[3]["bester"] == pytest.approx(exakt[3]["ring"], abs=1e-9)


def test_hot_cold_enumeration_row_and_the_correction_bullet():
    hk = j("kzs_heisskalt.json")
    n6 = {s: hk[f"n=6|struct={s}"] for s in ("block25", "block50", "alt25", "alt50")}
    n4 = {s: hk[f"n=4|struct={s}"] for s in ("block25", "block50", "alt25", "alt50")}
    line = row("Heiß neben kalt gegen die Aufzählung")
    has_all(line, de(100 * n6["block50"]["best_anteil"]), de(100 * n6["block50"]["hk_anteil"]), de(100 * n6["block25"]["hk_anteil"], 2), de(100 * n6["alt25"]["hk_anteil"], 2))
    assert n6["block50"]["best_anteil"] > n6["block50"]["hk_anteil"] and n6["alt50"]["best_anteil"] > n6["alt50"]["hk_anteil"]
    assert n6["block25"]["best_ist_hk_bis_auf_umbenennung"] and n6["alt25"]["best_ist_hk_bis_auf_umbenennung"]
    assert not n6["block50"]["best_ist_hk_bis_auf_umbenennung"]
    b = bullet("Heiß neben kalt ist nicht das Optimum")
    has_all(b, thou(n6["block50"]["mengen"]), thou(n6["block50"]["klassen"]), "495", de(100 * n6["block50"]["best_anteil"]), de(100 * n6["block50"]["hk_anteil"]),
            de(100 * n4["block50"]["hk_anteil"]))


def test_stream_spread_row_and_the_correction_bullet():
    s = j("kzs_streams.json")
    assert s["bloecke"] == 6 and len(s["zeilen"]) == 30
    has_all(row("Streuung über Bedarfsströme"), de(s["verhaeltnis_median"], 2), de(s["verhaeltnis_max"], 2), str(s["anzahl_verhaeltnis"]), de(s["max_sd_punkte"], 2))
    has_all(bullet("Die Streuung über Bedarfsströme"), de(s["verhaeltnis_median"], 2), de(s["verhaeltnis_max"], 2), str(s["anzahl_verhaeltnis"]))


def test_reproduction_and_timing_rows():
    rep = j("kzs_reproduction.json")
    assert rep["zellen"] == 147 and max(rep["abweichungen"].values()) < 1e-13
    has_all(row("Selbst-Reproduktion"), "147", thou(rep["zahlen"]), "1e-13")
    t = j("kzs_timing.json")
    assert t["anzahl"] == 240
    line = row("Rechenzeit")
    g1, g8 = t["g1"], t["g08"]
    has_all(line, "240", f"{de(g1['s1']['median'], 2)} / {de(g1['s1']['p90'], 2)} / {de(g1['s1']['max'], 2)}", f"{de(g8['s1']['median'], 2)} / {de(g8['s1']['p90'], 2)} / {de(g8['s1']['max'], 2)}",
            f"{de(g1['gesamt']['median'], 2)} / {de(g1['gesamt']['p90'], 2)} / {de(g1['gesamt']['max'], 2)}",
            f"{de(g8['gesamt']['median'], 2)} / {de(g8['gesamt']['p90'], 2)} / {de(g8['gesamt']['max'], 2)}", str(round(R.load()["meta"]["sekunden_summe"])))


def test_remaining_numbers_of_the_text():
    # Grenzen: 139 Zellen mit Wirkungsgrad 100 %, kleinster Gewinn, 8 Messpunkte mit Wirkungsgrad 0,8 alle unter 95 %
    assert sum(1 for c in R.cells().values() if c["meta"]["g"] == 1.0) == 139
    assert "139 Zellen" in README
    assert R.aussagen_messreihe()["gruppen"]["Wirkungsgrad 0,8"] == [8, 8] and "allen acht Messpunkten" in README
    gewinn_min = min(R.gewinn_punkte(c) for c in R.cells().values() if c["meta"]["g"] == 1.0)
    assert de(gewinn_min, 2) in README
    assert C.GEWINN_MIN_ANTEIL == 0.5 and "unter 0,5 Punkten" in README
    cov = R.load_coverage()
    assert min(r["gewinn_punkte"] for r in cov["rows"].values()) > C.GEWINN_MIN_ANTEIL
    # Modell- und Methodenzahlen
    assert C.N_SZENARIEN == 20000 and C.N_SZENARIEN_LP == 800 and C.N_KOMBINATIONEN == 2700 and "800 Szenarien" in README and "20.000" in README
    assert "593.775" in README and "4.096" in README and "17.943" in README


def test_preset_seeds_are_the_draws_nearest_to_the_mean():
    import kzs_stories as S
    b = bullet("Zufalls-Seeds der Presets")
    for name in S.PRESET_ORDER:
        p = S.PRESETS[name]
        s = S.preset_settings(name)
        c = R.cell_fuer(s)
        z = c["zufall"]["R"]
        nearest = min(range(z["ziehungen"]), key=lambda i: abs(z["anteile"][i] - z["anteil_mittel"]))
        assert nearest == p["seed"], name
    has_all(b, "Basis 3", "Block 1", "Überstreuung 10", "Kleine Gruppe 1")
