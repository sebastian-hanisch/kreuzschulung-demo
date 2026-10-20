"""Kreuzschulung: wen anlernen? - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Ein Lager hat Zonen (Wareneingang, Kommissionierung, Verpackung, Versand, ...), je Zone eine Gruppe mit der Hauptqualifikation. Der Tagesbedarf je
Zone ist zufällig. Kreuzschulung gibt Gruppen Zusatzzonen. Die Demo misst, wie viel vom Nutzen voller Flexibilität eine Anordnung holt, wann auch
der Ring nicht reicht und wie viele Mitarbeitende überhaupt lernen müssen.

Lauffähig mit: streamlit run app.py
"""

import dataclasses

import pandas as pd
import streamlit as st

import kzs_constants as C
import kzs_designs as DS
import kzs_evaluation as E
import kzs_pipeline as PL
import kzs_results as R
import kzs_stories as S
import kzs_visualization as V
from kzs_pdf_export import generate_pdf
from kzs_presets import (SETTING_SPECS, apply_preset, apply_template, bounds, init_session_state_defaults, load_permalink_settings, own_from_state,
                         own_key, randomize_day, randomize_seed, settings_from_state, sync_query_params)

st.set_page_config(page_title="Kreuzschulung: wen anlernen? – Sebastian Hanisch", layout="wide")


# --- Rechnung mit Ergebnis-Cache je Einstellung (alle Regler und der Eigene Entwurf im Schlüssel) -----------------------------------------

@st.cache_data(show_spinner=False, max_entries=64)
def _stufe1(s):
    return PL.stufe1(s)


@st.cache_data(show_spinner=False, max_entries=64)
def _stufe2(s):
    return PL.stufe2(s)


@st.cache_data(show_spinner=False, max_entries=64)
def _stufe3(s):
    return PL.stufe3(s)


@st.cache_data(show_spinner=False, max_entries=16)
def _bester_n4(s):
    return PL.bester_entwurf(s)


@st.cache_data(show_spinner=False, max_entries=64)
def _tag(s, masken, tag):
    return PL.beispieltag(s, masken, tag)


def _ohne(s, **kw):
    """Dieselbe Einstellung ohne die Größen, von denen eine Stufe nicht abhängt (gemeinsamer Cache-Eintrag)."""
    return dataclasses.replace(s, **kw)


def namen_station(i):
    return f"Station {i + 1}"


def say(item):
    {"success": st.success, "info": st.info, "warning": st.warning}[item["level"]](f"💡 {item['text']}")


# --- Kopf ----------------------------------------------------------------------------------------------------------------------------

st.title("🎓 Kreuzschulung: wen anlernen?")
st.markdown(
    """
Ein Lager hat **Zonen** (Wareneingang, Kommissionierung, Verpackung, Versand und weitere), je Zone eine Gruppe mit der Hauptqualifikation. Der Tagesbedarf je Zone
ist zufällig: Wo er die eigene Gruppe übersteigt, bleibt Arbeit liegen, während eine andere Gruppe Kapazität übrig hat. **Kreuzschulung** gibt Gruppen eine Zusatzzone.
Hier heißen die Zonen **Stationen**. Die Demo zeigt in der Reihenfolge der Befunde: wie viel eine Verkettung vom **Nutzen voller Flexibilität** holt, dass bei gleicher
Zahl Zusatzqualifikationen die **Anordnung** entscheidet, **wann auch der Ring nicht reicht** und **wie viele Mitarbeitende** überhaupt lernen müssen. Live auf 20.000
Szenarien, dazu die vorgerechnete Messreihe (Abschnitt **📐 Was die Messreihe zeigt**; Methode und Formeln in den Expandern **🔧 Wie wir das erreichen**,
**Wie funktioniert diese Demo?** und **📐 Mathematische Formulierung**).

Das Ergebnis ist Lehrbuchwissen (Prozessflexibilität, „lange Kette“): Die Demo vermisst es an Poisson- und Gamma-Poisson-Bedarf, sie entdeckt es nicht. Alle Parameter
sind erfunden: Beispielwerte, keine Prognose für Ihren Betrieb. Der Preis der Schulung ist nicht modelliert.
"""
)

# erklaerseite:einfach:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/kreuzschulung-erklaert.json, nicht von Hand ändern)
with st.expander("💬 In einfachen Worten"):
    st.markdown(
        """
Ein Lager hat mehrere **Stationen**, und zu jeder gehört eine Gruppe mit ihrer Hauptqualifikation. Der Tagesbedarf je Station ist zufällig: Mal ist an einer Station zu viel zu tun, während eine andere Gruppe Leerlauf hat. Bringt man Gruppen eine Zusatzstation bei, können sie sich gegenseitig aushelfen. Die Demo fragt, wie viel vom Nutzen voller Flexibilität man mit wenigen Zusatzqualifikationen holt und warum dabei die **Anordnung** zählt: Verbindet man die Stationen zu einem geschlossenen Ring, hilft das weit mehr als dieselbe Zahl Qualifikationen als Paare. Sie zeigt auch, wann selbst der Ring nicht reicht und wie viele Mitarbeitende überhaupt lernen müssen. Alle Parameter sind erfunden, der Preis der Schulung ist nicht modelliert.

[Ausführlich und verständlich erklärt, mit Fachteil](https://sebastianhanisch.net/kreuzschulung-erklaert.html)
        """
    )
# erklaerseite:einfach:end
st.caption(
    "Die Lücke, die die [Schichtplanung](https://sebastianhanisch-shift-demo.streamlit.app/) („keine Qualifikationen“) lässt: Wer lernt welche Zusatzstation? "
    "Pooling als Grenzfall kennt die [M/M/c-Warteschlange](https://sebastianhanisch-mmc-queue-demo.streamlit.app/) (alle zusammen oder getrennt); "
    "Design mit Rückgriff nach der Realisierung gibt es auch im [Netzdesign unter Unsicherheit](https://sebastianhanisch-netzdesign-unsicherheit-demo.streamlit.app/), "
    "dort mit Fixkosten, hier ist nur die Anordnung der Verbindungen bei gleichem Budget die Entscheidung."
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
row1 = st.columns(3)
row2 = st.columns(3)
for i, name in enumerate(S.PRESET_ORDER):
    with (row1 if i < 3 else row2)[i % 3]:
        st.button(name, key=f"preset_{name}", width="stretch", on_click=apply_preset, args=(name,), help=S.PRESET_HELP[name])
st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider, auch den Eigenen Entwurf – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.markdown("**Betrieb**")
    st.select_slider("Zahl der Stationen (je eine Gruppe)", options=C.N_OPTIONS, key="kzs_n_select", format_func=lambda n: f"{n} Stationen",
                     help="Gemessene Stufen. Bei 2 Stationen ist der Ring gleich F, bei ungeradem n fehlen die Paare, Ketten gibt es nur, wenn n durch die Länge teilbar ist.")
    st.select_slider("Mittlerer Tagesbedarf je Station (Personentage)", options=C.MU_OPTIONS, key="kzs_mu_select",
                     help="Kleiner Bedarf schwächt auch den Ring. Die Kapazität je Gruppe ist Verhältnis mal diesem Bedarf.")
    st.select_slider("Kapazität je Gruppe im Verhältnis zum Bedarf", options=C.R_OPTIONS, key="kzs_cap_select", format_func=lambda r: f"{round(100 * r)} %",
                     help="Bei 90 % deckelt die Kapazität jeden Entwurf; der Anteil am Nutzen bleibt aussagekräftig, der absolute Gewinn schrumpft.")
    st.markdown("**Bedarf**")
    st.select_slider("Verteilung des Bedarfs", options=C.DIST_ORDER, key="kzs_dist_select", format_func=lambda d: C.DIST_LABELS[d],
                     help="Poisson oder Gamma-Poisson (überstreut, Varianz mu + mu²/k). Die gemeinsame Schwankung ist nur mit Überstreuung definiert, "
                          "darum ein Regler mit fünf Zuständen statt zwei.")
    st.select_slider("Struktur des mittleren Bedarfs", options=C.STRUCT_ORDER, key="kzs_imb_select", format_func=lambda x: C.STRUCT_LABELS[x],
                     help="Block: die erste Hälfte der Stationen ist heiß, die zweite kalt. Abwechselnd: gerade Stationen heiß. Der Gesamtbedarf bleibt gleich.")
    st.markdown("**Qualifikation**")
    st.select_slider("Wirkungsgrad der Zusatzqualifikation", options=C.EFF_OPTIONS, key="kzs_eff_select", format_func=lambda g: C.EFF_LABELS[g],
                     help="Gruppe j liefert auf einer Zusatzstation nur diesen Anteil je Einheit Kapazität. Bei 80 % rechnet die App ein lineares Programm je Szenario "
                          "(800 Szenarien wie die Messreihe) und zeigt größere Standardfehler.")
    st.select_slider("Anteil jeder Gruppe, der die Zusatzstationen lernt", options=C.Q_OPTIONS, key="kzs_q_select", format_func=lambda q: f"{round(100 * q)} %",
                     help="Wirkt auf alle Entwürfe außer D0 und F (den beiden Bezugspunkten). Die ungeschulten Personen können nur ihre eigene Station.")
    st.slider("Zufalls-Seed der Zufallsentwürfe", *bounds("kzs_seed_input"), key="kzs_seed_input",
              help="Wählt die gezeigte Ziehung der Zeilen „Zufall“ und „Zufall je Gruppe“. 0 bis 23 (n ≤ 8) bzw. 0 bis 11 (n = 12) sind die Ziehungen der Messreihe.")
    st.button("🎲 Neue Zufallsziehung", width="stretch", on_click=randomize_seed)

values = {k: st.session_state[k] for k in SETTING_SPECS if k != "kzs_day_number"}
n_ = int(values["kzs_n_select"])
own = own_from_state(n_)
sync_query_params(values | {"kzs_day_number": st.session_state["kzs_day_number"]}, own)
settings = settings_from_state(values, own)
zustand = R.zustand(settings)
hinweis = E.zeithinweis(settings)

st.markdown("---")
st.markdown("## 🎓 Was holt die Verkettung?")
BADGE = {"gemessen": "🟢 **gemessen**: Messpunkt der Vorab-Messreihe, jede Zahl unten ist dort nachschlagbar.",
         "nicht gemessen": "⚪ **nicht gemessen**: kein Messpunkt der Messreihe; die Zahlen sind live exakt gerechnet, aber die Aussagen der Messreihe sind hier nicht belegt "
                           "(siehe Abdeckung im Abschnitt „Was die Messreihe zeigt“).",
         "bedingt": "🟡 **bedingt**: die Kombination ist ein Messpunkt, der Anteil geschult unter 100 % aber nur in 9 Zellen gemessen; diese Zahlen gelten unter der Annahme "
                    "des exakt gerechneten Teilqualifikationsmodells."}
st.caption(BADGE[zustand] + (" Messreihe: 147 Zellen, 138 Reglerkombinationen von 2.700." if zustand != "gemessen" else ""))
if hinweis:
    st.caption("⏱️ " + hinweis)
metrics_box = st.container()

# --- Stufe 1 --------------------------------------------------------------------------------------------------------------------------
with st.spinner("Stufe 1: Bezugspunkte und alle festen Entwürfe (meist unter einer Sekunde) …"):
    s1 = _stufe1(settings)
d = s1["designs"]
has_own = "E" in d
focus = "E" if has_own else "D1"
fk = d[focus]
zeigen = E.anteil_gezeigt(s1)

with metrics_box:
    m = st.columns(2)
    ring_d = d.get("D1")
    label = "Dein Entwurf holt" if has_own else "Der Ring (D1) holt"
    if zeigen and fk["anteil"] is not None:
        delta = f"± {E.de(2 * E.pct(fk['se']), 1)} Punkte (2 SE)"
        if has_own and ring_d is not None and ring_d["anteil"] is not None:
            delta += f"; Ring {E.de(E.pct(ring_d['anteil']))} %"
        m[0].metric(label, f"{E.de(E.pct(fk['anteil']))} %", delta=delta, delta_color="off",
                    help="Anteil am Nutzen voller Flexibilität: (Servicegrad des Entwurfs − Servicegrad von D0) geteilt durch (Servicegrad von F − Servicegrad von D0), "
                         "auf denselben 20.000 Szenarien (bei Wirkungsgrad 80 %: 800). Der absolute Gewinn steht daneben.")
    else:
        m[0].metric(label, "nicht gezeigt", delta="Gewinn von F zu klein", delta_color="off")
    m[1].metric("Servicegrad", f"{E.de(100 * fk['sg'])} %",
                delta=f"D0 {E.de(100 * d['D0']['sg'])} % → F {E.de(100 * d['F']['sg'])} %", delta_color="off",
                help="Verhältnis der Erwartungen: bedienter Bedarf geteilt durch Bedarf, über alle Szenarien. D0: jede Gruppe nur ihre Station, F: jede Gruppe jede Station.")
    m2 = st.columns(2)
    bel = E.belegschaft_mit_zusatz(fk["masken"], settings.q)
    m2[0].metric("Zusatzqualifikationen (Bögen)", f"{fk['bogen']}",
                 delta=f"{E.de(100 * bel, 0)} % der Belegschaft" + (f"; Ring {ring_d['bogen']}" if ring_d is not None else ""),
                 delta_color="off", help="Ein Bogen heißt: eine Gruppe ist für eine weitere Station qualifiziert. Der Prozentwert darunter ist der Anteil der Belegschaft mit mindestens einer "
                      "Zusatzstation (Gruppen mit Bogen mal Anteil geschult).")
    m2[1].metric("Gewinn voller Flexibilität", f"{E.de(s1['gewinn_pt'], 2)} PT je Tag",
                 delta=f"{E.de(s1['gewinn_punkte'], 2)} Servicegrad-Punkte", delta_color="off",
                 help=f"Absolut: Unterdeckung von D0 minus Unterdeckung von F, in Personentagen (PT) je Tag; der mittlere Bedarf ist {E.de(s1['bedarf_mittel'], 0)} Personentage. "
                      "Der Anteil allein sagt nicht, wie groß der ganze Kuchen ist.")

# --- ① ---------------------------------------------------------------------------------------------------------------------------------
st.markdown("### ① Wie viel holt die Verkettung?")
meld = E.alle_meldungen(settings, s1)
say(meld["ring"])

with st.spinner("Stufe 2: Streuung der Zufallsentwürfe (meist unter einer Sekunde) …"):
    s2 = _stufe2(_ohne(settings, seed=0, own=()))
meld = E.alle_meldungen(settings, s1, s2)
rows = E.tabelle(settings, s1, s2, o_n4=_bester_n4(settings) if (settings.n == 4 and settings.imb is None and settings.g >= 1.0) else None,
                 o_n6=(R.cell_fuer(settings) if (settings.n == 6 and settings.imb is None and settings.g >= 1.0 and settings.q >= 1.0
                                                  and R.cell_fuer(settings) is not None and "O" in R.cell_fuer(settings)["entwuerfe"]) else None))
c1, c2 = st.columns([3, 2])
with c1:
    st.plotly_chart(V.build_designs_bar(rows), width="stretch", key=f"bar_{settings.n}_{settings.mu}_{settings.dist}_{settings.struct}_{settings.q}_{settings.eff}")
    st.caption("Anteil am Nutzen voller Flexibilität je Entwurf, Striche ± 2 Standardfehler; die Raute ist das Mittel der Ziehungen der Zufallsentwürfe ± ihre Streuung "
               f"({settings.n_ziehungen} Ziehungen). Die Zahl der Bögen steht in der Tabelle.")
with c2:
    cols = ["Kürzel", "Entwurf", "Bögen", "Anteil %", "± 2 SE", "Servicegrad %", "Unterdeckung (PT/Tag)"]
    df = pd.DataFrame(rows)
    show = df[[c for c in cols if c in df.columns]].copy()
    st.dataframe(show, width="stretch", hide_index=True, column_config={
        "Anteil %": st.column_config.NumberColumn(format="%.1f"), "± 2 SE": st.column_config.NumberColumn(format="%.2f"),
        "Servicegrad %": st.column_config.NumberColumn(format="%.2f"), "Unterdeckung (PT/Tag)": st.column_config.NumberColumn(format="%.2f")})
    if not zeigen:
        st.caption("Der Anteil wird nicht gezeigt: Der Gewinn von F liegt unter der Schwelle.")


def coverage_caption(s):
    rec = R.abdeckung_zeile(s)
    if rec is None:
        st.caption("Die Abdeckungsrechnung liegt nicht vor.")
        return
    urt = R.abdeckung_aussagen(rec, s.n)
    where = "Messpunkt" if R.ist_messpunkt(s) else "kein Messpunkt"
    txt = {"gilt": "gilt", "gilt nicht": "gilt nicht", "unklar": "unklar", "n/a": "nicht anwendbar"}
    st.caption(f"Abdeckung ({where}; alle 2.700 Kombinationen vorgerechnet, zwei Standardfehler): A1 „Ring ≥ 95 %“ {txt[urt['A1']]}; A2 „Paare ≤ 60 %“ {txt[urt['A2']]}; "
               f"A3 „Ring ≥ Zufall + 20 Punkte“ {txt[urt['A3']]}; A4 „D2 ≥ Ring + 5 Punkte“ {txt[urt['A4']]}; A5 „Zufall über dem Ring“ {txt[urt['A5']]}.")


coverage_caption(settings)

# --- ② ---------------------------------------------------------------------------------------------------------------------------------
st.markdown("### ② Dieselbe Zahl Bögen, andere Anordnung")
say(meld["anordnung"])
if s2.get("R"):
    r2 = s2["R"]
    st.caption(f"Zufall: {r2['ziehungen']} Ziehungen von n Bögen, Mittel {E.de(E.pct(r2['mittel']))} %, Streuung {E.de(E.pct(r2['sd']))} Punkte, kleinste "
               f"{E.de(E.pct(r2['min']))} %, größte {E.de(E.pct(r2['max']))} %. Gezeigt ist die Ziehung mit dem Zufalls-Seed {settings.seed}.")

# --- ③ ---------------------------------------------------------------------------------------------------------------------------------
st.markdown("### ③ Wann reicht der Ring nicht?")
say(meld["diagnose"])

# --- Selbstbau ---------------------------------------------------------------------------------------------------------------------------
st.markdown("### 🛠️ Eigenen Entwurf bauen")
st.caption("Wählen Sie je Gruppe die Stationen, die sie zusätzlich lernt; oder laden Sie eine Vorlage. „Heiß neben kalt“ sortiert die Stationen nach mittlerem Bedarf "
           "und verkettet abwechselnd die höchste mit der niedrigsten: **eine Regel, kein Optimum**. Der Graph ist nur Anzeige, die Auswahl links ist die Eingabe.")
tpl = [t for t in DS.VORLAGEN if DS.vorlage_verfuegbar(t, settings.n)]
tcols = st.columns(len(tpl))
for col, t in zip(tcols, tpl):
    with col:
        st.button(DS.VORLAGE_LABEL[t], key=f"kzs_tpl_{t}", width="stretch", on_click=apply_template, args=(t,),
                  help="Füllt die Auswahl je Gruppe; jede Gruppe kann danach von Hand geändert werden.")
left, right = st.columns([3, 2])
with left:
    grid = st.columns(2 if settings.n <= 6 else 3)
    for j in range(settings.n):
        with grid[j % len(grid)]:
            st.multiselect(f"Gruppe {j + 1} lernt zusätzlich", options=[i for i in range(settings.n) if i != j], key=own_key(settings.n, j),
                           format_func=namen_station, placeholder="keine")
with right:
    own_masken = settings.own_masks if settings.own_masks is not None else DS.ring(settings.n, 0)
    st.plotly_chart(V.build_graph(settings.n, own_masken, settings.skala, titel="Eigener Entwurf"), width="content",
                    key=f"graph_own_{settings.n}_{'-'.join(str(m) for m in own_masken)}_{settings.struct}")
    st.caption("Knoten: Gruppe mit ihrer Hauptstation; Pfeil: Gruppe kann auch diese Station. Orange: heiße, blau: kalte Station (mittlerer Bedarf).")
say(meld["eigen"])

# --- Stufe 3 --------------------------------------------------------------------------------------------------------------------------
with st.spinner("Stufe 3: Kurve der Teilqualifikation (meist unter einer Sekunde, bei n = 12 mit Wirkungsgrad 80 % bis zu einigen Sekunden) …"):
    s3 = _stufe3(_ohne(settings, seed=0, q=1.0))
meld = E.alle_meldungen(settings, s1, s2, s3)
st.markdown("### ④ Wie viele müssen lernen?")
say(meld["schulung"])
st.plotly_chart(V.build_teil_kurve({k: [a for a, _ in v] for k, v in s3.items() if k != "sekunden"}, q_aktuell=settings.q), width="stretch",
                key=f"teil_{settings.n}_{settings.mu}_{settings.dist}_{settings.struct}_{settings.eff}_{'own' if has_own else 'ring'}")
st.caption("Anteil am Nutzen gegen den geschulten Anteil jeder Gruppe (Ring durchgezogen, Paare gestrichelt, Eigener Entwurf gepunktet); gepunktet waagerecht die 80 %. "
           "Der geschulte Anteil wird als Eigenkapazität zuerst, dann derselbe Graph mit reduziertem Bedarf gerechnet (exakt).")

st.markdown("### ⑤ Was der Anteil nicht sagt")
say(meld["kuchen"])

# --- PDF ---------------------------------------------------------------------------------------------------------------------------------
summary = [f"Stationen: {settings.n}, mittlerer Bedarf {settings.mu} Personentage je Station und Tag, Kapazität {round(100 * settings.r)} % des Bedarfs, "
           f"Verteilung {C.DIST_LABELS[settings.dist]}, Struktur {C.STRUCT_LABELS[settings.struct]}, Wirkungsgrad {C.EFF_LABELS[settings.eff]}, "
           f"Anteil geschult {round(100 * settings.q)} %, Zufalls-Seed {settings.seed}. {E.thou(s1['N'])} Szenarien.",
           f"Gewinn voller Flexibilität: {E.de(s1['gewinn_pt'], 2)} Personentage je Tag, {E.de(s1['gewinn_punkte'], 2)} Servicegrad-Punkte. Alle Parameter sind erfunden."]
pdf_rows = [["Entwurf", "Bögen", "Anteil %", "+/- 2 SE", "Servicegrad %", "Unterdeckung"]] + [
    [f"{r['Kürzel']} {r['Entwurf']}", r["Bögen"], E.de(r["Anteil %"]), E.de(r["± 2 SE"], 2), E.de(r["Servicegrad %"], 2), E.de(r["Unterdeckung (PT/Tag)"], 2)] for r in rows]
st.download_button("📄 Auswertung als PDF herunterladen",
                   data=generate_pdf("Kreuzschulung: wen anlernen?", summary, pdf_rows, [m["text"] for m in meld.values()],
                                     ["Beispielwerte, keine Prognose für Ihren Betrieb. Ein Tag, Fluid-Modell, kein Preis der Schulung."]),
                   file_name="kreuzschulung.pdf", mime="application/pdf", key="pdf_download")

# --- Wer macht was --------------------------------------------------------------------------------------------------------------------
with st.expander("🧭 Die Entwürfe: wer macht was?", expanded=True):
    st.markdown("Kürzel und Namen der Seite und der Messreihe. Die Spalten rechts zeigen, was der Entwurf in dieser Einstellung ist und holt; die Beispielspur nennt die "
                "ersten drei Gruppen und ihre Stationen.")
    erklaer = []
    for key, name, was, zahl in C.ENTWURF_TABELLE:
        z_ = d.get(key)
        if key == "O":
            if settings.n == 4 and settings.imb is None and settings.g >= 1.0:
                z_ = _bester_n4(settings)
            else:
                z_ = None
        spur = ""
        if z_ is not None and "masken" in z_:
            spur = "; ".join(f"Gruppe {j + 1}: " + ", ".join(str(i + 1) for i in DS.stationen_in(z_["masken"][j], settings.n)) for j in range(min(3, settings.n)))
        erklaer.append({"Kürzel": key, "Name": name, "Was es ist": was, "Bögen": zahl, "hier": "–" if z_ is None else str(z_["bogen"]),
                        "Anteil % (hier)": None if (z_ is None or z_["anteil"] is None or not zeigen) else round(E.pct(z_["anteil"]), 1), "Beispielspur": spur or "–"})
    st.dataframe(pd.DataFrame(erklaer), width="stretch", hide_index=True)
    st.caption("O (bester Entwurf) ist kein Verfahren zum Einsatz, sondern ein Test der Regel „Ring“: n = 4 live, n = 6 vorgerechnet, nicht gerechnet bei Ungleichgewicht und für n ≥ 8.")

# --- Kernabschnitt: Messreihe ---------------------------------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📐 Was die Messreihe zeigt")
res_meta = R.load()["meta"]
cov = R.load_coverage()
st.caption(f"Vorgerechnet (tools/build_results.py aus der Vorab-Messreihe, {res_meta['zellen']} Zellen, {R.aussagen_messreihe()['zellen']} verschiedene Reglerkombinationen, "
           f"{E.thou(C.N_SZENARIEN)} gepaarte Szenarien je Zelle, {E.thou(round(res_meta['sekunden_summe']))} s Rechenzeit) und die Abdeckung aller {E.thou(C.N_KOMBINATIONEN)} "
           "Kombinationen (tools/sweep_coverage.py, derselbe Live-Pfad wie oben); nichts davon wird im Browser gerechnet.")
az = R.aussagen_messreihe()
zusf = R.abdeckung_zusammenfassung() if cov is not None else None
tab_rows = []
for a, text in R.AUSSAGEN.items():
    row = {"Aussage": f"{a}: {text}"}
    for lab, cnt in (("Messpunkte", az["zaehlung"][a]),) + ((("alle Kombinationen", zusf["alle"][a]), ("nicht gemessene", zusf["ungemessen"][a])) if zusf else ()):
        row[lab] = " / ".join(f"{cnt.get(k, 0)} {k}" for k in ("gilt", "gilt nicht", "unklar", "n/a") if cnt.get(k, 0))
    tab_rows.append(row)
st.dataframe(pd.DataFrame(tab_rows), width="stretch", hide_index=True)
st.caption("Je Aussage die Zahl der Kombinationen, in denen sie gilt (zwei Standardfehler Abstand zur Schwelle), nicht gilt oder unklar bleibt. „n/a“: Paare gibt es nur bei "
           "geradem n ≥ 4, der Zufall erst ab n = 3. Der Hook „der Ring holt praktisch alles“ gilt auf der glatten Fläche (Poisson, mittlerer Bedarf ≥ 20, Wirkungsgrad 100 %, "
           "kein Ungleichgewicht), sonst ist er die Ausnahme.")

grp_rows = []
for g in R.GRUPPEN_REIHENFOLGE:
    z_, u_ = az["gruppen"].get(g, [0, 0])
    grp_rows.append({"Gruppe von Messpunkten": g, "Zellen": z_, "Ring unter 95 %": u_, "Ring ≥ 95 %": z_ - u_})
grp_rows.append({"Gruppe von Messpunkten": "alle", "Zellen": az["zellen"], "Ring unter 95 %": sum(v[1] for v in az["gruppen"].values()),
                 "Ring ≥ 95 %": az["zellen"] - sum(v[1] for v in az["gruppen"].values())})
g1, g2 = st.columns(2)
with g1:
    st.markdown("**Wo der Ring reicht** (Messpunkte)")
    st.dataframe(pd.DataFrame(grp_rows), width="stretch", hide_index=True)
with g2:
    st.markdown("**Die Gegenfälle** (Anteil am Nutzen, Messreihe)")
    faelle = []
    for lab, kw in (("Basis n = 6", dict(n=6, mu=20)), ("Block ±50 %, n = 12", dict(n=12, mu=20, imb=("block", 0.5))),
                    ("abwechselnd ±50 %, n = 12", dict(n=12, mu=20, imb=("alt", 0.5))), ("Block ±50 %, n = 6", dict(n=6, mu=20, imb=("block", 0.5))),
                    ("k = 4, n = 12", dict(n=12, mu=20, disp=4)), ("k = 4, n = 6", dict(n=6, mu=20, disp=4)),
                    ("Wirkungsgrad 80 %, n = 12", dict(n=12, mu=20, g=0.8)), ("mittlerer Bedarf 5, n = 12", dict(n=12, mu=5)), ("n = 3", dict(n=3, mu=20))):
        c_ = R.cell(**kw)
        if c_ is None:
            continue
        faelle.append((lab, {"D1": R.ring(c_), "D2": R.ring2(c_), "P": R.anteil(c_, "P"), "R": R.zufall_mittel(c_, "R")}))
    st.plotly_chart(V.build_gegenfaelle(faelle), width="stretch", key="mess_gegenfaelle")
    st.caption("Je Fall Ring, Ring mit 2, Paare und Mittel der Zufallsziehungen. Bei „Block ±50 %, n = 12“ liegt der Zufall über dem Ring, bei „abwechselnd“ darunter.")

st.markdown("**Die Abdeckung: Ring-Anteil über Verteilung und Struktur** (für die gewählte Zahl der Stationen, mittleren Bedarf, Kapazität und Wirkungsgrad; ● = Messpunkt)")
if cov is None:
    st.info("Die Abdeckungsrechnung liegt nicht vor.")
else:
    st.plotly_chart(V.build_abdeckung_karte(cov["rows"], settings.n, settings.mu, settings.r, settings.eff, R.messpunkte()), width="stretch",
                    key=f"cov_{settings.n}_{settings.mu}_{settings.r}_{settings.eff}")

nr = []
for n_ in (4, 6, 8, 12):
    c_ = R.cell(n_, 20)
    nr.append({"n": n_, "Ring %": round(R.ring(c_), 1), "Paare %": round(R.anteil(c_, "P"), 1), "Näherung Paare %": round(100 * (1 - 2 ** -0.5) / (1 - n_ ** -0.5), 1),
               "Zufall (Mittel) %": round(R.zufall_mittel(c_, "R"), 1), "eine je Gruppe %": round(R.zufall_mittel(c_, "R1"), 1),
               "Gewinn F (Punkte)": round(R.gewinn_punkte(c_), 2), "Gewinn F (PT/Tag)": round(R.gewinn_pt(c_), 2)})
st.markdown("**Die Zahl der Stationen** (Poisson, mittlerer Bedarf 20, Kapazität gleich Bedarf)")
st.dataframe(pd.DataFrame(nr), width="stretch", hide_index=True)
st.caption("Paare folgen dem Wurzelgesetz (1 − 1/√2)/(1 − 1/√n) mit dem Grenzwert 29,3 %: Pooling von 2 statt n Stationen.")

ex = R.extras()
ent = pd.DataFrame([{"Bedarf": ("Poisson" if r_["disp"] is None else f"k = {r_['disp']}") + f", mittlerer Bedarf {r_['mu']}", "D1 ≠ D2 (Szenarien von 20.000)": r_["d1_d2"],
                     "D2 ≠ D3": r_["d2_d3"]} for r_ in ex["entartung"]])
v1, v2 = st.columns(2)
with v1:
    st.markdown("**Poisson ist für den Ring entartet** (n = 6)")
    st.dataframe(ent, width="stretch", hide_index=True)
    st.caption("Ein zusätzlicher Bogen ändert den Min-Schnitt nur, wenn ein Block aus k benachbarten Stationen mehr als (k + 1) mal die Kapazität zieht; bei Poisson "
               "ist das selten. Das ist das Ergebnis, kein Fehler: „der zweite Bogen bringt nichts“ gilt dort, nicht allgemein.")
with v2:
    st.markdown("**Derselbe Block-Fall, andere Reihenfolge** (Ring und Paare, Anteil %)")
    vs = pd.DataFrame([{"Fall": f"{C.STRUCT_LABELS[r_['struct']]}, n = {r_['n']}", "Ring in Stationsreihenfolge": round(100 * r_["ring_stationsreihenfolge"]["anteil"], 1),
                        "Ring heiß, kalt, heiß, kalt": round(100 * r_["ring"]["anteil"], 1), "Paare Nachbarn": round(100 * r_["paare_nachbarn"]["anteil"], 1),
                        "Paare heiß neben kalt": round(100 * r_["paare"]["anteil"], 1)} for r_ in ex["verschraenkt"]])
    st.dataframe(vs, width="stretch", hide_index=True)
    st.caption("Gleiche Zahl Bögen, andere Reihenfolge: Das ist die Umbenennung der Stationen des Falls „abwechselnd“ und deshalb kein Wunder, aber es macht „wen anlernen?“ "
               "zur Entscheidung. Ein Beleg für ein Optimum ist es nicht.")
st.caption(f"Rechenzeiten (dieses Gerät, gemessen): Messreihe {E.thou(round(res_meta['sekunden_summe']))} s für {res_meta['zellen']} Zellen; Live-Pfad Stufe 1 dieser Seite "
           f"{E.de(s1['sekunden'], 2)} s. Die Messreihe wird nie live gerechnet.")

# --- Methodenvergleich ----------------------------------------------------------------------------------------------------------------
st.markdown("---")
with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich", expanded=False):
    tabs = st.tabs(["🕸️ Graph und Beispieltag", "🧮 Min-Schnitt gegen Fluss", "🔍 Bester Entwurf (O)", "📊 Messreihe: diese Zelle"])
    verfuegbar = [k for k in ("D1", "A", "P", "D2", "D3", "C3", "C4", "C6", "R", "R1", "E", "F") if k in d]
    with tabs[0]:
        t1, t2, t3 = st.columns([2, 1, 1])
        with t1:
            wahl = st.selectbox("Entwurf im Graph (Anzeigewahl, keine Einstellung der Rechnung)", verfuegbar, key="kzs_graph_view",
                                format_func=lambda k: f"{k} {C.ENTWURF_KURZ[k]}")
        with t2:
            day = st.number_input("Beispieltag (Nr. des Szenarios)", *bounds("kzs_day_number"), key="kzs_day_number", step=1,
                                  help="Reine Anzeigewahl: welches der Szenarien als Beispieltag gezeigt wird (bei Wirkungsgrad 80 % gibt es nur 800, die Nummer wird modulo gerechnet).")
        with t3:
            st.write("")
            st.button("🎲 Anderer Tag", key="kzs_day_random", width="stretch", on_click=randomize_day)
        masken = d[wahl]["masken"]
        tg = _tag(settings, masken, int(day))
        gl, gr = st.columns([1, 1])
        with gl:
            st.plotly_chart(V.build_graph(settings.n, masken, settings.skala, tg["unterdeckung"], tg["fluss"], titel=f"{C.ENTWURF_KURZ[wahl]}, Tag {tg['tag']}"),
                            width="content", key=f"graph_tag_{settings.n}_{wahl}_{tg['tag']}_{settings.struct}_{settings.eff}_{settings.q}")
            st.caption("Rand rot und dick: Unterdeckung an dieser Station am Beispieltag; Pfeilstärke: Bogenfluss. Ab 40 Bögen steht eine Matrix statt der Pfeile.")
        with gr:
            tab = pd.DataFrame({"Station": [i + 1 for i in range(settings.n)], "Bedarf": tg["bedarf"], "Kapazität": tg["kapazitaet"], "bedient": tg["bedient"].round(2),
                                "Unterdeckung": tg["unterdeckung"].round(2)})
            st.dataframe(tab, width="stretch", hide_index=True)
            st.caption(f"Tag {tg['tag']} von {E.thou(tg['N'])}: Bedarf {E.de(tg['bedarf_summe'], 0)}, bedient {E.de(tg['wert'], 2)} Personentage. Die Unterdeckung je Station ist nur an "
                       "einem einzelnen Tag eindeutig (ein Max-Fluss), im Mittel nicht.")
    with tabs[1]:
        if tg["schnitt"] is None:
            st.info("Bei Wirkungsgrad 80 % gibt es keinen Min-Schnitt-Wert zum Vergleich: der verallgemeinerte Fluss ist ein lineares Programm.")
        else:
            gleich = abs(tg["schnitt"] - tg["wert"]) < 1e-2
            st.markdown(f"**Beispieltag {tg['tag']}, Entwurf {wahl}:** kritische Teilmenge T der Stationen = {{{', '.join(str(i + 1) for i in tg['T']) or '∅'}}}, "
                        f"Gruppen, die T berühren = {{{', '.join(str(j + 1) for j in tg['gruppen']) or '∅'}}}.")
            st.dataframe(pd.DataFrame([{"Rechenweg": "Min-Schnitt (gruppiert, abgeschlossene Teilmengen)", "bedienter Bedarf": round(tg["schnitt"], 3)},
                                       {"Rechenweg": "Max-Fluss (scipy, ganzzahlig mit Faktor 1.000)", "bedienter Bedarf": round(tg["wert"], 3)}]),
                         width="stretch", hide_index=True)
            (st.success if gleich else st.error)("Beide Werte sind gleich." if gleich else "Die Werte weichen ab: das wäre ein Fehler im Kern.")
            st.caption("Das ist die Gegenprobe des Kerns in der App selbst. Der Schnitt zählt Bedarf außerhalb von T und die Kapazität aller Gruppen, die T berühren. "
                       "Die Aufzählung aller 2^n Teilmengen und der gruppierte Schnitt weichen auf 20.000 Szenarien nicht ab (Test).")
    with tabs[2]:
        if settings.n == 4 and settings.imb is None and settings.g >= 1.0:
            o4 = _bester_n4(settings)
            st.markdown(f"**n = 4, live:** {o4['klassen']} Klassen von Mengen aus 4 Bögen bis auf Umbenennung (495 Mengen), Auswahl auf {E.thou(C.N_AUSWAHL)} eigenen "
                        f"Szenarien, Bewertung auf den {E.thou(s1['N'])} Szenarien der Einstellung: der Gewählte holt {E.de(E.pct(o4['anteil']))} %, "
                        f"{'er ist der Ring bis auf Umbenennung' if o4['ist_ring'] else 'er ist nicht der Ring'}.")
        else:
            st.info("Live gerechnet wird O nur bei n = 4, austauschbarem Bedarf (Struktur gleich) und Wirkungsgrad 100 %. Für n = 6 stehen die Ergebnisse der Messreihe unten.")
        o_cells = [c_ for k_, c_ in R.cells().items() if "O" in c_["entwuerfe"]]
        diffs = [100 * (c_["entwuerfe"]["O"]["anteil"] - c_["entwuerfe"]["ring1"]["anteil"]) for c_ in o_cells]
        ist_ring = sum(1 for c_ in o_cells if c_["entwuerfe"]["O"]["auswahl"]["ist_ring"])
        st.markdown(f"**Messreihe (vorgerechnet):** in {ist_ring} von {len(o_cells)} Zellen (n = 4 und n = 6) ist der beste Entwurf der Ring bis auf Umbenennung; "
                    f"O minus D1 liegt zwischen {E.de(min(diffs), 2)} und {E.de(max(diffs), 2)} Punkten (Auswahl- und Stichprobenrauschen). "
                    "Nicht gerechnet: O bei Ungleichgewicht (dort entfällt die Symmetrie) und für n ≥ 8. Der Ring ist die beste Struktur bei austauschbarem Bedarf, "
                    "belegt nur für n = 4 und 6; „heiß neben kalt“ ist eine Regel, kein Optimum.")
    with tabs[3]:
        cz = R.cell_fuer(settings)
        if cz is None:
            st.info("Diese Einstellung ist kein Messpunkt der Messreihe: keine Zelle zum Vergleich. Die nächstgelegenen Messpunkte zeigt die Abdeckung oben.")
        else:
            mr = []
            for k_ in ("D0", "A", "D1", "D2", "D3", "P", "C3", "C4", "C6", "F"):
                kk = {"D1": "ring1", "D2": "ring2", "D3": "ring3"}.get(k_, k_)
                v_ = cz["entwuerfe"].get(kk)
                live_ = d.get(k_)
                if v_ is None:
                    continue
                mr.append({"Entwurf": k_, "Messreihe Anteil %": None if v_["anteil"] is None else round(100 * v_["anteil"], 3),
                           "live Anteil %": None if (live_ is None or live_["anteil"] is None) else round(100 * live_["anteil"], 3),
                           "Messreihe Servicegrad %": round(100 * v_["sg"], 3), "live Servicegrad %": None if live_ is None else round(100 * live_["sg"], 3)})
            st.dataframe(pd.DataFrame(mr), width="stretch", hide_index=True)
            st.caption(f"Zelle der Messreihe: {E.thou(cz['meta']['N'])} Szenarien, Rechenzeit {E.de(cz['meta']['sekunden'], 1)} s. Bei Anteil geschult 100 % sind beide Spalten gleich "
                       "(Selbst-Reproduktion auf alle Zellen: Abweichung unter 1e-12).")

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        """
**Das Bild.** Stationen als Kreis, Gruppen mit ihrer Hauptstation, Pfeile für Zusatzqualifikationen. Am Tag fließt Kapazität von den Gruppen zu den Stationen, der Rest bleibt
liegen. Was sich bedienen lässt, bestimmt der Min-Schnitt: bedient = kleinster Wert über alle Teilmengen T der Stationen aus „Bedarf außerhalb von T plus Kapazität aller Gruppen,
die T berühren“. Die App rechnet nur die abgeschlossenen Teilmengen je Komponente (exakt, gegen die volle Aufzählung geprüft).

**Warum der Ring so gut ist.** Er verbindet alle Stationen zu einer Kette, über die Überlast bis zur nächsten freien Gruppe weitergereicht werden kann; Paare tauschen nur zu zweit
(Wurzelgesetz, Grenzwert 29 %), und die offene Kette hat am Ende eine Sackgasse: der schließende Bogen bringt allein gut ein Drittel des Nutzens.

**Warum „viel hilft viel“ nicht gilt.** Bei Poisson-Bedarf bringen D2 bis D4 nichts mehr (der Ring ist praktisch voll); erst Überstreuung, Wirkungsgrad unter 100 % und
strukturelle Schieflage machen zusätzliche Bögen wertvoll. Poisson ist für den Ring entartet: Das ist das Ergebnis, kein Fehler.

**Warum die Anordnung am Bedarf hängt.** Im Block-Fall hängen die heißen Stationen aneinander; der Ring bezieht freie Kapazität nur über einen einzigen Bogen aus dem kalten Teil.
Heiß neben kalt behebt es mit denselben Bögen.

**Was „Anteil am Nutzen“ heißt und nicht sagt.** Anteil = (Servicegrad des Entwurfs − Servicegrad von D0) / (Servicegrad von F − Servicegrad von D0). Er sagt nichts über die
absolute Größe und ist für F ≈ D0 instabil; deshalb steht der absolute Gewinn in Punkten und Personentagen daneben, und bei sehr kleinem Gewinn wird der Anteil nicht gezeigt.

**Was live läuft und was vorgerechnet ist.** Live: Bedarf, alle Entwürfe, Eigener Entwurf, Zufallsentwürfe, Teilkurve, Beispieltag (20.000 Szenarien; bei Wirkungsgrad 80 %
ein LP je Szenario mit 800 Szenarien wie die Messreihe). Vorgerechnet: die Messreihe (147 Zellen), O für n = 6 und die Abdeckung aller 2.700 Kombinationen.
**Die Zustände einer Einstellung:** gemessen, nicht gemessen, bedingt (siehe oben).
""",
    )

with st.expander("📐 Mathematische Formulierung"):
    # erklaerseite:lesehilfe:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/kreuzschulung-erklaert.json, nicht von Hand ändern)
    st.markdown(
        r"""
**Lesehilfe.** Gegeben sind die Stationen mit zufälligem Bedarf $D_i$, die Gruppen mit Kapazität $S_j$ und ihren Qualifikationen $Q_j$. Gesucht ist, wie viel Bedarf bedient wird und welchen Anteil am Nutzen voller Flexibilität ein Entwurf holt.

| Symbol | Bedeutung |
|---|---|
| $i$, $j$ | Station und Gruppe (Gruppe $j$ gehört zur Station $j$) |
| $n$ | Zahl der Stationen |
| $D_i$ | Bedarf der Station $i$ an einem Tag |
| $S_j$ | Kapazität der Gruppe $j$ |
| $Q_j$ | Menge der Stationen, für die Gruppe $j$ qualifiziert ist |
| $T$ | Teilmenge der Stationen (beim Min-Schnitt) |
| $\mathrm{bedient}(D)$ | größte Menge Bedarf, die bei gegebenem Bedarf bedient werden kann |
| $SG(E)$ | Servicegrad des Entwurfs $E$ (bedient geteilt durch Bedarf) |
| $D_0$, $F$ | Bezugspunkte: keine Zusatzqualifikation, volle Flexibilität |
| $\bar a$, $\bar b$ | mittlerer Gewinn an bedientem Bedarf: Entwurf gegenüber $D_0$ und $F$ gegenüber $D_0$ |
| $\mathbb{E}$ | Erwartungswert über die Szenarien |

[Schritt für Schritt erklärt, mit Herleitung und Literatur](https://sebastianhanisch.net/kreuzschulung-erklaert.html#fachleute)
        """
    )
    # erklaerseite:lesehilfe:end
    st.markdown("**Bedienung** (Gruppe j mit Kapazität $S_j$, Station i mit Bedarf $D_i$, Qualifikationsmenge $Q_j$):")
    st.markdown(r"""
$$\mathrm{bedient}(D) = \max \sum_{j,i} x_{ji} \quad \text{unter} \quad \sum_i x_{ji} \le S_j,\ \ \sum_j x_{ji} \le D_i,\ \ x_{ji} = 0 \text{ für } i \notin Q_j$$

$$\mathrm{bedient}(D) = \min_{T} \Big[ \sum_{i \notin T} D_i + \sum_{j:\, Q_j \cap T \ne \emptyset} S_j \Big]$$
""")
    st.markdown("**Servicegrad, Anteil und Standardfehler** (Delta-Methode auf den Szenario-Paaren, $a = x - d_0$, $b = f - d_0$):")
    st.markdown(r"""
$$SG(E) = 1 - \frac{\mathbb{E}\,[\sum_i D_i - \mathrm{bedient}]}{\mathbb{E}\,[\sum_i D_i]}$$

$$\mathrm{Anteil}(E) = \frac{SG(E) - SG(D_0)}{SG(F) - SG(D_0)} = \frac{\bar a}{\bar b}$$

$$\mathrm{SE} = \frac{\sqrt{\operatorname{Var}(a - r\,b)/N}}{|\bar b|}, \quad r = \bar a / \bar b$$
""")
    st.markdown("**Teilqualifikation** (Anteil $q$ jeder Gruppe lernt die Zusatzstationen, $D_0$ und $F$ bleiben Bezugspunkte):")
    st.markdown(r"""
$$\mathrm{bedient}_q(D) = \sum_i \min\big(D_i,\ (1-q) S_i\big) + \mathrm{bedient}\big(Q,\ q S,\ (D - (1-q) S)^{+}\big)$$
""")
    st.markdown("**Wirkungsgrad** $g$ (Gruppe j auf Station $i \\ne j$ liefert $g$ je Einheit; $F$ in geschlossener Form):")
    st.markdown(r"""
$$\max \sum_{j,i} \gamma_{ji}\, x_{ji} \quad \text{unter} \quad \sum_i x_{ji} \le S_j,\ \ \sum_j \gamma_{ji}\, x_{ji} \le D_i, \qquad \gamma_{jj} = 1,\ \gamma_{ji} = g$$

$$F_g(D) = \sum_i \min(S_i, D_i) + \min\Big(g \sum_i (S_i - D_i)^{+},\ \sum_i (D_i - S_i)^{+}\Big)$$
""")
    st.markdown("**Überstreuung** (Gamma-Poisson, gemeinsame Schwankung $G_i = \\tfrac12 E_i + \\tfrac12 C$):")
    st.markdown(r"""
$$D_i \mid G_i \sim \mathrm{Poisson}(\mu\, G_i), \quad G_i \sim \mathrm{Gamma}(k,\ \text{Mittel } 1), \quad \operatorname{Var}(D_i) = \mu + \mu^2 / k$$
""")
    st.markdown("**Paare** (Näherung des Wurzelgesetzes, Pooling von 2 statt n Stationen):")
    st.markdown(r"""
$$\mathrm{Anteil}_P \approx \frac{1 - 1/\sqrt{2}}{1 - 1/\sqrt{n}}$$
""")

with st.expander("🚧 Wo die Annahmen enden"):
    st.markdown(
        """
| Annahme | Was sie ausblendet | Wer setzt an |
|---|---|---|
| Ein Tag, Fluid-Modell, teilbare Kapazität | Schichtlage, Zeit, Wochenmuster, Ganzzahligkeit der Zuordnung; das ist die Bedienung nach Realisierung des Bedarfs, nicht die Dienstplanung | [Schichtplanung](https://sebastianhanisch-shift-demo.streamlit.app/) (Überdeckung eines gegebenen Bedarfs); eine Verbindung von Qualifikation und Schichtlage ist nicht gebaut |
| Keine Warteschlange | Servicegrad je Stunde statt Tagesbilanz, Skill-based Routing | Multiskill-Warteschlange nicht gebaut |
| Kein Preis der Schulung | Lohnt es sich? Lernkurve, Auffrischung, Wechsel | nicht gebaut; die App nennt den Gewinn je Zusatzqualifikation in Personentagen |
| Symmetrischer, erfundener Bedarf | Wochentagsmuster, Prognosefehler, Saison; Ungleichgewicht nur als „Block“ und „abwechselnd“ | nicht gebaut |
| Ein Wirkungsgrad für alle Bögen | unterschiedlich gute Vertretung | nicht gebaut |
| Bedarf aus Poisson und Gamma-Poisson | Gleichverteilung, Mehrgipfligkeit | nicht gemessen |
| Gruppen statt Personen | namentliche Zuordnung, Ganzzahligkeit | nicht gebaut |
| Pooling immer voll | ob eine teilweise Verbindung reicht | hier; das volle Pooling zeigt die [M/M/c-Warteschlange](https://sebastianhanisch-mmc-queue-demo.streamlit.app/) |
""",
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Schichtplanung optimieren](https://sebastianhanisch.net/schichtplanung-optimierung.html)."
)
