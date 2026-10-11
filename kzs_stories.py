"""Presets (alle fünf auf gemessenen Zellen der Vorab-Messreihe, Wirkungsgrad 100 %), ihre Geschichten und die Abnahmekriterien.

Jedes Preset gibt eine Einstellung und eine Geschichte vor. Die Kriterien stehen als Funktionen auf Kennzahlen und werden in
tests/test_stories.py an der Messreihe UND an der gezeigten Ziehung (Zufalls-Seed) geprüft, nie an der Streuung einer einzelnen Ziehung
allein. Kennzahlen in Prozent. Vorzeichenkriterien stehen mit Abstand zur Schwelle (ihr Standardfehler liegt unter 0,3 Punkten)."""

import kzs_constants as C

PRESET_ORDER = ("Ring, Paare, Zufall", "Block-Ungleichgewicht", "Überstreuung", "Wie viele lernen?", "Kleine Gruppe")

_BASIS = {"n": 6, "mu": 20, "r": 1.0, "dist": "poisson", "struct": "gleich", "eff": 1.0, "q": 1.0, "seed": 3}
PRESETS = {
    "Ring, Paare, Zufall": dict(_BASIS),
    "Block-Ungleichgewicht": dict(_BASIS, n=12, struct="block50", seed=1),
    "Überstreuung": dict(_BASIS, n=12, dist="k4", seed=10),
    "Wie viele lernen?": dict(_BASIS, q=0.3),
    "Kleine Gruppe": dict(_BASIS, n=3, seed=1),
}
PRESET_HELP = {
    "Ring, Paare, Zufall": "Derselbe Aufwand, drei Anordnungen: Der Ring holt fast alles, Paare und Zufall die Hälfte, die offene Kette zwei Drittel. "
                           "Sechs Stationen, mittlerer Bedarf 20, Poisson.",
    "Block-Ungleichgewicht": "Zwölf Stationen, sechs heiße nebeneinander: Freie Kapazität kommt nur über einen einzigen Bogen aus dem kalten Teil in den Block. "
                            "Der Zufall ist im Mittel besser als der Ring; erst heiß neben kalt (Vorlage im Selbstbau) oder drei Zusatzstationen je Gruppe helfen.",
    "Überstreuung": "Je stärker der Bedarf streut, desto mehr ist zu holen und desto weniger reicht der Ring: ein zweiter Bogen je Gruppe schließt den Rest.",
    "Wie viele lernen?": "Nicht alle müssen lernen: Mit 30 % jeder Gruppe holt der Ring über 80 %, die Paare sind bei ihrer Obergrenze schon bei der Hälfte.",
    "Kleine Gruppe": "Bei drei Stationen ist nichts zu verketten: Der Ring ist praktisch voll, Paare gibt es nicht, und der ganze Kuchen ist klein.",
}

# Beispieltag je Preset (Nummer des Szenarios, gefunden mit tools/seed_search.py; Regeln dort): der Tag, an dem die Geschichte sichtbar wird.
PRESET_TAG = {"Ring, Paare, Zufall": 8815, "Block-Ungleichgewicht": 17260, "Überstreuung": 10865, "Wie viele lernen?": 6518, "Kleine Gruppe": 6214}

# Kennzahlen (Prozent, falls nicht anders):
#   ring, d2, d3, paare, kette (A), c3     Anteil am Nutzen voller Flexibilität
#   r_mittel                               Mittel der Zufallsziehungen (R)
#   r_zug                                  die gezeigte Ziehung (Zufalls-Seed)
#   gewinn_pkt, gewinn_pt                  Gewinn von F gegenüber D0 (Servicegrad-Punkte, Personentage je Tag)
#   gewinn_poisson_n12                     Gewinn von F in der Poisson-Zelle n = 12, mu = 20 (Vergleich für „Überstreuung“)
#   q80                                    geschulter Anteil (Prozent der Gruppe) für 80 % des Nutzens beim Ring
#   ring_q50                               Ring bei halber Gruppe geschult
#   heiss_kalt                             Vorlage „heiß neben kalt“ (nur Live-Messung, nicht Teil der Messreihe)
#   hat_paare                              1 bei geradem n >= 4
#   ring_q30_paare, ...                    nach Bedarf
# Je Kriterium: (Beschriftung, Kennzahl, Vergleich, Schwelle). Fehlt eine Kennzahl (None), entfällt das Kriterium in dieser Fassung.
CRITERIA = {
    "Ring, Paare, Zufall": [
        ("Ring holt mindestens 99 %", "ring", ">=", 99.0),
        ("Paare holen mindestens 45 %", "paare", ">=", 45.0), ("Paare holen höchstens 55 %", "paare", "<=", 55.0),
        ("Offene Kette holt mindestens 60 %", "kette", ">=", 60.0), ("Offene Kette holt höchstens 72 %", "kette", "<=", 72.0),
        ("Dreierketten holen mindestens 66 %", "c3", ">=", 66.0), ("Dreierketten holen höchstens 77 %", "c3", "<=", 77.0),
        ("Zufall im Mittel mindestens 45 %", "r_mittel", ">=", 45.0), ("Zufall im Mittel höchstens 58 %", "r_mittel", "<=", 58.0),
        ("Gezeigte Ziehung mindestens 48 %", "r_zug", ">=", 48.0), ("Gezeigte Ziehung höchstens 55 %", "r_zug", "<=", 55.0),
        ("Gewinn von F mindestens 5 Punkte", "gewinn_pkt", ">=", 5.0),
    ],
    "Block-Ungleichgewicht": [
        ("Ring holt höchstens 45 %", "ring", "<=", 45.0),
        ("D2 holt mindestens 65 %", "d2", ">=", 65.0), ("D2 holt höchstens 80 %", "d2", "<=", 80.0),
        ("D3 holt mindestens 95 %", "d3", ">=", 95.0),
        ("Paare holen höchstens 2 %", "paare", "<=", 2.0), ("Offene Kette holt höchstens 2 %", "kette", "<=", 2.0),
        ("Zufall im Mittel mindestens 3 Punkte über dem Ring", "r_minus_ring", ">=", 3.0),
        ("Heiß neben kalt holt mindestens 95 %", "heiss_kalt", ">=", 95.0),
    ],
    "Überstreuung": [
        ("Ring holt mindestens 78 %", "ring", ">=", 78.0), ("Ring holt höchstens 85 %", "ring", "<=", 85.0),
        ("D2 holt mindestens 97 %", "d2", ">=", 97.0),
        ("Paare holen höchstens 45 %", "paare", "<=", 45.0),
        ("Gewinn von F mindestens 14 Punkte", "gewinn_pkt", ">=", 14.0),
        ("Gewinn mindestens das Doppelte der Poisson-Zelle (n = 12)", "gewinn_verhaeltnis", ">=", 2.0),
    ],
    "Wie viele lernen?": [
        ("Ring bei 30 % geschult mindestens 80 %", "ring", ">=", 80.0), ("Ring bei 30 % geschult höchstens 87 %", "ring", "<=", 87.0),
        ("Paare höchstens 52 %", "paare", "<=", 52.0),
        ("Für 80 % genügen weniger als 30 % der Gruppe", "q80", "<=", 30.0),
        ("Ring bei halber Gruppe mindestens 95 %", "ring_q50", ">=", 95.0),
    ],
    "Kleine Gruppe": [
        ("Ring holt mindestens 99,5 %", "ring", ">=", 99.5),
        ("Gewinn von F höchstens 4 Punkte", "gewinn_pkt", "<=", 4.0), ("Gewinn von F höchstens 2,5 Personentage je Tag", "gewinn_pt", "<=", 2.5),
        ("Zufall im Mittel mindestens 60 %", "r_mittel", ">=", 60.0), ("Zufall im Mittel höchstens 72 %", "r_mittel", "<=", 72.0),
        ("Keine Paare bei ungeradem n", "hat_paare", "<=", 0.0),
    ],
}


def check(name, facts):
    """Prüft die Kriterien eines Presets gegen ein Wörterbuch von Kennzahlen: Liste (Beschriftung, erfüllt oder None, Wert)."""
    out = []
    for label, key, op, thr in CRITERIA[name]:
        v = facts.get(key)
        if v is None:
            out.append((label, None, None))
            continue
        out.append((label, v >= thr if op == ">=" else v <= thr, v))
    return out


def preset_settings(name):
    """Das Preset als Settings (nur Schlüsselwörter)."""
    import kzs_pipeline as PL
    return PL.Settings(**PRESETS[name])


def measured_facts(name):
    """Kennzahlen aus der Messreihe (vorgerechnet): die Zelle des Presets und, bei Anteil geschult < 100 %, die Teil-Zelle."""
    import kzs_results as R
    p = PRESETS[name]
    s = preset_settings(name)
    c = R.cell_fuer(s)
    facts = {}
    ziehung = None
    if c is not None:
        if p["q"] >= 1.0:
            facts.update({"ring": R.ring(c), "d2": R.ring2(c), "d3": R.anteil(c, "D3"), "paare": R.anteil(c, "P"), "kette": R.anteil(c, "A"),
                          "c3": R.anteil(c, "C3")})
        rm = R.zufall_mittel(c, "R")
        facts["r_mittel"] = rm
        facts["gewinn_pkt"] = R.gewinn_punkte(c)
        facts["gewinn_pt"] = R.gewinn_pt(c)
        if rm is not None and R.ring(c) is not None:
            facts["r_minus_ring"] = rm - R.ring(c)
        if "R" in c["zufall"] and p["seed"] < c["zufall"]["R"]["ziehungen"]:
            ziehung = 100.0 * c["zufall"]["R"]["anteile"][p["seed"]]
        facts["r_zug"] = ziehung
        facts["hat_paare"] = 1.0 if (p["n"] % 2 == 0 and p["n"] >= 4) else 0.0
    if p["q"] < 1.0:
        ct = R.cell(s.n, s.mu, s.disp, s.korr, s.r, s.g, s.imb, True)
        if ct is not None:
            facts["ring"] = 100.0 * ct["teil"]["ring_q%s" % p["q"]]["anteil"]
            facts["paare"] = 100.0 * ct["teil"]["paar_q%s" % p["q"]]["anteil"] if "paar_q%s" % p["q"] in ct["teil"] else None
            facts["ring_q50"] = 100.0 * ct["teil"]["ring_q0.5"]["anteil"]
            facts["q80"] = _q80([ct["teil"]["ring_q%s" % q]["anteil"] for q in C.Q_OPTIONS])
    elif c is not None:
        ct = R.cell(s.n, s.mu, s.disp, s.korr, s.r, s.g, s.imb, True)
        if ct is not None:
            facts["ring_q50"] = 100.0 * ct["teil"]["ring_q0.5"]["anteil"]
            facts["q80"] = _q80([ct["teil"]["ring_q%s" % q]["anteil"] for q in C.Q_OPTIONS])
    for e in R.extras()["verschraenkt"]:
        if e["n"] == p["n"] and e["struct"] == p["struct"] and p["mu"] == 20 and p["dist"] == "poisson":
            facts["heiss_kalt"] = 100.0 * e["ring"]["anteil"]
    poisson12 = R.cell(12, 20)
    if poisson12 is not None and facts.get("gewinn_pkt") is not None:
        facts["gewinn_verhaeltnis"] = facts["gewinn_pkt"] / R.gewinn_punkte(poisson12)
    return facts


def _q80(anteile):
    import kzs_pipeline as PL
    q = PL.q_fuer_ziel(anteile, C.ZIEL_SCHULUNG / 100.0)
    return None if q is None else 100.0 * q


def instance_facts(name):
    """Kennzahlen der gezeigten Einstellung aus der Live-Rechnung (Stufe 1 bis 3 und die Vorlage heiß neben kalt)."""
    import kzs_designs as DS
    import kzs_flow as FL
    import kzs_pipeline as PL
    import kzs_stats as ST
    s = preset_settings(name)
    s1 = PL.stufe1(s)
    s2 = PL.stufe2(s)
    d = s1["designs"]

    def a(nm):
        v = d.get(nm)
        return None if v is None or v["anteil"] is None else 100.0 * v["anteil"]

    facts = {"ring": a("D1"), "d2": a("D2"), "d3": a("D3"), "paare": a("P"), "kette": a("A"), "c3": a("C3"), "r_zug": a("R"),
             "gewinn_pkt": s1["gewinn_punkte"], "gewinn_pt": s1["gewinn_pt"], "hat_paare": 1.0 if "P" in d else 0.0}
    if s.n <= 3 and facts["d2"] is None:
        facts["d2"] = 100.0
    if "R" in s2 and s2["R"]["mittel"] is not None:
        facts["r_mittel"] = 100.0 * s2["R"]["mittel"]
        if facts["ring"] is not None:
            facts["r_minus_ring"] = facts["r_mittel"] - facts["ring"]
    s3 = PL.stufe3(s)
    anteile = [a_ for a_, _ in s3["D1"]]
    facts["ring_q50"] = None if anteile[4] is None else 100.0 * anteile[4]
    facts["q80"] = _q80(anteile)
    ref = PL.Settings(n=12, mu=20, r=1.0, dist="poisson", struct="gleich", eff=1.0, q=1.0, seed=0)
    ref1 = PL.stufe1(ref)
    facts["gewinn_verhaeltnis"] = s1["gewinn_punkte"] / ref1["gewinn_punkte"]
    if s.imb is not None:
        D = PL.szenarien(s)
        d0, f = FL.bezug(D, s.S1, s.g)
        q = DS.ring_in_reihenfolge(DS.heiss_neben_kalt(s.skala))
        kz = ST.kennzahlen(FL.bedient(D, s.S1, q, s.q, s.g), D, d0, f)
        facts["heiss_kalt"] = 100.0 * kz["anteil"]
    return facts
