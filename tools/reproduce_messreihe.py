"""Selbst-Reproduktion (Bau-Gate, AP 0a): der Live-Pfad der App rechnet alle Zellen der Vorab-Messreihe nach und vergleicht jede Zahl
(Servicegrad, Unterdeckung, Anteil, Standardfehler, jede Ziehung der Zufallsentwürfe, die Teil-Zellen) mit den gespeicherten Werten.

Aufruf (Projektordner, Test-venv):
    python tools/reproduce_messreihe.py [--daten PFAD] [--zellen N] [--toleranz 1e-12]
Standard-Datenquelle: data/kzs_results.json. Der Lauf rechnet das Auswahlverfahren O nicht (n = 4 und 6, Aufzählung) und vergleicht es nicht."""

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import kzs_constants as C  # noqa: E402
import kzs_pipeline as PL  # noqa: E402

NAMEN = {"ring1": "D1", "ring2": "D2", "ring3": "D3", "ring4": "D4"}
INV_DIST = {v: k for k, v in C.DIST_PARAMS.items()}
INV_STRUCT = {(v if v is None else tuple(v)): k for k, v in C.STRUCT_PARAMS.items()}


def settings_aus_meta(m):
    imb = tuple(m["imb"]) if m["imb"] else None
    return PL.Settings(n=m["n"], mu=m["mu"], r=m["r"], dist=INV_DIST[(m["disp"], m["korr"])], struct=INV_STRUCT[imb], eff=m["g"], q=1.0, seed=0)


def vergleiche_zelle(key, c):
    """Alle vergleichbaren Zahlen einer Zelle; Rückgabe: (Anzahl, größte Abweichungen je Art)."""
    s = settings_aus_meta(c["meta"])
    abw = {"sg": 0.0, "unterdeckung": 0.0, "anteil": 0.0, "se": 0.0, "zufall": 0.0, "teil": 0.0, "teil_se": 0.0}
    zahl = 0
    if key.endswith("teil=True"):
        s3 = PL.stufe3(s)
        for art, name in (("ring", "D1"), ("paar", "P")):
            if name not in s3:
                continue
            for q, (a, se) in zip(C.Q_OPTIONS, s3[name]):
                ref = c["teil"]["%s_q%s" % (art, q)]
                abw["teil"] = max(abw["teil"], abs(a - ref["anteil"]))
                abw["teil_se"] = max(abw["teil_se"], abs(se - ref["anteil_se"]))
                zahl += 2
    s1 = PL.stufe1(s)["designs"]
    for nm0, v in c["entwuerfe"].items():
        nm = NAMEN.get(nm0, nm0)
        if nm == "O" or nm not in s1:
            continue
        live = s1[nm]
        abw["sg"] = max(abw["sg"], abs(live["sg"] - v["sg"]))
        abw["unterdeckung"] = max(abw["unterdeckung"], abs(live["unterdeckung"] - v["unterdeckung"]))
        zahl += 2
        if v["anteil"] is not None and live["anteil"] is not None:
            abw["anteil"] = max(abw["anteil"], abs(live["anteil"] - v["anteil"]))
            zahl += 1
        if v["anteil_se"] is not None and live["se"] is not None:
            abw["se"] = max(abw["se"], abs(live["se"] - v["anteil_se"]))
            zahl += 1
    if c["zufall"]:
        s2 = PL.stufe2(s)
        for fam, v in c["zufall"].items():
            live = s2[fam]["anteile"]
            assert len(live) == v["ziehungen"], (key, fam)
            for a, b in zip(live, v["anteile"]):
                abw["zufall"] = max(abw["zufall"], abs(a - b))
                zahl += 1
    return zahl, abw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daten", default=str(ROOT / "data" / "kzs_results.json"))
    ap.add_argument("--zellen", type=int, default=0, help="nur die ersten N Zellen (0 = alle)")
    ap.add_argument("--toleranz", type=float, default=1e-12)
    ap.add_argument("--schreiben", action="store_true", help="Ergebnis nach data/kzs_reproduction.json schreiben (nur bei allen Zellen)")
    args = ap.parse_args()
    daten = json.loads(pathlib.Path(args.daten).read_text(encoding="utf-8"))
    cells = daten["cells"] if "cells" in daten else daten
    items = list(cells.items())
    if args.zellen:
        items = items[:args.zellen]
    t0 = time.time()
    gesamt, zahl_gesamt, schlecht = {}, 0, []
    for i, (key, c) in enumerate(items, 1):
        zahl, abw = vergleiche_zelle(key, c)
        zahl_gesamt += zahl
        for k, v in abw.items():
            gesamt[k] = max(gesamt.get(k, 0.0), v)
            if v > args.toleranz:
                schlecht.append((key, k, v))
        if i % 20 == 0:
            print("... %d Zellen, %.0f s" % (i, time.time() - t0), flush=True)
    print("Zellen: %d, verglichene Zahlen: %d, Dauer %.0f s" % (len(items), zahl_gesamt, time.time() - t0))
    print("größte Abweichungen:", {k: "%.2e" % v for k, v in gesamt.items()})
    for key, k, v in schlecht[:10]:
        print("ÜBER TOLERANZ:", key, k, v)
    if args.schreiben and not args.zellen:
        out = {"zellen": len(items), "zahlen": zahl_gesamt, "sekunden": round(time.time() - t0), "abweichungen": gesamt, "toleranz": args.toleranz}
        (ROOT / "data" / "kzs_reproduction.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if schlecht else 0


if __name__ == "__main__":
    sys.exit(main())
