"""Zeitmessung je Stufe (AP 0 e): zufällige Reglerkombinationen (alle Verteilungen, Strukturen, n, mu, r, Wirkungsgrad, Anteil geschult, Eigener Entwurf),
Median, 90. Perzentil und Maximum je Stufe in Sekunden, getrennt nach Wirkungsgrad. Schreibt data/kzs_timing.json.

Aufruf (Projektordner, Test-venv): python tools/live_timing.py [--anzahl 240]
Die Zeiten hängen von der Last des Geräts ab (parallele Sitzungen): sie sind Richtwerte, keine Zusagen; Streamlit Cloud ist nicht gemessen."""

import argparse
import json
import pathlib
import statistics as st
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import kzs_constants as C  # noqa: E402
import kzs_designs as DS  # noqa: E402
import kzs_pipeline as PL  # noqa: E402
from kzs_rng import SplitMix64, seed_aus  # noqa: E402


def quantile(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def kennzahl(zeiten):
    return {"median": st.median(zeiten), "p90": quantile(zeiten, 0.9), "max": max(zeiten), "n": len(zeiten)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anzahl", type=int, default=240)
    args = ap.parse_args()
    rng = SplitMix64(seed_aus("live_timing"))
    zeilen = []
    for k in range(args.anzahl):
        n = C.N_OPTIONS[rng.randint(0, len(C.N_OPTIONS) - 1)]
        eff = 0.8 if rng.uniform() < 0.3 else 1.0
        own = ()
        if n >= 3 and rng.uniform() < 0.5:
            own = tuple((((j + rng.randint(1, n - 1)) % n),) for j in range(n))
        s = PL.Settings(n=n, mu=C.MU_OPTIONS[rng.randint(0, 2)], r=C.R_OPTIONS[rng.randint(0, 2)], dist=C.DIST_ORDER[rng.randint(0, 4)],
                        struct=C.STRUCT_ORDER[rng.randint(0, 4)], eff=eff, q=C.Q_OPTIONS[rng.randint(0, len(C.Q_OPTIONS) - 1)],
                        seed=rng.randint(0, 99), own=own)
        t0 = time.perf_counter()
        PL.stufe1(s)
        t1 = time.perf_counter()
        PL.stufe2(PL.Settings(**{**s.__dict__, "seed": 0, "own": ()}))
        t2 = time.perf_counter()
        PL.stufe3(PL.Settings(**{**s.__dict__, "seed": 0, "q": 1.0}))
        t3 = time.perf_counter()
        t = PL.beispieltag(s, DS.ring(n, 1), rng.randint(0, 19999))
        t4 = time.perf_counter()
        zeilen.append({"n": n, "eff": eff, "s1": t1 - t0, "s2": t2 - t1, "s3": t3 - t2, "tag": t4 - t3, "gesamt": t3 - t0})
    out = {"anzahl": len(zeilen)}
    for lab, sel in (("g1", [z for z in zeilen if z["eff"] >= 1.0]), ("g08", [z for z in zeilen if z["eff"] < 1.0]), ("alle", zeilen)):
        out[lab] = {st_: kennzahl([z[st_] for z in sel]) for st_ in ("s1", "s2", "s3", "tag", "gesamt")}
    out["s1_je_n"] = {str(n): {"g1": kennzahl([z["s1"] for z in zeilen if z["n"] == n and z["eff"] >= 1.0] or [0.0]),
                               "g08": kennzahl([z["s1"] for z in zeilen if z["n"] == n and z["eff"] < 1.0] or [0.0])} for n in C.N_OPTIONS}
    (ROOT / "data" / "kzs_timing.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for lab in ("g1", "g08", "alle"):
        print(lab, {k: "%.2f / %.2f / %.2f (n=%d)" % (v["median"], v["p90"], v["max"], v["n"]) for k, v in out[lab].items()})


if __name__ == "__main__":
    main()
