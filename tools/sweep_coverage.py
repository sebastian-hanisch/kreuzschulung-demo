"""Abdeckung (AP 0b): alle 2.700 Kombinationen aus Zahl der Stationen, Bedarf, Kapazität, Verteilung, Struktur und Wirkungsgrad mit dem
Live-Pfad der App rechnen (Stufe 1, 2 und 3: alle festen Entwürfe, Zufallsentwürfe über die Ziehungen der Messreihe, Kurve der
Teilqualifikation von Ring und Paaren) und nach data/kzs_coverage.json schreiben.

Aufruf (Projektordner, Test-venv):
    python tools/sweep_coverage.py [--jobs 6] [--neu] [--grenze N]
Wiederaufnahme: schon gerechnete Kombinationen stehen in tools/_coverage_teil.json und werden übersprungen (--neu rechnet alles neu).
Der Lauf nutzt höchstens --jobs Prozesse (Standard 6); er beendet nie fremde Prozesse."""

import argparse
import itertools
import json
import os
import pathlib
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import kzs_constants as C  # noqa: E402
import kzs_pipeline as PL  # noqa: E402

TEIL = ROOT / "tools" / "_coverage_teil.json"
ZIEL = ROOT / "data" / "kzs_coverage.json"
RUND = 6


def kombi_schluessel(n, mu, r, dist, struct, eff):
    return "n=%s|mu=%s|r=%s|dist=%s|struct=%s|eff=%s" % (n, mu, r, dist, struct, eff)


def alle_kombinationen():
    return [(n, mu, r, dist, struct, eff) for n, mu, r, dist, struct, eff in
            itertools.product(C.N_OPTIONS, C.MU_OPTIONS, C.R_OPTIONS, C.DIST_ORDER, C.STRUCT_ORDER, C.EFF_OPTIONS)]


def _runde(x):
    if isinstance(x, float):
        return round(x, RUND)
    if isinstance(x, dict):
        return {k: _runde(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_runde(v) for v in x]
    return x


def rechne(kombi):
    n, mu, r, dist, struct, eff = kombi
    t0 = time.perf_counter()
    s = PL.Settings(n=n, mu=mu, r=r, dist=dist, struct=struct, eff=eff)
    rec = PL.abdeckung_satz(s)
    rec["sekunden"] = time.perf_counter() - t0
    return kombi_schluessel(*kombi), _runde(rec)


def kosten(kombi):
    n, mu, r, dist, struct, eff = kombi
    return (n ** 2) * (8 if eff < 1.0 else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--neu", action="store_true")
    ap.add_argument("--grenze", type=int, default=0, help="nur die ersten N offenen Kombinationen (Test)")
    args = ap.parse_args()
    jobs = max(1, min(args.jobs, 6))
    fertig = {}
    if TEIL.exists() and not args.neu:
        fertig = json.loads(TEIL.read_text(encoding="utf-8"))
    offen = [k for k in alle_kombinationen() if kombi_schluessel(*k) not in fertig]
    offen.sort(key=kosten, reverse=True)
    if args.grenze:
        offen = offen[:args.grenze]
    print("Kombinationen: %d gesamt, %d offen, %d Prozesse" % (len(alle_kombinationen()), len(offen), jobs), flush=True)
    t0 = time.time()
    if offen:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            for i, (key, rec) in enumerate(ex.map(rechne, offen, chunksize=4), 1):
                fertig[key] = rec
                if i % 50 == 0 or i == len(offen):
                    tmp = TEIL.with_suffix(".tmp")
                    tmp.write_text(json.dumps(fertig, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                    os.replace(tmp, TEIL)
                    print("... %d/%d, %.0f s" % (i, len(offen), time.time() - t0), flush=True)
    if len(fertig) == C.N_KOMBINATIONEN:
        out = {"meta": {"kombinationen": len(fertig), "szenarien": C.N_SZENARIEN, "szenarien_lp": C.N_SZENARIEN_LP,
                        "sekunden_summe": round(sum(r["sekunden"] for r in fertig.values()), 1),
                        "regler": ["n", "mu", "r", "dist", "struct", "eff"]},
               "rows": {k: fertig[k] for k in sorted(fertig)}}
        ZIEL.parent.mkdir(exist_ok=True)
        ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print("geschrieben:", ZIEL, "(%d Kombinationen)" % len(fertig))
    print("Dauer %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
