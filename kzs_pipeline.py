"""Rechenpfad einer Einstellung in drei Stufen (ohne Streamlit): Stufe 1 sofort (Bezugspunkte, alle festen Entwürfe, Eigener Entwurf),
Stufe 2 (Streuung der Zufallsentwürfe), Stufe 3 (Kurve der Teilqualifikation). Alle Stufen rechnen auf denselben gepaarten Szenarien.

Einstellungen sind eine Dataclass nur mit Schlüsselwörtern (ein eingefügtes Feld verschob schon einmal still Werte)."""

import itertools
import time
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

import kzs_constants as C
import kzs_designs as DS
import kzs_flow as FL
import kzs_stats as ST
from kzs_demand import STREAM_KEY, bedarf, skala_aus


@dataclass(frozen=True, kw_only=True)
class Settings:
    n: int = C.DEFAULT_N
    mu: int = C.DEFAULT_MU
    r: float = C.DEFAULT_R
    dist: str = C.DEFAULT_DIST
    struct: str = C.DEFAULT_STRUCT
    eff: float = C.DEFAULT_EFF
    q: float = C.DEFAULT_Q
    seed: int = C.DEFAULT_SEED
    own: tuple = ()          # Auswahl je Gruppe: Tupel von n Tupeln mit Zusatzstationen; () = noch kein Eigener Entwurf

    @property
    def disp(self):
        return C.DIST_PARAMS[self.dist][0]

    @property
    def korr(self):
        return C.DIST_PARAMS[self.dist][1]

    @property
    def imb(self):
        return C.STRUCT_PARAMS[self.struct]

    @property
    def g(self):
        return self.eff

    @property
    def N(self):
        return C.N_SZENARIEN if self.eff >= 1.0 else C.N_SZENARIEN_LP

    @property
    def S1(self):
        return self.r * self.mu

    @property
    def skala(self):
        return skala_aus(self.n, self.imb)

    @property
    def own_masks(self):
        """Maskentupel des Eigenen Entwurfs oder None, solange keine Zusatzqualifikation gewählt ist."""
        if len(self.own) != self.n or not any(len(a) for a in self.own):
            return None
        return DS.eigener_entwurf(self.n, self.own)

    @property
    def n_ziehungen(self):
        if self.eff < 1.0:
            return C.N_ZIEHUNGEN_LP
        return C.N_ZIEHUNGEN_KLEIN if self.n <= 8 else C.N_ZIEHUNGEN_GROSS


def zellen_schluessel(n, mu, disp, korr, r, g, imb, teil):
    """Schlüssel einer Zelle der Vorab-Messreihe (dieselbe Schreibweise wie in data/kzs_results.json)."""
    return "n=%s|mu=%s|disp=%s|korr=%s|r=%s|g=%s|imb=%s|teil=%s" % (n, mu, disp, korr, r, g, imb, teil)


def mess_schluessel(s, teil=False):
    return zellen_schluessel(s.n, s.mu, s.disp, s.korr, s.r, s.g, s.imb, teil)


def kombination(s):
    """Die sechs Regler der Rechnung ohne Anteil geschult, Zufalls-Seed und Eigenen Entwurf (die 2.700 Kombinationen der Abdeckung)."""
    return (s.n, s.mu, s.r, s.dist, s.struct, s.eff)


def szenarien(s, N=None, block=0):
    return bedarf(s.n, s.mu, s.disp, s.korr, N=N or s.N, block=block, schluessel=STREAM_KEY, skala=s.skala)


def _bezug(s):
    D = szenarien(s)
    d0, f = FL.bezug(D, s.S1, s.g)
    return D, d0, f


def _anteil_eines(D, d0, f, s, q):
    return ST.kennzahlen(FL.bedient(D, s.S1, q, s.q, s.g), D, d0, f)


# --- Stufe 1 ------------------------------------------------------------------------------------------------------------------------

def stufe1(s):
    """Bezugspunkte und alle festen Entwürfe plus Eigener Entwurf. Rückgabe: {"designs": {Name: Kennzahlen mit bogen und Masken}, ...}."""
    t0 = time.perf_counter()
    D, d0, f = _bezug(s)
    satz = DS.entwurfssatz(s.n, s.seed, s.own_masks)
    out = {}
    for name, q in satz.items():
        if name == "D0":
            kz = ST.kennzahlen(d0, D, d0, f)
        elif name == "F":
            kz = ST.kennzahlen(f, D, d0, f)
        else:
            kz = _anteil_eines(D, d0, f, s, q)
        kz.update({"bogen": DS.zahl_bogen(q), "masken": q, "zeilen": FL.zeilen(q, s.n) if s.g >= 1.0 else None})
        out[name] = kz
    d0k, fk = out["D0"], out["F"]
    return {"designs": out, "bedarf_mittel": float(D.sum(1).mean()), "kapazitaet": float(s.n * s.S1), "N": int(D.shape[0]),
            "gewinn_punkte": 100.0 * (fk["sg"] - d0k["sg"]), "gewinn_pt": d0k["unterdeckung"] - fk["unterdeckung"],
            "sekunden": time.perf_counter() - t0}


# --- Stufe 2 ------------------------------------------------------------------------------------------------------------------------

def stufe2(s):
    """Streuung der Zufallsentwürfe R und R1 über die Ziehungen 0 bis n_ziehungen - 1 (die der Messreihe)."""
    t0 = time.perf_counter()
    out = {}
    if s.n >= 3:
        D, d0, f = _bezug(s)
        for fam in ("R", "R1"):
            anteile = []
            for dr in range(s.n_ziehungen):
                q = DS.zufall_ziehung(s.n, fam, dr)
                anteile.append(_anteil_eines(D, d0, f, s, q)["anteil"])
            res = ST.streuung(anteile)
            res["anteile"] = anteile
            out[fam] = res
    out["sekunden"] = time.perf_counter() - t0
    return out


# --- Stufe 3 ------------------------------------------------------------------------------------------------------------------------

def teil_kurve(s, masken):
    """Anteil und Standardfehler für jeden Anteil geschult der Rasters Q_OPTIONS (Entwurf `masken`)."""
    D, d0, f = _bezug(s)
    out = []
    for q in C.Q_OPTIONS:
        kz = ST.kennzahlen(FL.bedient(D, s.S1, masken, q, s.g), D, d0, f)
        out.append((kz["anteil"], kz["se"]))
    return out


def stufe3(s):
    """Kurven der Teilqualifikation: Ring (D1), Paare (falls es sie gibt) und der Eigene Entwurf (falls gebaut)."""
    t0 = time.perf_counter()
    D, d0, f = _bezug(s)
    ents = {"D1": DS.ring(s.n, 1)}
    if s.n % 2 == 0 and s.n >= 4:
        ents["P"] = DS.ketten(s.n, 2)
    if s.own_masks is not None:
        ents["E"] = s.own_masks
    out = {}
    for name, masken in ents.items():
        pts = []
        for q in C.Q_OPTIONS:
            kz = ST.kennzahlen(FL.bedient(D, s.S1, masken, q, s.g), D, d0, f)
            pts.append((kz["anteil"], kz["se"]))
        out[name] = pts
    out["sekunden"] = time.perf_counter() - t0
    return out


def q_fuer_ziel(anteile, ziel):
    """Kleinster geschulter Anteil (lineare Interpolation auf dem Raster, vom Ursprung aus), bei dem `ziel` (0 bis 1) erreicht wird;
    None, wenn es auch bei q = 1 nicht erreicht wird. `anteile`: Werte zu C.Q_OPTIONS."""
    pts = [(0.0, 0.0)] + [(q, a) for q, a in zip(C.Q_OPTIONS, anteile) if a is not None]
    for (q0, a0), (q1, a1) in zip(pts, pts[1:]):
        if a0 < ziel <= a1 + 1e-12:
            return q0 + (q1 - q0) * (ziel - a0) / (a1 - a0) if a1 > a0 else q1
    return None


# --- Bester Entwurf (Aufzählung bis auf Umbenennung), nur n = 4 live ------------------------------------------------------------------

@lru_cache(maxsize=4)
def klassen(n, k):
    """Alle Mengen aus k Zusatzbögen bis auf Umbenennung der Stationen (bei austauschbarem Bedarf ist jede Umbenennung eine Symmetrie).
    Rückgabe: Tupel (Bogenliste, Vielfachheit); Vertreter = kleinste Bitmaske über alle n! Umbenennungen."""
    bogen = [(j, i) for j in range(n) for i in range(n) if i != j]
    idx = {b: a for a, b in enumerate(bogen)}
    kombi = np.array(list(itertools.combinations(range(len(bogen)), k)), dtype=np.int64)
    masken = (np.int64(1) << kombi).sum(axis=1)
    kanon = masken.copy()
    for perm in itertools.permutations(range(n)):
        pa = np.array([idx[(perm[j], perm[i])] for (j, i) in bogen], dtype=np.int64)
        kanon = np.minimum(kanon, (np.int64(1) << pa[kombi]).sum(axis=1))
    werte, anz = np.unique(kanon, return_counts=True)
    return tuple((tuple(bogen[b] for b in range(len(bogen)) if (int(w) >> b) & 1), int(a)) for w, a in zip(werte, anz))


def kanonisch(n, bogen):
    best = None
    for perm in itertools.permutations(range(n)):
        m = tuple(sorted((perm[j], perm[i]) for (j, i) in bogen))
        best = m if best is None or m < best else best
    return best


def bester_entwurf(s):
    """O bei n = 4 (austauschbarer Bedarf, Wirkungsgrad 100 %): Auswahl auf den eigenen Szenarien (Block 1000), Bewertung auf den
    Szenarien der Einstellung (Block 0). Rückgabe: Kennzahlen mit Bögen, Anzahl Klassen und ob der Gewählte der Ring ist."""
    if s.n != 4 or s.imb is not None or s.g < 1.0:
        return None
    n = s.n
    D, d0, f = _bezug(s)
    Dsel = szenarien(s, N=C.N_AUSWAHL, block=C.AUSWAHL_BLOCK)
    kl = klassen(n, n)
    best_w, best_k = -1.0, 0
    for a, (bogen, _) in enumerate(kl):
        w = FL.bedient(Dsel, s.S1, DS.aus_bogen(n, bogen), s.q, 1.0).mean()
        if w > best_w + 1e-12:
            best_w, best_k = float(w), a
    bogen = kl[best_k][0]
    q = DS.aus_bogen(n, bogen)
    kz = _anteil_eines(D, d0, f, s, q)
    ring_kan = kanonisch(n, [(j, i) for j in range(n) for i in range(n) if i != j and (DS.ring(n, 1)[j] >> i) & 1])
    kz.update({"bogen": DS.zahl_bogen(q), "masken": q, "klassen": len(kl), "ist_ring": kanonisch(n, bogen) == ring_kan})
    return kz


# --- Beispieltag --------------------------------------------------------------------------------------------------------------------

def beispieltag(s, masken, tag):
    """Ein Szenario (Nummer `tag`, modulo der Szenarienzahl): Bedarf je Station, Bogenfluss, bedient je Station, Min-Schnitt gegen
    Max-Fluss. Rückgabe-Wörterbuch."""
    D = szenarien(s)
    d = int(tag) % D.shape[0]
    Dz = D[d]
    wert, fluss, served = FL.tagesfluss(Dz, s.S1, masken, s.q, s.g)
    erg = {"tag": d, "N": int(D.shape[0]), "bedarf": Dz.copy(), "kapazitaet": np.full(s.n, s.S1), "fluss": fluss, "bedient": served,
           "unterdeckung": Dz - served, "wert": wert, "bedarf_summe": float(Dz.sum())}
    if s.g >= 1.0:
        u = (1.0 - s.q) * s.S1
        D2 = np.maximum(Dz - u, 0.0) if s.q < 1.0 else Dz
        basis = float(np.minimum(Dz, u).sum()) if s.q < 1.0 else 0.0
        cut, T, grp = FL.kritische_menge(D2, np.full(s.n, s.q * s.S1), masken)
        erg.update({"schnitt": basis + cut, "T": T, "gruppen": grp, "schnitt_basis": basis})
    else:
        erg.update({"schnitt": None, "T": None, "gruppen": None, "schnitt_basis": 0.0})
    return erg


# --- Kompakter Satz für die Abdeckung (alle Stufen, ohne Eigenen Entwurf) -------------------------------------------------------------

def abdeckung_satz(s):
    """Kennzahlen einer Kombination für data/kzs_coverage.json: Anteile der festen Entwürfe, R und R1 (Mittel und Streuung über die
    Ziehungen der Messreihe), Gewinn von F, Kurven der Teilqualifikation von Ring und Paaren. Eigener Entwurf und Zufalls-Seed spielen keine Rolle."""
    s = Settings(n=s.n, mu=s.mu, r=s.r, dist=s.dist, struct=s.struct, eff=s.eff, q=1.0, seed=0)
    s1 = stufe1(s)
    s2 = stufe2(s)
    s3 = stufe3(s)
    rec = {"gewinn_punkte": s1["gewinn_punkte"], "gewinn_pt": s1["gewinn_pt"], "entwuerfe": {}}
    for name, kz in s1["designs"].items():
        if name in ("D0", "F", "R", "R1"):
            continue
        rec["entwuerfe"][name] = {"anteil": kz["anteil"], "se": kz["se"], "bogen": kz["bogen"], "sg": kz["sg"]}
    rec["sg_d0"] = s1["designs"]["D0"]["sg"]
    rec["sg_f"] = s1["designs"]["F"]["sg"]
    for fam in ("R", "R1"):
        if fam in s2:
            rec[fam] = {k: s2[fam][k] for k in ("mittel", "sd", "min", "max", "ziehungen")}
    rec["teil"] = {name: [a for a, _ in pts] for name, pts in s3.items() if name != "sekunden"}
    rec["teil_se"] = {name: [e for _, e in pts] for name, pts in s3.items() if name != "sekunden"}
    return rec
