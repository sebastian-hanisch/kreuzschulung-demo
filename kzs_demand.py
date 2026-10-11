"""Bedarfsszenarien: Poisson per Inversion, Gamma-Poisson (überstreut) mit optionaler gemeinsamer Schwankung, Struktur des mittleren Bedarfs.

Alles aus dem eigenen ganzzahligen Generator (kzs_rng). Die Schlüssel der Bedarfsströme enthalten weder die Kapazität r noch den
Wirkungsgrad noch den Entwurf: alle Entwürfe einer Einstellung werden auf denselben Szenarien bewertet (gepaarte Szenarien).
Der Schlüsseltext STREAM_KEY ist derselbe wie in der Vorab-Messreihe; nur so sind die Live-Zahlen dort nachschlagbar."""

import numpy as np

from kzs_rng import seed_aus, uniformen

STREAM_KEY = "sw"
_POISSON_SCHUTZ = 5000   # Schutz gegen Rundungsstau der Verteilungsfunktion bei u sehr nahe 1


def poisson_inversion(u, rate):
    """Poisson-Ziehung per Inversion (Suche entlang der Verteilungsfunktion), elementweise; u in (0, 1), rate >= 0."""
    rate = np.broadcast_to(rate, u.shape).astype(np.float64)
    p = np.exp(-rate)
    cdf = p.copy()
    d = np.zeros(u.shape, dtype=np.float64)
    maske = u > cdf
    k = 0
    while maske.any():
        d += maske
        k += 1
        p = p * rate / k
        cdf = cdf + p
        maske &= (u > cdf)
        if k > _POISSON_SCHUTZ:
            break
    return d


def gamma_erlang(u, k0):
    """Gamma(Form k0, Mittel 1) für ganzzahliges k0 als Summe von k0 Exponentialen; u hat die Form (N, k0)."""
    return (-np.log(u)).sum(axis=1) / k0


def bedarf(n, mu, disp=None, korr=0.0, N=20000, block=0, schluessel=STREAM_KEY, skala=None):
    """Bedarfsmatrix (N, n), ganzzahlig.

    disp None: reines Poisson mit Mittel mu.  disp = k: Gamma-gemischtes Poisson, Rate mu * G mit G ~ Gamma(Form k, Mittel 1),
    Varianz mu + mu^2 / k.  skala: Mittel je Station = mu * skala_i.  korr = 0,5: G_i = 0,5 * E_i + 0,5 * C mit unabhängigen
    Gamma(Form k/2, Mittel 1); die Randverteilung behält Mittel und Varianz, die Korrelation der Raten ist 0,5."""
    mittel = mu * (np.ones(n) if skala is None else np.asarray(skala, float))
    if disp is None:
        if korr:
            raise ValueError("Korrelation ohne überstreute Rate ist nicht definiert")
        u = uniformen(seed_aus(schluessel, n, mu, "p", block), N * n).reshape(N, n)
        return poisson_inversion(u, mittel[None, :])
    if korr:
        k0 = disp // 2
        if 2 * k0 != disp:
            raise ValueError("gemeinsame Schwankung braucht eine geradzahlige Form")
        g = np.empty((N, n))
        c = gamma_erlang(uniformen(seed_aus(schluessel, n, mu, disp, "c", block), N * k0).reshape(N, k0), k0)
        for i in range(n):
            e = gamma_erlang(uniformen(seed_aus(schluessel, n, mu, disp, "e", i, block), N * k0).reshape(N, k0), k0)
            g[:, i] = (1.0 - korr) * e + korr * c
    else:
        g = np.empty((N, n))
        for i in range(n):
            g[:, i] = gamma_erlang(uniformen(seed_aus(schluessel, n, mu, disp, "g", i, block), N * disp).reshape(N, disp), disp)
    u = uniformen(seed_aus(schluessel, n, mu, disp, bool(korr), "p", block), N * n).reshape(N, n)
    return poisson_inversion(u, mittel[None, :] * g)


def skala_aus(n, imb):
    """Mittlerer Bedarf je Station als Vielfaches von mu. imb None: alle 1. ("block", delta): erste Hälfte heiß (1 + delta), zweite
    Hälfte kalt (1 - delta). ("alt", delta): gerade Stationen heiß, ungerade kalt. Bei ungeradem n bleibt eine Station neutral (1),
    damit der Gesamtbedarf gleich bleibt (Block: die mittlere, abwechselnd: die letzte)."""
    if imb is None:
        return [1.0] * n
    art, delta = imb
    if art == "block":
        return [1.0 + delta if i < n // 2 else (1.0 - delta if i >= n - n // 2 else 1.0) for i in range(n)]
    s = [1.0 + delta if i % 2 == 0 else 1.0 - delta for i in range(n)]
    if n % 2 == 1:
        s[n - 1] = 1.0
    return s
