"""Preset-Abstimmung (AP 0 f): je Preset (1) die Ziehung der Zufallsentwürfe, die dem Mittel der Zelle am nächsten liegt, (2) der Beispieltag,
an dem die Geschichte des Presets sichtbar wird, und (3) die Kontrolle der Kriterien aus kzs_stories gegen Messreihe und Live-Rechnung.

Aufruf (Projektordner, Test-venv): python tools/seed_search.py
Tagesregeln (Szenarien der Einstellung, Wirkungsgrad 100 %):
  Ring, Paare, Zufall / Wie viele lernen? / Kleine Gruppe: unter den Tagen, an denen F nichts liegen lässt und der Ring (bei „Wie viele lernen?“ der Ring mit
    Anteil geschult) höchstens soviel wie F, der Tag mit der größten Unterdeckung von D0 (der Ring hebt sie auf).
  Block-Ungleichgewicht: unter den Tagen, an denen F und die Vorlage heiß neben kalt nichts liegen lassen, der Tag mit der größten Unterdeckung des Rings.
  Überstreuung: unter den Tagen, an denen D2 nichts liegen lässt, der Tag mit der größten Unterdeckung des Rings."""

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import kzs_designs as DS  # noqa: E402
import kzs_flow as FL  # noqa: E402
import kzs_pipeline as PL  # noqa: E402
import kzs_stories as S  # noqa: E402


def unmet(D, S1, q, anteil=1.0):
    return D.sum(1) - FL.bedient(D, S1, q, anteil)


def tag_fuer(name):
    s = S.preset_settings(name)
    D = PL.szenarien(s)
    n, S1 = s.n, s.S1
    d0 = unmet(D, S1, DS.ring(n, 0))
    f = unmet(D, S1, DS.voll(n))
    ring = unmet(D, S1, DS.ring(n, 1), s.q)
    eps = 1e-9
    if name == "Block-Ungleichgewicht":
        hk = unmet(D, S1, DS.ring_in_reihenfolge(DS.heiss_neben_kalt(s.skala)))
        ok = (f <= eps) & (hk <= eps)
        score = np.where(ok, ring, -1.0)
    elif name == "Überstreuung":
        d2 = unmet(D, S1, DS.ring(n, 2))
        ok = d2 <= eps
        score = np.where(ok, ring, -1.0)
    else:
        ok = (f <= eps) & (ring <= f + eps)
        score = np.where(ok, d0, -1.0)
    t = int(np.argmax(score))
    return t, float(d0[t]), float(ring[t]), float(f[t]), int(ok.sum())


def main():
    for name in S.PRESET_ORDER:
        s = S.preset_settings(name)
        t, d0, ring, f, n_ok = tag_fuer(name)
        print(f"{name}: Tag {t} (D0 unterdeckt {d0:.0f}, Ring {ring:.0f}, F {f:.0f}; {n_ok} passende Tage)")
        mf = S.measured_facts(name)
        inf = S.instance_facts(name)
        for label, ok, v in S.check(name, mf):
            print(f"   Messreihe: {'ok ' if ok else ('-- ' if ok is None else 'FEHLT')} {label}: {v if v is None else round(v, 2)}")
        for label, ok, v in S.check(name, inf):
            if not ok:
                print(f"   live: {'--' if ok is None else 'FEHLT'} {label}: {v if v is None else round(v, 2)}")
    # Ziehungen nahe am Mittel
    from kzs_results import cell
    for name in S.PRESET_ORDER:
        p = S.PRESETS[name]
        s = S.preset_settings(name)
        c = cell(s.n, s.mu, s.disp, s.korr, s.r, s.g, s.imb)
        if c is None or "R" not in c["zufall"]:
            continue
        z = c["zufall"]["R"]
        best = min(range(z["ziehungen"]), key=lambda i: abs(z["anteile"][i] - z["anteil_mittel"]))
        print(f"{name}: gewählter Zufalls-Seed {p['seed']}: {100 * z['anteile'][p['seed']]:.1f} % (Mittel {100 * z['anteil_mittel']:.1f} %); "
              f"nächste Ziehung zum Mittel: {best} mit {100 * z['anteile'][best]:.1f} %")


if __name__ == "__main__":
    main()
