"""Bedienung nach der Realisierung des Bedarfs: größter Fluss Quelle -> Gruppen (S_j) -> Stationen in Q_j -> Senke (D_i).

Max-Fluss-Min-Schnitt: bedient(D) = min über Teilmengen T der Stationen von  sum_{i nicht in T} D_i + sum_{j: Q_j schneidet T} S_j.
Gruppierter Min-Schnitt (exakt): Der Graph zerfällt in Komponenten, die sich addieren; je Komponente genügen die ABGESCHLOSSENEN
Teilmengen T (T enthält jede Station, deren Anbieter alle zu den Gruppen gehören, die T berühren), weil bei gleicher Gruppenmenge das
größte T den kleinsten Wert liefert. Statt 2^n Teilmengen sind es je Entwurf einige Dutzend bis wenige Hundert Zeilen.

Teilqualifikation (Anteil q jeder Gruppe lernt die Zusatzstationen): Eigenkapazität (1-q)*S zuerst auf die eigene Station, dann derselbe
Graph mit Kapazität q*S und Bedarf (D - (1-q)*S)^+. Exakt, weil die nur-eigene Kapazität nie schadet.

Wirkungsgrad g < 1 (Gruppe j auf Station i != j liefert g je Einheit Kapazität): verallgemeinerter Fluss als LP je Szenario (alle
Szenarien als ein blockdiagonales LP); F in geschlossener Form: eigene Station zuerst, dann min(g * freie Kapazität, offener Bedarf)."""

from functools import lru_cache

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog
from scipy.sparse.csgraph import maximum_flow

from kzs_designs import stationen_in


# --- Struktur: Komponenten und abgeschlossene Teilmengen -----------------------------------------------------------------------------

def komponenten(q, n):
    """Zusammenhangskomponenten des bipartiten Graphen (Stationen i, Gruppen j mit i in Q_j) als Liste von Stationsmasken."""
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for m in q:
        st_ = stationen_in(m, n)
        for a in st_[1:]:
            ra, rb = find(st_[0]), find(a)
            if ra != rb:
                parent[ra] = rb
    comp = {}
    for i in range(n):
        comp.setdefault(find(i), 0)
        comp[find(i)] |= 1 << i
    return list(comp.values())


@lru_cache(maxsize=8192)
def struktur(q, n):
    """Je Komponente: (Stationen, notin (Zeilen, m) 0/1, Gruppen, hit (Zeilen, Gruppen) 0/1) für alle abgeschlossenen Teilmengen.
    notin[z, a] = 1, wenn Station a der Komponente nicht in T_z liegt; hit[z, b] = 1, wenn Gruppe b die Menge T_z berührt."""
    qarr = np.array(q, dtype=np.int64)
    out = []
    for cm in komponenten(q, n):
        sts = stationen_in(cm, n)
        m = len(sts)
        gr = [j for j in range(len(q)) if q[j] & cm]
        serv = []   # Anbieter je Station als Bitmaske über die lokale Gruppenliste
        for i in sts:
            s = 0
            for a, j in enumerate(gr):
                if (q[j] >> i) & 1:
                    s |= 1 << a
            serv.append(s)
        t = np.arange(1 << m, dtype=np.int64)
        G = np.zeros(1 << m, dtype=np.int64)
        for a in range(m):
            G |= np.where((t >> a) & 1, serv[a], 0)
        Tp = np.zeros(1 << m, dtype=np.int64)
        for a in range(m):
            Tp |= ((serv[a] & ~G) == 0).astype(np.int64) << a
        tt = t[Tp == t]                                  # abgeschlossene Teilmengen (lokale Stationsindizes als Bitmaske)
        notin = (1.0 - ((tt[:, None] >> np.arange(m)[None, :]) & 1)).astype(np.float64)
        tg = np.zeros(len(tt), dtype=np.int64)           # dieselben Mengen als globale Stationsmasken
        for a, i in enumerate(sts):
            tg |= ((tt >> a) & 1) << i
        hit = ((tg[:, None] & qarr[None, gr]) != 0).astype(np.float64)
        out.append((sts, notin, gr, hit))
    return tuple(out)


def zeilen(q, n):
    """Zahl der ausgewerteten Zeilen (abgeschlossene Teilmengen über alle Komponenten)."""
    return sum(len(c[1]) for c in struktur(tuple(q), n))


def bedient_gruppiert(D, S, q):
    """Bedienter Bedarf je Szenario. D (N, n), S (n,) Kapazität je Gruppe, q Entwurf (Tupel von Masken)."""
    n = D.shape[1]
    S = np.asarray(S, dtype=np.float64)
    tot = np.zeros(D.shape[0])
    for sts, notin, gr, hit in struktur(tuple(q), n):
        cap = hit @ S[gr]
        tot += (D[:, sts] @ notin.T + cap[None, :]).min(axis=1)
    return tot


def bedient_aufzaehlung(D, S, q):
    """Referenz: Min-Schnitt als volle Aufzählung aller 2^n Teilmengen (ohne Gruppierung)."""
    N, n = D.shape
    t = np.arange(1 << n, dtype=np.int64)
    notin = (1.0 - ((t[:, None] >> np.arange(n)[None, :]) & 1)).astype(np.float64)
    cap = np.zeros(len(t))
    for j in range(len(q)):
        cap += S[j] * ((t & q[j]) != 0)
    return (D @ notin.T + cap[None, :]).min(axis=1)


def kritische_menge(Dzeile, S, q):
    """Min-Schnitt eines einzelnen Szenarios: (Wert, T als Liste der Stationen, Gruppen, die T berühren)."""
    n = len(Dzeile)
    S = np.asarray(S, dtype=np.float64)
    wert = 0.0
    T, gruppen = [], []
    for sts, notin, gr, hit in struktur(tuple(q), n):
        cap = hit @ S[gr]
        v = notin @ np.asarray(Dzeile, dtype=np.float64)[sts] + cap
        z = int(np.argmin(v))
        wert += float(v[z])
        T += [sts[a] for a in range(len(sts)) if notin[z, a] == 0.0]
        gruppen += [gr[b] for b in range(len(gr)) if hit[z, b] == 1.0]
    return wert, sorted(T), sorted(gruppen)


# --- Teilqualifikation, Wirkungsgrad -------------------------------------------------------------------------------------------------

def f_geschlossen(D, S, g):
    """Volle Flexibilität bei Wirkungsgrad g: eigene Station zuerst, dann min(g * freie Kapazität, offener Bedarf). S Vektor oder Zahl."""
    S = np.broadcast_to(np.asarray(S, dtype=np.float64), (D.shape[1],))
    eigen = np.minimum(D, S[None, :]).sum(1)
    frei = np.maximum(S[None, :] - D, 0.0).sum(1)
    offen = np.maximum(D - S[None, :], 0.0).sum(1)
    return eigen + np.minimum(g * frei, offen)


def batch_lp(D, S, q, g):
    """Bedienter Bedarf je Szenario bei Wirkungsgrad g: verallgemeinerter Fluss als LP (HiGHS), alle Szenarien blockdiagonal in einem LP.
    x_ji >= 0 Kapazität der Gruppe j auf Station i; sum_i x_ji <= S_j; sum_j gewinn_ji x_ji <= D_i; max sum gewinn_ji x_ji;
    gewinn_jj = 1, gewinn_ji = g für i != j."""
    N, n = D.shape
    S = np.broadcast_to(np.asarray(S, dtype=np.float64), (len(q),))
    bogen = [(j, i) for j in range(len(q)) for i in stationen_in(q[j], n)]
    m = len(bogen)
    gew = np.array([1.0 if j == i else g for (j, i) in bogen])
    ng = len(q)
    rows, cols, vals = [], [], []
    for a, (j, i) in enumerate(bogen):
        rows += [j, ng + i]
        cols += [a, a]
        vals += [1.0, gew[a]]
    A1 = sp.csr_matrix((vals, (rows, cols)), shape=(ng + n, m))
    A = sp.block_diag([A1] * N, format="csr")
    b = np.concatenate([np.tile(S, (N, 1)), D], axis=1).reshape(-1)
    c = np.tile(-gew, N)
    res = linprog(c, A_ub=A, b_ub=b, bounds=(0, None), method="highs")
    x = res.x.reshape(N, m)
    return (x * gew[None, :]).sum(axis=1)


def bedient(D, S1, q, anteil=1.0, g=1.0):
    """Bedienter Bedarf je Szenario für den Entwurf q bei Kapazität S1 je Gruppe, Anteil geschult `anteil` und Wirkungsgrad g.
    Der Anteil gilt für die Zusatzstationen; die eigene Station können alle (die ungeschulten Personen nur diese)."""
    n = D.shape[1]
    if anteil < 1.0:
        u = (1.0 - anteil) * S1
        basis = np.minimum(D, u).sum(1)
        D2 = np.maximum(D - u, 0.0)
        S2 = anteil * S1
    else:
        basis, D2, S2 = 0.0, D, S1
    S2v = np.full(n, S2)
    if g >= 1.0:
        return basis + bedient_gruppiert(D2, S2v, q)
    return basis + batch_lp(D2, S2v, q, g)


def bezug(D, S1, g):
    """Die beiden Bezugspunkte je Szenario: D0 (jede Gruppe nur ihre Station) und F (voll)."""
    n = D.shape[1]
    d0 = np.minimum(D, S1).sum(1)
    if g >= 1.0:
        f = bedient_gruppiert(D, np.full(n, S1), tuple((1 << n) - 1 for _ in range(n)))
    else:
        f = f_geschlossen(D, S1, g)
    return d0, f


# --- Ein Tag: Max-Fluss mit Bogenflüssen (Beispieltag) --------------------------------------------------------------------------------

SKALA_FLUSS = 1000   # Kapazitäten mit diesem Faktor ganzzahlig (S = 4,5; Anteil 5 % ergibt 0,225)


def tagesfluss(Dzeile, S1, q, anteil=1.0, g=1.0):
    """Ein Szenario, ein Fluss. Rückgabe: Wert (bedienter Bedarf), Bogenfluss als Matrix (Gruppe j, Station i; Diagonale = eigene
    Station inklusive der ungeschulten Kapazität), bedient je Station. Bei g = 1 Max-Fluss (scipy, ganzzahlig mit Faktor 1000),
    sonst das LP des verallgemeinerten Flusses (Bogenfluss in Kapazitätseinheiten der Gruppe, bedient = gewinn * Fluss)."""
    n = len(Dzeile)
    D = np.asarray(Dzeile, dtype=np.float64)
    if anteil < 1.0:
        u = (1.0 - anteil) * S1
        eigen = np.minimum(D, u)
        D2 = np.maximum(D - u, 0.0)
        S2 = anteil * S1
    else:
        eigen = np.zeros(n)
        D2 = D
        S2 = S1
    fluss = np.zeros((n, n))
    served = np.zeros(n)
    if g >= 1.0:
        sc = SKALA_FLUSS
        gross = int(round((S2 * n + D2.sum()) * sc)) + 1
        V = 2 * n + 2
        s, t = 0, 2 * n + 1
        A = np.zeros((V, V), dtype=np.int32)
        for j in range(n):
            A[s, 1 + j] = int(round(S2 * sc))
            for i in stationen_in(q[j], n):
                A[1 + j, 1 + n + i] = gross
            A[1 + n + j, t] = int(round(D2[j] * sc))
        res = maximum_flow(sp.csr_matrix(A), s, t)
        F = res.flow.toarray() if hasattr(res.flow, "toarray") else np.asarray(res.flow)
        for j in range(n):
            for i in stationen_in(q[j], n):
                fluss[j, i] = max(F[1 + j, 1 + n + i], 0) / sc
        served = fluss.sum(axis=0)
    else:
        bogen = [(j, i) for j in range(n) for i in stationen_in(q[j], n)]
        gew = np.array([1.0 if j == i else g for (j, i) in bogen])
        A = np.zeros((2 * n, len(bogen)))
        for a, (j, i) in enumerate(bogen):
            A[j, a] = 1.0
            A[n + i, a] = gew[a]
        b = np.concatenate([np.full(n, S2), D2])
        res = linprog(-gew, A_ub=A, b_ub=b, bounds=(0, None), method="highs")
        for a, (j, i) in enumerate(bogen):
            fluss[j, i] = res.x[a]
            served[i] += gew[a] * res.x[a]
    # eigene Station: ungeschulte Kapazität und eigener Fluss zusammen
    fluss_gesamt = fluss.copy()
    for j in range(n):
        fluss_gesamt[j, j] += eigen[j]
    served = served + eigen
    return float(served.sum()), fluss_gesamt, served
