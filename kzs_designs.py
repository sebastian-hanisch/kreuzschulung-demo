"""Qualifikationsgraphen (Entwürfe) als Bitmasken: Gruppe j kann die Stationen in Maske q[j] (immer inklusive der eigenen Station j).

Ein Bogen (j, i) heißt: alle Personen der Gruppe j sind zusätzlich für die Station i qualifiziert. „Zusatzqualifikationen“ werden als
Bögen gezählt. Entwürfe sind Tupel von n Masken; sie sind hashbar und dienen als Schlüssel der Struktur- und Ergebnis-Caches."""

from kzs_rng import SplitMix64, seed_aus


def bits(*stationen):
    m = 0
    for s in stationen:
        m |= 1 << s
    return m


def stationen_in(maske, n):
    """Indizes der gesetzten Bits unterhalb von n."""
    return [i for i in range(n) if (maske >> i) & 1]


def zahl_bogen(q):
    """Zahl der Zusatzqualifikationen (Bögen j -> i, i != j)."""
    return sum(bin(m).count("1") - 1 for m in q)


def ring(n, k):
    """Ring mit k Zusatzstationen je Gruppe: Gruppe j kann j, j+1, ..., j+k (mod n). k = 0 ist D0, k = n-1 ist F."""
    k = min(k, n - 1)
    return tuple(bits(*[(j + t) % n for t in range(k + 1)]) for j in range(n))


def ketten(n, laenge):
    """Geschlossene Ketten der Länge L (n muss durch L teilbar sein): im Block qualifiziert Station i auch für i+1 (zyklisch im Block).
    L = 2: disjunkte Paare; L = n: ein Ring."""
    if n % laenge:
        raise ValueError("n ist nicht durch die Kettenlänge teilbar")
    q = []
    for j in range(n):
        b0 = (j // laenge) * laenge
        q.append(bits(j, b0 + ((j - b0 + 1) % laenge)))
    return tuple(q)


def offene_kette(n):
    """Gruppe j auch für Station j+1, die letzte Gruppe nur für die eigene: n-1 Bögen."""
    return tuple(bits(j, j + 1) if j < n - 1 else bits(j) for j in range(n))


def voll(n):
    return tuple((1 << n) - 1 for _ in range(n))


def aus_bogen(n, bogen):
    q = [1 << j for j in range(n)]
    for (j, i) in bogen:
        q[j] |= 1 << i
    return tuple(q)


def zufall_bogen(n, rng, k=None):
    """k Zusatzqualifikationen (Bögen j -> i, i != j) gleichverteilt ohne Zurücklegen (Standard k = n), partieller Fisher-Yates."""
    k = n if k is None else k
    bogen = [(j, i) for j in range(n) for i in range(n) if i != j]
    k = min(k, len(bogen))
    for a in range(k):
        b = rng.randint(a, len(bogen) - 1)
        bogen[a], bogen[b] = bogen[b], bogen[a]
    return aus_bogen(n, bogen[:k])


def zufall_je_gruppe(n, rng):
    """Jede Gruppe genau eine zufällige Zusatzstation."""
    q = []
    for j in range(n):
        i = rng.randint(0, n - 2)
        if i >= j:
            i += 1
        q.append(bits(j, i))
    return tuple(q)


def zufall_ziehung(n, familie, ziehung):
    """Ziehung Nummer `ziehung` (der Zufalls-Seed der App) der Familie "R" (n Bögen) oder "R1" (eine je Gruppe)."""
    rng = SplitMix64(seed_aus(familie, n, ziehung))
    return zufall_bogen(n, rng) if familie == "R" else zufall_je_gruppe(n, rng)


def eigener_entwurf(n, auswahl):
    """Entwurf aus der Auswahl je Gruppe (Tupel von n Tupeln mit Zusatzstationen). Ungültiges (eigene Station, außerhalb) entfällt."""
    q = []
    for j in range(n):
        m = 1 << j
        for i in (auswahl[j] if j < len(auswahl) else ()):
            if 0 <= int(i) < n and int(i) != j:
                m |= 1 << int(i)
        q.append(m)
    return tuple(q)


def auswahl_aus_entwurf(q):
    """Umkehrung: je Gruppe die Zusatzstationen als sortiertes Tupel."""
    n = len(q)
    return tuple(tuple(i for i in range(n) if i != j and (q[j] >> i) & 1) for j in range(n))


def heiss_neben_kalt(skala):
    """Reihenfolge der Stationen: abwechselnd die mit dem höchsten und dem niedrigsten mittleren Bedarf (Gleichstände nach Index).
    Eine Regel, kein Optimum."""
    n = len(skala)
    sortiert = sorted(range(n), key=lambda i: (-skala[i], i))
    out = []
    lo, hi = 0, n - 1
    while lo <= hi:
        out.append(sortiert[lo])
        lo += 1
        if lo <= hi:
            out.append(sortiert[hi])
            hi -= 1
    return out


def ring_in_reihenfolge(order):
    """Ring über die gegebene Reihenfolge der Stationen: Gruppe order[k] kann auch Station order[k+1] (zyklisch)."""
    n = len(order)
    q = [0] * n
    for k, j in enumerate(order):
        q[j] = bits(j, order[(k + 1) % n])
    return tuple(q)


VORLAGEN = ("ring", "paare", "kette", "heiss_kalt", "zufall", "leer")
VORLAGE_LABEL = {"ring": "Ring", "paare": "Paare", "kette": "Offene Kette", "heiss_kalt": "Heiß neben kalt", "zufall": "Zufall", "leer": "Leer"}


def vorlage_verfuegbar(name, n):
    """Paare gibt es nur bei geradem n >= 4 (bei n = 2 sind sie der Ring); Ring und Heiß neben kalt ab n = 3 (bei n = 2 ist der Ring voll)."""
    if name == "paare":
        return n % 2 == 0 and n >= 4
    if name in ("zufall",):
        return n >= 3
    return True


def vorlage(name, n, skala, zufalls_seed=0, zaehler=0):
    """Auswahl je Gruppe (Tupel von n Tupeln) für eine Vorlage. `skala`: mittlerer Bedarf je Station (für Heiß neben kalt)."""
    if name == "leer":
        return tuple(() for _ in range(n))
    if name == "ring":
        q = ring(n, 1)
    elif name == "paare":
        q = ketten(n, 2)
    elif name == "kette":
        q = offene_kette(n)
    elif name == "heiss_kalt":
        q = ring_in_reihenfolge(heiss_neben_kalt(skala))
    elif name == "zufall":
        q = zufall_bogen(n, SplitMix64(seed_aus("E", n, zufalls_seed, zaehler)))
    else:
        raise ValueError(name)
    return auswahl_aus_entwurf(q)


def entwurfssatz(n, zufalls_seed, eigener=None):
    """Geordnetes Wörterbuch aller festen Entwürfe der Einstellung (Name -> Masken). Welche es gibt, hängt nur von n ab:
    A ab n = 2, D1 ab n = 3 (bei n = 2 gleich F), D2 ab n = 4, D3 ab n = 5, Paare bei geradem n >= 4, C3/C4/C6 bei Teilbarkeit
    (und kleiner als n), R und R1 ab n = 3, E nur mit Eigenem Entwurf."""
    e = {"D0": ring(n, 0), "A": offene_kette(n)}
    for k in (1, 2, 3):
        if n - 1 > k:
            e["D%d" % k] = ring(n, k)
    if n == 2:
        e["D1"] = ring(2, 1)
    if n % 2 == 0 and n >= 4:
        e["P"] = ketten(n, 2)
    for laenge in (3, 4, 6):
        if n % laenge == 0 and laenge < n:
            e["C%d" % laenge] = ketten(n, laenge)
    if n >= 3:
        e["R"] = zufall_ziehung(n, "R", zufalls_seed)
        e["R1"] = zufall_ziehung(n, "R1", zufalls_seed)
    if eigener is not None:
        e["E"] = eigener
    e["F"] = voll(n)
    return e
