"""AP 0 (d): Ist die Regel „heiß neben kalt“ ein Optimum? Aufzählung aller Mengen aus n Bögen im Ungleichgewicht (Block und abwechselnd,
±25 % und ±50 %) für n = 4 (495 Mengen) und n = 6 (593.775 Mengen, bis auf Umbenennung innerhalb der heißen und innerhalb der kalten Stationen),
Auswahl auf eigenen Szenarien (Block 1000), Bewertung auf den Szenarien der Zelle (Block 0), Vergleich mit dem Ring in der Reihenfolge heiß neben
kalt und dem Ring in der Stationsreihenfolge. Schreibt data/kzs_heisskalt.json.

Aufruf (Projektordner, Test-venv): python tools/heiss_kalt_aufzaehlung.py [--n 4 6]"""

import argparse
import itertools
import json
import pathlib
import sys
import time

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

ZIEL = ROOT / "data" / "kzs_heisskalt.json"


def klassen_mit_symmetrie(n, k, gruppen):
    """Mengen aus k Zusatzbögen bis auf Umbenennung innerhalb der Stationsgruppen `gruppen` (Liste von Listen). Rückgabe: (Vertreter-Bogenlisten,
    Vielfachheiten)."""
    bogen = [(j, i) for j in range(n) for i in range(n) if i != j]
    idx = {b: a for a, b in enumerate(bogen)}
    kombi = np.array(list(itertools.combinations(range(len(bogen)), k)), dtype=np.int64)
    masken = (np.int64(1) << kombi).sum(axis=1)
    kanon = masken.copy()
    for teile in itertools.product(*[itertools.permutations(g) for g in gruppen]):
        perm = list(range(n))
        for g, pg in zip(gruppen, teile):
            for a, b in zip(g, pg):
                perm[a] = b
        pa = np.array([idx[(perm[j], perm[i])] for (j, i) in bogen], dtype=np.int64)
        kanon = np.minimum(kanon, (np.int64(1) << pa[kombi]).sum(axis=1))
    werte, anz = np.unique(kanon, return_counts=True)
    out = [tuple(bogen[b] for b in range(len(bogen)) if (int(w) >> b) & 1) for w in werte]
    return out, [int(a) for a in anz], int(len(kombi))


def kanonisch(n, bogen, gruppen):
    best = None
    for teile in itertools.product(*[itertools.permutations(g) for g in gruppen]):
        perm = list(range(n))
        for g, pg in zip(gruppen, teile):
            for a, b in zip(g, pg):
                perm[a] = b
        m = tuple(sorted((perm[j], perm[i]) for (j, i) in bogen))
        best = m if best is None or m < best else best
    return best


def bogen_aus_masken(q):
    n = len(q)
    return [(j, i) for j in range(n) for i in range(n) if i != j and (q[j] >> i) & 1]


def zelle(n, struct):
    s = PL.Settings(n=n, mu=20, r=1.0, dist="poisson", struct=struct, eff=1.0, q=1.0, seed=0)
    skala = s.skala
    heiss = [i for i in range(n) if skala[i] > 1.0]
    kalt = [i for i in range(n) if skala[i] < 1.0]
    gruppen = [g for g in (heiss, kalt) if len(g) > 1]
    t0 = time.time()
    klassen, vielf, summe = klassen_mit_symmetrie(n, n, gruppen)
    t_klassen = time.time() - t0
    Dsel = PL.szenarien(s, N=C.N_AUSWAHL, block=C.AUSWAHL_BLOCK)
    D = PL.szenarien(s)
    d0, f = FL.bezug(D, s.S1, 1.0)
    # Auswahl in Blöcken
    mittel = np.empty(len(klassen))
    for a, bogen in enumerate(klassen):
        mittel[a] = FL.bedient_gruppiert(Dsel, np.full(n, s.S1), DS.aus_bogen(n, bogen)).mean()
    rang = np.argsort(-mittel)[:5]
    top = []
    for a in rang:
        q = DS.aus_bogen(n, klassen[a])
        kz = ST.kennzahlen(FL.bedient_gruppiert(D, np.full(n, s.S1), q), D, d0, f)
        top.append({"bogen": [list(b) for b in klassen[a]], "auswahl_mittel": float(mittel[a]), "anteil": kz["anteil"], "se": kz["se"],
                    "vielfachheit": vielf[a]})
    best_q = DS.aus_bogen(n, klassen[int(rang[0])])
    order = DS.heiss_neben_kalt(skala)
    hk = DS.ring_in_reihenfolge(order)
    kz_hk = ST.kennzahlen(FL.bedient_gruppiert(D, np.full(n, s.S1), hk), D, d0, f)
    kz_ring = ST.kennzahlen(FL.bedient_gruppiert(D, np.full(n, s.S1), DS.ring(n, 1)), D, d0, f)
    kz_best = ST.kennzahlen(FL.bedient_gruppiert(D, np.full(n, s.S1), best_q), D, d0, f)
    # bester nach Bewertung unter den fünf besten der Auswahl und Gleichheit mit der Regel bis auf Umbenennung
    gleich = kanonisch(n, bogen_aus_masken(best_q), gruppen) == kanonisch(n, bogen_aus_masken(hk), gruppen)
    return {"n": n, "struct": struct, "mengen": summe, "klassen": len(klassen), "sekunden_klassen": round(t_klassen, 1),
            "best_anteil": kz_best["anteil"], "best_se": kz_best["se"], "hk_anteil": kz_hk["anteil"], "hk_se": kz_hk["se"],
            "ring_anteil": kz_ring["anteil"], "ring_se": kz_ring["se"], "best_ist_hk_bis_auf_umbenennung": bool(gleich),
            "hk_unter_den_fuenf_besten": any(kanonisch(n, [tuple(b) for b in t["bogen"]], gruppen) == kanonisch(n, bogen_aus_masken(hk), gruppen) for t in top),
            "top": top, "sekunden": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, nargs="+", default=[4, 6])
    args = ap.parse_args()
    out = json.loads(ZIEL.read_text(encoding="utf-8")) if ZIEL.exists() else {}
    for n in args.n:
        for struct in ("block25", "block50", "alt25", "alt50"):
            key = f"n={n}|struct={struct}"
            r = zelle(n, struct)
            out[key] = r
            ZIEL.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
            print(key, "Klassen %d, bester %.4f (se %.4f), heiß neben kalt %.4f, Ring %.4f, gleich %s, in Top 5: %s, %.0f s" % (
                r["klassen"], r["best_anteil"], r["best_se"], r["hk_anteil"], r["ring_anteil"], r["best_ist_hk_bis_auf_umbenennung"],
                r["hk_unter_den_fuenf_besten"], r["sekunden"]), flush=True)


if __name__ == "__main__":
    main()
