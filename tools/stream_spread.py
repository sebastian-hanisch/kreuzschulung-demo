"""AP 0 (c): Streuung über Bedarfsströme. Der Standardfehler der App ist nur der über die Szenarien (Delta-Methode auf einem Strom). Hier:
30 zufällig gezogene Kombinationen, je 6 Bedarfsströme (Block-Nummern 0 bis 5 des Schlüssels „sw“), Anteil von Ring und Paaren je Strom, Streuung
über die Ströme gegen den mittleren Standardfehler. Schreibt data/kzs_streams.json und druckt eine Zusammenfassung.

Aufruf (Projektordner, Test-venv): python tools/stream_spread.py"""

import json
import pathlib
import statistics as st
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import kzs_constants as C  # noqa: E402
import kzs_designs as DS  # noqa: E402
import kzs_flow as FL  # noqa: E402
import kzs_pipeline as PL  # noqa: E402
import kzs_stats as ST  # noqa: E402
from kzs_rng import SplitMix64, seed_aus  # noqa: E402

BLOECKE = 6


def main():
    rng = SplitMix64(seed_aus("stream_spread"))
    zeilen = []
    for k in range(30):
        n = C.N_OPTIONS[rng.randint(0, len(C.N_OPTIONS) - 1)]
        if n == 2:
            n = 4
        mu = C.MU_OPTIONS[rng.randint(0, 2)]
        r = C.R_OPTIONS[rng.randint(0, 2)]
        dist = C.DIST_ORDER[rng.randint(0, 4)]
        struct = C.STRUCT_ORDER[rng.randint(0, 4)]
        eff = 0.8 if rng.uniform() < 0.25 else 1.0
        s = PL.Settings(n=n, mu=mu, r=r, dist=dist, struct=struct, eff=eff)
        res = {"D1": [], "P": [], "se_D1": [], "se_P": []}
        for b in range(BLOECKE):
            D = PL.szenarien(s, block=b)
            d0, f = FL.bezug(D, s.S1, s.g)
            for nm, q in (("D1", DS.ring(n, 1)), ("P", DS.ketten(n, 2) if n % 2 == 0 else None)):
                if q is None:
                    continue
                kz = ST.kennzahlen(FL.bedient(D, s.S1, q, 1.0, s.g), D, d0, f)
                res[nm].append(kz["anteil"])
                res["se_" + nm].append(kz["se"])
        row = {"n": n, "mu": mu, "r": r, "dist": dist, "struct": struct, "eff": eff}
        for nm in ("D1", "P"):
            if res[nm]:
                row[nm] = {"mittel": float(np.mean(res[nm])), "sd_streams": float(np.std(res[nm], ddof=1)), "se_mittel": float(np.mean(res["se_" + nm])),
                           "werte": res[nm]}
        zeilen.append(row)
        print(k, n, mu, r, dist, struct, eff, "D1 %.3f sd %.4f se %.4f" % (row["D1"]["mittel"], row["D1"]["sd_streams"], row["D1"]["se_mittel"]), flush=True)
    out = {"bloecke": BLOECKE, "zeilen": zeilen}
    # Zusammenfassung: Verhältnis der Streuung über die Ströme zum Standardfehler (nur Zellen mit nennenswertem Standardfehler)
    verh = [z["D1"]["sd_streams"] / z["D1"]["se_mittel"] for z in zeilen if z["D1"]["se_mittel"] > 1e-4]
    out["verhaeltnis_median"] = st.median(verh)
    out["verhaeltnis_max"] = max(verh)
    out["max_sd_punkte"] = 100 * max(z["D1"]["sd_streams"] for z in zeilen)
    out["anzahl_verhaeltnis"] = len(verh)
    (ROOT / "data" / "kzs_streams.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Verhältnis sd über Ströme / Standardfehler: Median %.2f, Max %.2f (%d Zellen); größte Streuung über Ströme %.2f Punkte" % (
        out["verhaeltnis_median"], out["verhaeltnis_max"], len(verh), out["max_sd_punkte"]))


if __name__ == "__main__":
    main()
