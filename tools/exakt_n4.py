"""Bester Entwurf bei n = 4 durch vollständige Aufzählung aller 495 Mengen aus 4 Bögen mit exakter Erwartung über das abgeschnittene
Poisson-Raster (Rechenweg unabhängig vom Live-Pfad: Aufzählung aller 2^n Teilmengen). Schreibt data/kzs_n4_exakt.json.

Aufruf (Projektordner, Test-venv): python tools/exakt_n4.py"""

import itertools
import json
import pathlib
import sys

import numpy as np
from scipy.stats import poisson

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import kzs_designs as DS  # noqa: E402


def erwartung(n, mu, S1, entwuerfe, dmax):
    grid = np.array(list(itertools.product(range(dmax + 1), repeat=n)), float)
    w = np.prod(poisson.pmf(grid, mu), axis=1)
    t = np.arange(1 << n)
    notin = (1.0 - ((t[:, None] >> np.arange(n)[None, :]) & 1)).astype(float)
    dt = grid @ notin.T
    out = []
    for q in entwuerfe:
        cap = np.zeros(1 << n)
        for j in range(n):
            cap += S1 * ((t & q[j]) != 0)
        out.append(float((dt + cap[None, :]).min(axis=1) @ w) / float(w.sum()))
    return np.array(out)


def main():
    n = 4
    bogen = [(j, i) for j in range(n) for i in range(n) if i != j]
    ents = [DS.aus_bogen(n, b) for b in itertools.combinations(bogen, n)]
    out = {"mengen": len(ents), "zellen": []}
    for mu in (2, 3):
        dmax = int(mu * 5 + 8)
        ex = erwartung(n, mu, float(mu), ents, dmax)
        d0, f, ring, paare = erwartung(n, mu, float(mu), [DS.ring(n, 0), DS.voll(n), DS.ring(n, 1), DS.ketten(n, 2)], dmax)
        a = lambda x: float((x - d0) / (f - d0))  # noqa: E731
        out["zellen"].append({"mu": mu, "r": 1.0, "dmax": dmax, "ring": a(ring), "paare": a(paare), "bester": a(ex.max()), "schlechtester": a(ex.min())})
        print(out["zellen"][-1], flush=True)
    (ROOT / "data" / "kzs_n4_exakt.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
