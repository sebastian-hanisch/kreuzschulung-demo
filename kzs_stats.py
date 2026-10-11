"""Kennzahlen je Entwurf auf gepaarten Szenarien: Servicegrad, Unterdeckung, Anteil am vollen Flexibilitätsnutzen mit Standardfehler.

Anteil(E) = (SG(E) - SG(D0)) / (SG(F) - SG(D0)) = mean(x - d0) / mean(f - d0). Der Standardfehler folgt der Delta-Methode auf den
Szenario-Paaren: r = mean(a) / mean(b) mit a = x - d0, b = f - d0, SE = sqrt(var(a - r*b) / N) / |mean(b)|."""

import math

import numpy as np

MB_MIN = 1e-12   # darunter ist F gleich D0 und der Anteil nicht definiert


def stat_anteil(x, d0, f):
    """(Anteil, Standardfehler, mittlerer Gewinn von F gegenüber D0). Ist der Gewinn von F null, sind Anteil und Standardfehler None."""
    a = x - d0
    b = f - d0
    mb = float(b.mean())
    if abs(mb) < MB_MIN:
        return None, None, 0.0
    ratio = float(a.mean()) / mb
    resid = a - ratio * b
    se = math.sqrt(float(resid.var(ddof=1)) / len(a)) / abs(mb)
    return ratio, se, mb


def kennzahlen(served, D, d0, f):
    """Kennzahlen eines Entwurfs: Servicegrad (Verhältnis der Erwartungen), Unterdeckung (Personentage je Tag), Anteil, Standardfehler."""
    unmet = D.sum(1) - served
    total = float(D.sum(1).mean())
    anteil, se, _ = stat_anteil(served, d0, f)
    return {"sg": float(1.0 - unmet.mean() / total), "unterdeckung": float(unmet.mean()), "anteil": anteil, "se": se}


def streuung(anteile):
    """Mittel, Standardabweichung (n - 1), Minimum und Maximum der Anteile mehrerer Ziehungen; None-Werte zählen nicht."""
    a = np.array([x for x in anteile if x is not None], dtype=float)
    if len(a) == 0:
        return {"mittel": None, "sd": None, "min": None, "max": None, "ziehungen": 0}
    return {"mittel": float(a.mean()), "sd": float(a.std(ddof=1)) if len(a) > 1 else 0.0, "min": float(a.min()), "max": float(a.max()),
            "ziehungen": int(len(a))}
