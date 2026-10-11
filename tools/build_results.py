"""Erzeugt data/kzs_results.json aus der Vorab-Messreihe (sweep_data.json, nur gelesen) und ergänzt Messungen mit dem Live-Pfad der App.

Aufruf (Projektordner, Test-venv):
    python tools/build_results.py [--sweep PFAD_ZU_sweep_data.json] [--ohne-extras]

Inhalt: "cells" (147 Zellen der Messreihe, auf die Felder reduziert, die die App und die Tests brauchen, volle Genauigkeit),
"extras" (Messungen dieses Repos: Zahl der Szenarien, in denen Nachbarn D1/D2/D3 abweichen; Ring und Paare in der Reihenfolge
heiß, kalt, heiß, kalt auf den Block-Zellen), "meta" (Herkunft). Nichts davon wird im Browser gerechnet."""

import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import kzs_constants as C  # noqa: E402
import kzs_designs as DS  # noqa: E402
import kzs_flow as FL  # noqa: E402
import kzs_pipeline as PL  # noqa: E402
import kzs_stats as ST  # noqa: E402
from kzs_demand import bedarf  # noqa: E402

STANDARD_QUELLE = pathlib.Path(r"C:\Users\sebas\Claude Code Projects\personal-planung\messreihe_kreuzschulung\sweep_data.json")
ENTW_FELDER = ("bogen", "sg", "unterdeckung", "anteil", "anteil_se")
ZUFALL_FELDER = ("bogen", "sg", "unterdeckung", "anteil_mittel", "anteil_sd", "anteil_min", "anteil_max", "ziehungen", "anteile")


def reduziere(c):
    out = {"meta": {k: c["meta"][k] for k in ("n", "mu", "disp", "korr", "r", "g", "imb", "N", "sd_bedarf", "kapazitaet", "sekunden")},
           "entwuerfe": {}, "zufall": {}, "teil": {}, "d0_f_diff": c["d0_f_diff"]}
    for nm, v in c["entwuerfe"].items():
        e = {k: v[k] for k in ENTW_FELDER}
        if "auswahl" in v:
            e["auswahl"] = v["auswahl"]
        out["entwuerfe"][nm] = e
    for fam, v in c["zufall"].items():
        out["zufall"][fam] = {k: v[k] for k in ZUFALL_FELDER}
    for nm, v in c["teil"].items():
        out["teil"][nm] = {"anteil": v["anteil"], "anteil_se": v["anteil_se"], "geschult_anteil": v["geschult_anteil"]}
    return out


def entartung():
    """Szenarien (von 20.000), in denen Nachbarn D1/D2 bzw. D2/D3 abweichen, auf einem eigenen Bedarfsstrom (Schlüssel t8z), n = 6."""
    rows = []
    for mu, disp, korr in ((20, None, 0.0), (5, None, 0.0), (20, 4, 0.0), (5, 4, 0.0)):
        D = bedarf(6, mu, disp, korr, N=C.N_SZENARIEN, block=0, schluessel="t8z")
        S = float(mu)
        v = [FL.bedient(D, S, DS.ring(6, k)) for k in (1, 2, 3)]
        rows.append({"mu": mu, "disp": disp, "korr": korr, "d1_d2": int((np.abs(v[1] - v[0]) > 1e-9).sum()),
                     "d2_d3": int((np.abs(v[2] - v[1]) > 1e-9).sum()), "N": C.N_SZENARIEN})
    return rows


def paare_in_reihenfolge(n, order):
    q = [0] * n
    for k in range(0, n, 2):
        a, b = order[k], order[k + 1]
        q[a] = DS.bits(a, b)
        q[b] = DS.bits(b, a)
    return tuple(q)


def verschraenkt():
    """Block-Fälle (mu = 20, Poisson, r = 1): Ring und Paare in der Reihenfolge heiß, kalt, heiß, kalt; gleiche Szenarien wie die Zelle."""
    rows = []
    for n, struct in ((6, "block50"), (12, "block50"), (12, "block25")):
        s = PL.Settings(n=n, mu=20, r=1.0, dist="poisson", struct=struct, eff=1.0, q=1.0, seed=0)
        D = PL.szenarien(s)
        d0, f = FL.bezug(D, s.S1, 1.0)
        order = DS.heiss_neben_kalt(s.skala)
        res = {"n": n, "struct": struct}
        for name, q in (("ring", DS.ring_in_reihenfolge(order)), ("paare", paare_in_reihenfolge(n, order)),
                        ("ring_stationsreihenfolge", DS.ring(n, 1)), ("paare_nachbarn", DS.ketten(n, 2))):
            kz = ST.kennzahlen(FL.bedient(D, s.S1, q), D, d0, f)
            res[name] = {"anteil": kz["anteil"], "se": kz["se"], "bogen": DS.zahl_bogen(q)}
        res["order"] = order
        rows.append(res)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default=str(STANDARD_QUELLE))
    ap.add_argument("--ohne-extras", action="store_true")
    args = ap.parse_args()
    quelle = pathlib.Path(args.sweep)
    roh = json.loads(quelle.read_text(encoding="utf-8"))
    cells = {k: reduziere(c) for k, c in roh.items()}
    out = {"meta": {"quelle": "messreihe_kreuzschulung/sweep_data.json (Vorab-Messreihe 2026-10-11)", "zellen": len(cells),
                    "szenarien": C.N_SZENARIEN, "szenarien_lp": C.N_SZENARIEN_LP,
                    "sekunden_summe": round(sum(c["meta"]["sekunden"] for c in roh.values()), 1)},
           "cells": cells}
    if not args.ohne_extras:
        out["extras"] = {"entartung": entartung(), "verschraenkt": verschraenkt()}
    ziel = ROOT / "data" / "kzs_results.json"
    text = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    ziel.parent.mkdir(exist_ok=True)
    ziel.write_text(text, encoding="utf-8")
    print("geschrieben:", ziel, "(%d Zellen, %d kB)" % (len(cells), len(text) // 1024))
    if "extras" in out:
        print(json.dumps(out["extras"], ensure_ascii=False, indent=1)[:2500])


if __name__ == "__main__":
    main()
