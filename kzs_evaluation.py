"""Auswertung einer Einstellung: erzeugte Sätze in drei Zuständen je Abschnitt, Diagnose der Ursache, Tabelle der Entwürfe.

Alle Schwellen stehen als benannte Konstanten in kzs_constants; jedes Vorzeichenkriterium verlangt zwei Standardfehler Abstand.
Funktionen sind rein (kein Streamlit). Anteile stehen in den Eingaben als Bruchteile, in den Ausgaben in Prozent."""

import math

import kzs_constants as C
import kzs_designs as DS
import kzs_pipeline as PL
import kzs_results as R


# --- Formatierung -------------------------------------------------------------------------------------------------------------------

def de(x, d=1, vorzeichen=False):
    """Zahl mit Dezimalkomma."""
    if x is None:
        return "–"
    s = f"{x:+.{d}f}" if vorzeichen else f"{x:.{d}f}"
    return s.replace(".", ",")


def thou(n):
    """Ganzzahl mit Tausenderpunkt (nur die Zahl, nie ein ganzer Satz umformatieren)."""
    return f"{int(round(n)):,}".replace(",", ".")


def pct(x):
    """Bruchteil -> Prozent (None bleibt None)."""
    return None if x is None else 100.0 * x


# --- Zahlen einer Einstellung --------------------------------------------------------------------------------------------------------

def zahlen(s, s1, s2=None):
    """Prozentwerte der Entwürfe aus Stufe 1 (und Stufe 2): {"d1": (Anteil, SE), ...}. Fehlende Entwürfe None.
    D2 ist bei n <= 3 gleich F (100 %), D1 bei n = 2 gleich F."""
    d = s1["designs"]

    def a(nm):
        v = d.get(nm)
        return None if v is None else (pct(v["anteil"]), pct(v["se"]) if v["se"] is not None else 0.0)

    z = {nm: a(nm) for nm in ("A", "D1", "D2", "D3", "P", "C3", "C4", "C6", "R", "R1", "E")}
    if z["D1"] is None and s.n <= 2:
        z["D1"] = (100.0, 0.0)
    if z["D2"] is None and s.n <= 3 and s.q >= 1.0:
        z["D2"] = (100.0, 0.0)
    z["rmittel"] = None
    if s2 and "R" in s2 and s2["R"]["mittel"] is not None:
        z["rmittel"] = (pct(s2["R"]["mittel"]), pct(s2["R"]["sd"]), s2["R"]["ziehungen"], pct(s2["R"]["min"]), pct(s2["R"]["max"]))
    z["r1mittel"] = None
    if s2 and "R1" in s2 and s2["R1"]["mittel"] is not None:
        z["r1mittel"] = (pct(s2["R1"]["mittel"]), pct(s2["R1"]["sd"]), s2["R1"]["ziehungen"], pct(s2["R1"]["min"]), pct(s2["R1"]["max"]))
    z["gewinn_pkt"] = s1["gewinn_punkte"]
    z["gewinn_pt"] = s1["gewinn_pt"]
    return z


def anteil_gezeigt(s1):
    """Der Anteil wird nur gezeigt, wenn der Gewinn von F über der Schwelle liegt (sonst ist er ein Quotient zweier Rauschgrößen)."""
    return s1["gewinn_punkte"] >= C.GEWINN_MIN_ANTEIL


# --- Ursachen ---------------------------------------------------------------------------------------------------------------------

def ursachen(s):
    """Welche Gegenfall-Bestandteile die Einstellung enthält (aus den Reglern, nicht aus den Zahlen)."""
    out = []
    if s.struct.startswith("block"):
        out.append("struktur")
    if s.dist in ("k10", "k4", "k10_korr", "k4_korr"):
        out.append("streuung")
    if s.eff < 1.0:
        out.append("wirkungsgrad")
    if s.mu == 5 and s.n >= 8:
        out.append("klein")
    if s.q < 1.0:
        out.append("schulung")
    return out


URSACHE_TEXT = {
    "struktur": "Die heißen Stationen hängen im Block aneinander, freie Kapazität aus dem kalten Teil kommt nur über einen einzigen Bogen hinein",
    "streuung": "Die Überstreuung des Bedarfs lässt auch den Ring an seine Grenzen kommen",
    "wirkungsgrad": "Mit Wirkungsgrad 80 % verliert jeder Umweg einen Teil der Kapazität, ein zweiter Bogen je Gruppe wird wieder wertvoll",
    "klein": "Bei kleinem Bedarf je Station (mittlerer Bedarf 5) und vielen Stationen bleibt auch dem Ring ein Rest",
    "schulung": "Nur ein Teil jeder Gruppe hat die Zusatzstationen gelernt, das begrenzt jeden Entwurf",
}


def erster_entwurf_ab(s, s1, schwelle=C.RING_HOCH):
    """Erster Ring (D2, D3) oder F, der mindestens `schwelle` Prozent holt: (Name, Anteil) oder None."""
    d = s1["designs"]
    for nm in ("D2", "D3"):
        v = d.get(nm)
        if v is not None and v["anteil"] is not None and 100.0 * v["anteil"] >= schwelle:
            return nm, 100.0 * v["anteil"]
    if s.n <= 3:
        return "F", 100.0
    return None


# --- Meldungen ---------------------------------------------------------------------------------------------------------------------

def aussage(key, level, text):
    return {"key": key, "level": level, "text": text}


def meldung_ring(s, s1):
    """① Wie viel holt die Verkettung? Ring gegen F."""
    z = zahlen(s, s1)
    if z["D1"] is None or z["D1"][0] is None or not anteil_gezeigt(s1):
        return aussage("ring", "info", f"Hier ist der Gewinn von F gegenüber D0 mit {de(s1['gewinn_punkte'], 2)} Servicegrad-Punkten so klein, dass der "
                       "Anteil am Nutzen nicht gezeigt wird: Er wäre ein Quotient zweier Rauschgrößen. Maßgeblich ist der absolute Gewinn.")
    d1, se1 = z["D1"]
    d2 = z["D2"][0] if z["D2"] is not None else None
    if s.n == 2:
        return aussage("ring", "success", "Bei zwei Stationen ist der Ring voll flexibel (D1 = F per Konstruktion): 100 % des Nutzens, es gibt nichts zu verketten.")
    if d1 + C.SE_FAKTOR * se1 < C.RING_MITTEL:
        txt = f"Der Ring reicht nicht: {de(d1)} %"
        txt += f", D2 {de(d2)} %" if d2 is not None else ""
        d3 = z["D3"]
        txt += f", D3 {de(d3[0])} %" if d3 is not None else ""
        return aussage("ring", "warning", txt + ".")
    if d1 - C.SE_FAKTOR * se1 >= C.RING_HOCH:
        zus = ""
        if d2 is not None:
            zus = f"; ein zweiter Bogen je Gruppe (D2) bringt {de(d2 - d1, 1)} Punkte mehr"
        if s.dist == "poisson" and s.eff >= 1.0:
            zus += ": bei Poisson-Bedarf fallen D2 bis F fast pfadweise zusammen"
        return aussage("ring", "success", f"Der Ring holt {de(d1)} % des Nutzens voller Flexibilität{zus}.")
    zus = f", ein zweiter Bogen je Gruppe {de(d2)} %" if d2 is not None else ""
    return aussage("ring", "info", f"Der Ring holt {de(d1)} %{zus}.")


def meldung_anordnung(s, s1, s2=None):
    """② Dieselbe Zahl Bögen, andere Anordnung: Ring gegen Paare (oder Zufall) und gegen den Zufall im Mittel."""
    z = zahlen(s, s1, s2)
    if s.n == 2:
        return aussage("anordnung", "info", "Bei zwei Stationen gibt es nur einen Entwurf mit Zusatzqualifikation je Gruppe: keine Anordnung zu vergleichen.")
    if z["D1"] is None or z["D1"][0] is None or not anteil_gezeigt(s1):
        return aussage("anordnung", "info", "Der Anteil am Nutzen wird hier nicht gezeigt (Gewinn von F zu klein).")
    d1, se1 = z["D1"]
    bogen = s1["designs"]["D1"]["bogen"]
    rm = z["rmittel"]
    if rm is not None and rm[0] > d1 + C.SE_FAKTOR * se1:
        return aussage("anordnung", "warning", f"Der Zufall schlägt den Ring: {de(rm[0])} % im Mittel gegen {de(d1)} %. Der Ring passt nicht zum Bedarf; "
                       "heiße neben kalte Stationen zu verketten (Vorlage im Selbstbau) ist die Regel dagegen.")
    partner = z["P"]
    pname = "Paare"
    if partner is None:
        partner = z["R"]
        pname = "zufällige Verteilung"
    if partner is None or partner[0] is None:
        return aussage("anordnung", "info", f"Der Ring holt {de(d1)} %.")
    pv, spv = partner
    diff_se = math.sqrt(se1 ** 2 + spv ** 2)
    if d1 - pv - C.SE_FAKTOR * diff_se >= C.ABSTAND_PAARE:
        return aussage("anordnung", "success", f"Die Anordnung entscheidet: gleiche {bogen} Bögen, {de(d1)} % als Ring gegen {de(pv)} % als {pname}.")
    wer = "Paare liegen" if pname == "Paare" else "Die zufällige Verteilung liegt"
    return aussage("anordnung", "info", f"{wer} nahe am Ring: {de(pv)} % gegen {de(d1)} % bei gleichen {bogen} Bögen.")


def meldung_diagnose(s, s1):
    """③ Wann reicht der Ring nicht? Diagnose aus den Reglern."""
    z = zahlen(s, s1)
    if z["D1"] is None or z["D1"][0] is None or not anteil_gezeigt(s1):
        return aussage("diagnose", "info", "Keine Diagnose: der Gewinn von F ist hier zu klein, um einen Anteil auszuweisen.")
    d1, se1 = z["D1"]
    if s.n == 2:
        return aussage("diagnose", "info", "Bei zwei Stationen gibt es keinen Gegenfall: Der Ring ist F.")
    if d1 + C.SE_FAKTOR * se1 >= C.RING_HOCH or d1 >= C.RING_HOCH:
        hinweise = []
        for label, (n_, kw) in (("Block ±50 %, n = 12", (12, dict(imb=("block", 0.5)))), ("Überstreuung k = 4, n = 12", (12, dict(disp=4))),
                                ("Wirkungsgrad 80 %, n = 12", (12, dict(g=0.8))), ("mittlerer Bedarf 5, n = 12", (12, dict(mu=5)))):
            c = R.cell(n_, kw.get("mu", 20), kw.get("disp"), 0.0, 1.0, kw.get("g", 1.0), kw.get("imb"))
            if c is not None:
                hinweise.append(f"{label}: {de(R.ring(c))} %")
        return aussage("diagnose", "success", "Hier reicht der Ring. In der Messreihe schwächen ihn (Ring-Anteil; Kapazität gleich Bedarf, mittlerer Bedarf 20, "
                       "Poisson, soweit nicht genannt): " + "; ".join(hinweise) + ".")
    ur = ursachen(s)
    rest = erster_entwurf_ab(s, s1)
    if rest is None:
        wer = " Auch D3 holt noch keine 95 %."
    elif rest[0] == "F":
        wer = " Erst F holt den Rest."
    else:
        wer = f" Erst {rest[0]} (Ring mit {rest[0][1:]} Zusatzstationen je Gruppe) holt {de(rest[1])} %."
    if len(ur) == 1:
        return aussage("diagnose", "warning", f"Der Ring holt hier {de(d1)} %. {URSACHE_TEXT[ur[0]]}.{wer}")
    if len(ur) >= 2:
        return aussage("diagnose", "warning", f"Mehrere Ursachen zugleich: der Ring holt {de(d1)} %.{wer}")
    return aussage("diagnose", "warning", f"Der Ring holt {de(d1)} %, ohne dass ein einzelner Gegenfall der Regler zu erkennen ist "
                   f"(Kapazität gegen Bedarf, Anordnung).{wer}")


def meldung_eigener(s, s1):
    """Eigener Entwurf gegen den Ring."""
    d = s1["designs"]
    if "E" not in d:
        return aussage("eigen", "info", "Noch keine Zusatzqualifikation gewählt: Der Eigene Entwurf entspricht D0 (jede Gruppe nur ihre Station). "
                       "Wählen Sie je Gruppe Zusatzstationen oder laden Sie eine Vorlage.")
    e = d["E"]
    if e["anteil"] is None or not anteil_gezeigt(s1):
        return aussage("eigen", "info", f"Dein Entwurf hat {e['bogen']} Zusatzqualifikationen; der Anteil am Nutzen wird hier nicht gezeigt (Gewinn von F zu klein).")
    ring = d.get("D1")
    ea, ese = pct(e["anteil"]), pct(e["se"])
    if ring is None or ring["anteil"] is None:
        return aussage("eigen", "info", f"Dein Entwurf holt {de(ea)} % mit {e['bogen']} Zusatzqualifikationen.")
    ra, rse = pct(ring["anteil"]), pct(ring["se"])
    rb = ring["bogen"]
    diff_se = math.sqrt(ese ** 2 + rse ** 2)
    if e["bogen"] < rb and ea >= 0.95 * ra:
        return aussage("eigen", "success", f"Mit weniger Aufwand: Dein Entwurf holt {de(ea)} % mit {e['bogen']} Zusatzqualifikationen (Ring: {de(ra)} % mit {rb}).")
    if ea >= ra - C.SE_FAKTOR * diff_se:
        return aussage("eigen", "success", f"Dein Entwurf holt {de(ea)} % mit {e['bogen']} Zusatzqualifikationen (Ring: {de(ra)} % mit {rb}).")
    if e["bogen"] >= rb:
        return aussage("eigen", "warning", f"Mit {e['bogen']} Bögen holt der Ring mehr: {de(ra)} % gegen {de(ea)} % (Ring: {rb} Bögen).")
    return aussage("eigen", "info", f"Weniger Aufwand, weniger Nutzen: {de(ea)} % mit {e['bogen']} Bögen, der Ring holt {de(ra)} % mit {rb}.")


def meldung_schulung(s, s1, s3):
    """④ Wie viele müssen lernen? Anteil geschult für 80 % des Nutzens (Ring, bei gebautem Entwurf auch der Eigene)."""
    import kzs_pipeline as PL
    if not anteil_gezeigt(s1):
        return aussage("schulung", "info", "Der Anteil am Nutzen wird hier nicht gezeigt (Gewinn von F zu klein).")
    name = "E" if "E" in s3 else "D1"
    anteile = [a for a, _ in s3[name]]
    ziel = C.ZIEL_SCHULUNG / 100.0
    q80 = PL.q_fuer_ziel(anteile, ziel)
    wer = "Dein Entwurf" if name == "E" else "Der Ring"
    if q80 is not None and q80 <= C.SCHULUNG_WENIG + 1e-12:
        return aussage("schulung", "success", f"Es genügen {de(100 * q80, 0)} % jeder Gruppe: {wer} holt damit {de(C.ZIEL_SCHULUNG, 0)} % des Nutzens voller Flexibilität.")
    if q80 is not None:
        return aussage("schulung", "info", f"Viele müssen lernen: {wer} braucht {de(100 * q80, 0)} % jeder Gruppe für {de(C.ZIEL_SCHULUNG, 0)} % des Nutzens.")
    top = anteile[-1]
    return aussage("schulung", "warning", f"Mehr Schulung ändert nichts: {wer} erreicht auch mit allen Personen nur {de(pct(top))} % (Obergrenze dieses "
                   f"Entwurfs); {de(C.ZIEL_SCHULUNG, 0)} % des Nutzens liegen außer Reichweite. Nicht die Zahl der Geschulten, die Anordnung ist hier das Problem.")


def meldung_kuchen(s, s1):
    """⑤ Was der Anteil nicht sagt: absoluter Gewinn."""
    g, pt = s1["gewinn_punkte"], s1["gewinn_pt"]
    if g < C.KUCHEN_KLEIN:
        return aussage("kuchen", "warning", f"Der ganze Kuchen ist klein: voll flexibel gewinnt man {de(g, 2)} Servicegrad-Punkte, {de(pt, 2)} Personentage je Tag. "
                       "Auch ein hoher Anteil davon ist wenig in absoluten Zahlen.")
    if s.n <= 3:
        txt = "Ring = F" if s.n == 2 else "D2 = F"
        return aussage("kuchen", "info", f"{txt} per Konstruktion: Es gibt nichts weiter zu verketten. Voll flexibel gewinnt man {de(g, 2)} Punkte, {de(pt, 2)} Personentage je Tag.")
    ring = s1["designs"].get("D1")
    if ring is not None and ring["bogen"] > 0:
        je = (s1["designs"]["D0"]["unterdeckung"] - ring["unterdeckung"]) / ring["bogen"]
        return aussage("kuchen", "info", f"Voll flexibel gewinnt man {de(g, 2)} Servicegrad-Punkte, {de(pt, 2)} Personentage je Tag; der Ring bringt davon "
                       f"{de(je, 2)} Personentage je Tag und Zusatzqualifikation. Der Preis der Schulung ist nicht modelliert.")
    return aussage("kuchen", "info", f"Voll flexibel gewinnt man {de(g, 2)} Servicegrad-Punkte, {de(pt, 2)} Personentage je Tag.")


def alle_meldungen(s, s1, s2=None, s3=None):
    out = {"ring": meldung_ring(s, s1), "anordnung": meldung_anordnung(s, s1, s2), "diagnose": meldung_diagnose(s, s1),
           "eigen": meldung_eigener(s, s1), "kuchen": meldung_kuchen(s, s1)}
    if s3 is not None:
        out["schulung"] = meldung_schulung(s, s1, s3)
    return out


# --- Zeithinweis -----------------------------------------------------------------------------------------------------------------

def zeithinweis(s):
    """Hinweis zur Rechenzeit der Einstellung (None, wenn unauffällig)."""
    if s.eff < 1.0 and s.n >= C.ZEITHINWEIS_N:
        return "n = 12 mit Wirkungsgrad 80 % rechnet mit 800 Szenarien je Entwurf ein lineares Programm je Szenario: bis zu etwa 3 Sekunden."
    return None


# --- Tabelle der Entwürfe --------------------------------------------------------------------------------------------------------------

def belegschaft_mit_zusatz(q, s_q):
    """Anteil der Belegschaft mit mindestens einer Zusatzstation: Gruppen mit Bogen mal Anteil geschult."""
    n = len(q)
    return s_q * sum(1 for m in q if bin(m).count("1") > 1) / n


def tabelle(s, s1, s2=None, o_n4=None, o_n6=None):
    """Zeilen der Tabelle der Entwürfe (Liste von Wörterbüchern). Anteil in Prozent, Standardfehler in Punkten.
    o_n4: Kennzahlen des live gerechneten O (n = 4); o_n6: Zelle der Messreihe mit O (n = 6)."""
    d = s1["designs"]
    z = zahlen(s, s1, s2)
    zeigen = anteil_gezeigt(s1)
    rows = []
    for key in C.ANZEIGE_REIHENFOLGE:
        if key == "O":
            if o_n4 is not None:
                kz, quelle = o_n4, "live, Aufzählung (27 Klassen)"
            elif o_n6 is not None:
                v = o_n6["entwuerfe"].get("O")
                kz = {"anteil": v["anteil"], "se": v["anteil_se"], "sg": v["sg"], "unterdeckung": v["unterdeckung"], "bogen": v["bogen"]}
                quelle = "vorgerechnet, Aufzählung (1.043 Klassen)"
            else:
                continue
        elif key not in d:
            continue
        else:
            kz, quelle = d[key], "live"
        a = kz["anteil"]
        row = {"Kürzel": key, "Entwurf": C.ENTWURF_KURZ[key], "Bögen": kz["bogen"], "Anteil %": (pct(a) if (zeigen and a is not None) else None),
               "± 2 SE": (2 * pct(kz["se"]) if (zeigen and kz["se"] is not None) else None),
               "Servicegrad %": 100.0 * kz["sg"], "Unterdeckung (PT/Tag)": kz["unterdeckung"], "Quelle": quelle}
        if key in ("R", "R1"):
            m = z["rmittel"] if key == "R" else z["r1mittel"]
            if m is not None:
                row["Mittel der Ziehungen %"] = m[0]
                row["Streuung (sd)"] = m[1]
                row["Ziehungen"] = m[2]
        rows.append(row)
    return rows
