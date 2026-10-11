"""Vorgerechnete Ergebnisse: Messreihe (data/kzs_results.json, 147 Zellen) und Abdeckung (data/kzs_coverage.json, alle 2.700 Kombinationen).

Nichts davon wird im Browser gerechnet. Die Aussagen A1 bis A5 werden auf zwei Standardfehler genommen (gilt / gilt nicht / unklar)."""

import json
import math
import pathlib
from functools import lru_cache

import kzs_constants as C

DATA = pathlib.Path(__file__).resolve().parent / "data"
INV_DIST = {v: k for k, v in C.DIST_PARAMS.items()}
INV_STRUCT = {(v if v is None else tuple(v)): k for k, v in C.STRUCT_PARAMS.items()}
NAMEN = {"ring1": "D1", "ring2": "D2", "ring3": "D3", "ring4": "D4"}

AUSSAGEN = {
    "A1": "Der Ring holt mindestens 95 % des Nutzens.",
    "A2": "Paare holen höchstens 60 %.",
    "A3": "Der Ring liegt mindestens 20 Punkte über dem Zufall (Mittel).",
    "A4": "Ein zweiter Bogen je Gruppe (D2) bringt mindestens 5 Punkte über den Ring.",
    "A5": "Der Zufall liegt im Mittel über dem Ring.",
}


@lru_cache(maxsize=1)
def load():
    return json.loads((DATA / "kzs_results.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_coverage():
    p = DATA / "kzs_coverage.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def cells():
    return load()["cells"]


def extras():
    return load()["extras"]


def schluessel(n, mu, disp=None, korr=0.0, r=1.0, g=1.0, imb=None, teil=False):
    return "n=%s|mu=%s|disp=%s|korr=%s|r=%s|g=%s|imb=%s|teil=%s" % (n, mu, disp, korr, r, g, imb, teil)


def cell(n, mu, disp=None, korr=0.0, r=1.0, g=1.0, imb=None, teil=False):
    return cells().get(schluessel(n, mu, disp, korr, r, g, imb, teil))


def cell_fuer(s, teil=False):
    return cell(s.n, s.mu, s.disp, s.korr, s.r, s.g, s.imb, teil)


def kombination_aus_meta(m):
    imb = tuple(m["imb"]) if m["imb"] else None
    return (m["n"], m["mu"], m["r"], INV_DIST[(m["disp"], m["korr"])], INV_STRUCT[imb], m["g"])


@lru_cache(maxsize=1)
def messpunkte():
    """Die verschiedenen Reglerkombinationen der Messreihe (n, mu, r, dist, struct, eff): 138 von 2.700."""
    return frozenset(kombination_aus_meta(c["meta"]) for c in cells().values())


@lru_cache(maxsize=1)
def teil_kombinationen():
    return frozenset(kombination_aus_meta(c["meta"]) for k, c in cells().items() if k.endswith("teil=True"))


def ist_messpunkt(s):
    return (s.n, s.mu, s.r, s.dist, s.struct, s.eff) in messpunkte()


def zustand(s):
    """Zustand einer Einstellung gegenüber der Messreihe: "gemessen" (Messpunkt; Anteil geschult 100 % oder eine der 9 Teil-Zellen),
    "bedingt" (Messpunkt, aber Anteil geschult unter 100 % in einer Kombination ohne Teil-Zelle) oder "nicht gemessen" (kein Messpunkt)."""
    kombi = (s.n, s.mu, s.r, s.dist, s.struct, s.eff)
    if kombi not in messpunkte():
        return "nicht gemessen"
    if s.q < 1.0 and kombi not in teil_kombinationen():
        return "bedingt"
    return "gemessen"


# --- Zugriff in Prozent --------------------------------------------------------------------------------------------------------------

def anteil(c, nm):
    """Anteil in Prozent (None: nicht vorhanden oder nicht definiert). Namen der Messreihe (ring1) werden mit D1 usw. übersetzt."""
    inv = {v: k for k, v in NAMEN.items()}
    v = c["entwuerfe"].get(inv.get(nm, nm))
    return None if v is None or v["anteil"] is None else 100.0 * v["anteil"]


def se(c, nm):
    inv = {v: k for k, v in NAMEN.items()}
    v = c["entwuerfe"].get(inv.get(nm, nm))
    return None if v is None or v["anteil_se"] is None else 100.0 * v["anteil_se"]


def zufall_mittel(c, fam="R"):
    return None if fam not in c["zufall"] else 100.0 * c["zufall"][fam]["anteil_mittel"]


def ring(c):
    """Ring-Anteil in Prozent; bei n = 2 ist der Ring per Konstruktion voll (die Messreihe führt ihn dort nicht eigens)."""
    return anteil(c, "D1") if "ring1" in c["entwuerfe"] else 100.0


def ring2(c):
    if "ring2" in c["entwuerfe"]:
        return anteil(c, "D2")
    return 100.0 if c["meta"]["n"] <= 3 else None


def gewinn_punkte(c):
    return 100.0 * (c["entwuerfe"]["F"]["sg"] - c["entwuerfe"]["D0"]["sg"])


def gewinn_pt(c):
    return c["entwuerfe"]["D0"]["unterdeckung"] - c["entwuerfe"]["F"]["unterdeckung"]


def urteil(wert, s, schwelle, richtung):
    """gilt / gilt nicht / unklar auf zwei Standardfehler; n/a ohne Wert."""
    if wert is None:
        return "n/a"
    if richtung == ">=":
        if wert - C.SE_FAKTOR * s >= schwelle:
            return "gilt"
        if wert + C.SE_FAKTOR * s < schwelle:
            return "gilt nicht"
        return "unklar"
    if wert + C.SE_FAKTOR * s <= schwelle:
        return "gilt"
    if wert - C.SE_FAKTOR * s > schwelle:
        return "gilt nicht"
    return "unklar"


def aussagen(d1, se1, d2, se2, p, se_p, r_mittel):
    """A1 bis A5 aus Prozentwerten (Anteil, Standardfehler); r_mittel: Mittel der Zufallsziehungen (R)."""
    out = {"A1": urteil(d1, se1, C.RING_HOCH, ">="),
           "A2": urteil(p, se_p, C.PAARE_MAX, "<=") if p is not None else "n/a",
           "A3": urteil(d1 - r_mittel, se1, C.ABSTAND_PAARE, ">=") if (d1 is not None and r_mittel is not None) else "n/a",
           "A4": (urteil(d2 - d1, math.sqrt(se1 ** 2 + se2 ** 2), C.D2_ABSTAND, ">=") if (d1 is not None and d2 is not None) else "n/a")}
    if d1 is None or r_mittel is None:
        out["A5"] = "n/a"
    else:
        out["A5"] = "gilt" if r_mittel > d1 else "gilt nicht"
    return out


def aussagen_zelle(c):
    return aussagen(ring(c), se(c, "D1") or 0.0, ring2(c), se(c, "D2") or 0.0, anteil(c, "P"), se(c, "P") or 0.0, zufall_mittel(c, "R"))


def basiszelle_zeilen():
    """Zellen der Messreihe ohne die Teil-Zellen (diese teilen sich die Szenarien mit je einer anderen Zelle)."""
    return {k: c for k, c in cells().items() if not k.endswith("teil=True")}


def gruppe_der_zelle(c):
    m = c["meta"]
    if m["g"] < 1:
        return "Wirkungsgrad 0,8"
    if m["imb"]:
        return "Ungleichgewicht"
    if m["disp"]:
        return "überstreut k = %d%s" % (m["disp"], ", gemeinsame Schwankung" if m["korr"] else "")
    return "Poisson, mu = %d" % m["mu"]


GRUPPEN_REIHENFOLGE = ("Poisson, mu = 5", "Poisson, mu = 20", "Poisson, mu = 50", "überstreut k = 10", "überstreut k = 10, gemeinsame Schwankung",
                       "überstreut k = 4", "überstreut k = 4, gemeinsame Schwankung", "Ungleichgewicht", "Wirkungsgrad 0,8")


@lru_cache(maxsize=1)
def aussagen_messreihe():
    """Zählung der Aussagen über alle 138 Messpunkte: {"A1": {"gilt": 86, ...}, ...}, dazu Gruppentabelle (Zellen, Ring unter 95 %)."""
    counts = {a: {} for a in AUSSAGEN}
    gruppen = {}
    ring_n = []
    for k, c in basiszelle_zeilen().items():
        urt = aussagen_zelle(c)
        for a, u in urt.items():
            counts[a][u] = counts[a].get(u, 0) + 1
        g = gruppen.setdefault(gruppe_der_zelle(c), [0, 0])
        g[0] += 1
        g[1] += 1 if urt["A1"] != "gilt" else 0
        ring_n.append((k, ring(c)))
    return {"zaehlung": counts, "gruppen": gruppen, "zellen": len(basiszelle_zeilen())}


# --- Abdeckung ------------------------------------------------------------------------------------------------------------------------

def abdeckung_schluessel(n, mu, r, dist, struct, eff):
    return "n=%s|mu=%s|r=%s|dist=%s|struct=%s|eff=%s" % (n, mu, r, dist, struct, eff)


def abdeckung_zeile(s):
    cov = load_coverage()
    if cov is None:
        return None
    return cov["rows"].get(abdeckung_schluessel(s.n, s.mu, s.r, s.dist, s.struct, s.eff))


def abdeckung_ring(rec):
    e = rec["entwuerfe"].get("D1")
    return 100.0 if e is None else None if e["anteil"] is None else 100.0 * e["anteil"]


def abdeckung_aussagen(rec, n):
    """A1 bis A5 einer Zeile der Abdeckung (die Zeile hält Anteile als Bruchteile). Bei n <= 3 ist D2 gleich F (100 %), bei n = 2 D1 gleich F."""
    def pct(x):
        return None if x is None else 100.0 * x

    ents = rec["entwuerfe"]
    d1 = ents.get("D1")
    d1p = pct(d1["anteil"]) if d1 else (100.0 if n <= 2 else None)
    se1 = pct(d1["se"]) if d1 and d1["se"] is not None else 0.0
    d2 = ents.get("D2")
    d2p = pct(d2["anteil"]) if d2 else (100.0 if n <= 3 else None)
    se2 = pct(d2["se"]) if d2 and d2["se"] is not None else 0.0
    p = ents.get("P")
    pp = pct(p["anteil"]) if p else None
    sep = pct(p["se"]) if p and p["se"] is not None else 0.0
    rm = pct(rec["R"]["mittel"]) if "R" in rec else None
    return aussagen(d1p, se1, d2p, se2, pp, sep, rm)


def abdeckung_zusammenfassung():
    """Zählung der Aussagen A1 bis A4 über alle Kombinationen der Abdeckung, getrennt nach Messpunkt und Nicht-Messpunkt."""
    cov = load_coverage()
    if cov is None:
        return None
    out = {"alle": {a: {} for a in AUSSAGEN}, "gemessen": {a: {} for a in AUSSAGEN}, "ungemessen": {a: {} for a in AUSSAGEN},
           "kombinationen": len(cov["rows"])}
    mp = messpunkte()
    for key, rec in cov["rows"].items():
        parts = dict(p.split("=", 1) for p in key.split("|"))
        kombi = (int(parts["n"]), int(parts["mu"]), float(parts["r"]), parts["dist"], parts["struct"], float(parts["eff"]))
        urt = abdeckung_aussagen(rec, kombi[0])
        for grp in ("alle", "gemessen" if kombi in mp else "ungemessen"):
            for a, u in urt.items():
                out[grp][a][u] = out[grp][a].get(u, 0) + 1
    return out
