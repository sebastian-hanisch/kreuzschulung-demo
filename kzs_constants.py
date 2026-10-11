"""Regler-Stufen, feste Annahmen, Schwellen, Beschriftungen und Farben (alle Regler mit festen Stufen: kein berechneter Bereich)."""

# --- Rechenumfang (die Szenarienzahlen der Vorab-Messreihe: nur so sind die Live-Zahlen dort nachschlagbar) -----------------------------
N_SZENARIEN = 20000          # Wirkungsgrad 100 %
N_SZENARIEN_LP = 800         # Wirkungsgrad < 100 %: ein LP je Szenario
N_AUSWAHL = 3000             # Auswahl des besten Entwurfs (O) auf eigenen Szenarien
AUSWAHL_BLOCK = 1000         # Block-Nummer des Auswahl-Stroms (Bewertung auf Block 0)
N_ZIEHUNGEN_KLEIN = 24       # Ziehungen der Zufallsentwürfe bei n <= 8
N_ZIEHUNGEN_GROSS = 12       # bei n = 12
N_ZIEHUNGEN_LP = 4           # bei Wirkungsgrad < 100 %

# --- Regler ---------------------------------------------------------------------------------------------------------------------------
N_OPTIONS = (2, 3, 4, 6, 8, 12)
MU_OPTIONS = (5, 20, 50)
R_OPTIONS = (0.9, 1.0, 1.1)
DIST_ORDER = ("poisson", "k10", "k10_korr", "k4", "k4_korr")
DIST_PARAMS = {"poisson": (None, 0.0), "k10": (10, 0.0), "k10_korr": (10, 0.5), "k4": (4, 0.0), "k4_korr": (4, 0.5)}
DIST_LABELS = {"poisson": "Poisson", "k10": "überstreut k = 10", "k10_korr": "k = 10, gemeinsame Schwankung",
               "k4": "stark überstreut k = 4", "k4_korr": "k = 4, gemeinsame Schwankung"}
STRUCT_ORDER = ("gleich", "block25", "block50", "alt25", "alt50")
STRUCT_PARAMS = {"gleich": None, "block25": ("block", 0.25), "block50": ("block", 0.5), "alt25": ("alt", 0.25), "alt50": ("alt", 0.5)}
STRUCT_LABELS = {"gleich": "gleich", "block25": "Block ±25 %", "block50": "Block ±50 %", "alt25": "abwechselnd ±25 %", "alt50": "abwechselnd ±50 %"}
EFF_OPTIONS = (1.0, 0.8)
EFF_LABELS = {1.0: "100 %", 0.8: "80 %"}
Q_OPTIONS = (0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0)
SEED_MIN, SEED_MAX = 0, 99
DAY_MIN, DAY_MAX = 0, N_SZENARIEN - 1

DEFAULT_N, DEFAULT_MU, DEFAULT_R = 6, 20, 1.0
DEFAULT_DIST, DEFAULT_STRUCT, DEFAULT_EFF, DEFAULT_Q = "poisson", "gleich", 1.0, 1.0
DEFAULT_SEED = 3
DEFAULT_DAY = 8815          # Beispieltag des Standard-Presets (Basiszelle), gefunden mit tools/seed_search.py

N_KOMBINATIONEN = (len(N_OPTIONS) * len(MU_OPTIONS) * len(R_OPTIONS) * len(DIST_ORDER) * len(STRUCT_ORDER) * len(EFF_OPTIONS))   # 2.700

# --- Schwellen der Meldungen (die 95 / 80 / 20 stammen aus den Gegenfällen der Messreihe: Ring-Anteile 37 bis 100 %) ---------------------
RING_HOCH = 95.0             # Ring holt praktisch alles
RING_MITTEL = 80.0
ABSTAND_PAARE = 20.0         # Ring minus Paare in Punkten
PAARE_MAX = 60.0
D2_ABSTAND = 5.0             # D2 mindestens so viel über dem Ring
ZIEL_SCHULUNG = 80.0         # Anteil am Nutzen, für den der geschulte Anteil gesucht wird
SCHULUNG_WENIG = 0.40        # bis zu diesem geschulten Anteil heißt es „es genügen X %“
KUCHEN_KLEIN = 3.0           # Gewinn von F in Servicegrad-Punkten
SE_FAKTOR = 2.0              # Vorzeichenkriterien gelten nur mit zwei Standardfehlern Abstand
GEWINN_MIN_ANTEIL = 0.5      # darunter (Punkte Servicegrad) wird der Anteil nicht gezeigt, nur der absolute Gewinn
ZEITHINWEIS_N = 12           # n = 12 mit Wirkungsgrad 80 % rechnet bis zu einigen Sekunden

# --- Farben (Plotly) -------------------------------------------------------------------------------------------------------------------
COLORS = {"ring": "#1f77b4", "paare": "#ff7f0e", "zufall": "#7f7f7f", "kette": "#9467bd", "eigen": "#d62728", "ref": "#2ca02c",
          "heiss": "#d95f02", "kalt": "#1f78b4", "neutral": "#bdbdbd", "unter": "#c0392b", "grid": "#e0e0e0"}

# --- Entwürfe: Kürzel, Name, Beschreibung -------------------------------------------------------------------------------------------
# (Schlüssel, Name, Was es ist, Zahl der Zusatzqualifikationen)
ENTWURF_TABELLE = (
    ("D0", "D0 dedicated", "Jede Gruppe kann nur ihre eigene Station.", "0"),
    ("A", "A offene Kette", "Gruppe j auch für Station j+1, die letzte nur ihre eigene.", "n − 1"),
    ("D1", "D1 Ring (lange Kette)", "Gruppe j auch für j+1, zyklisch geschlossen: alle Gruppen und Stationen hängen in einem Kreis.", "n"),
    ("D2", "D2 Ring mit 2", "Gruppe j auch für j+1 und j+2.", "2n"),
    ("D3", "D3 Ring mit 3", "Gruppe j auch für j+1, j+2 und j+3.", "3n"),
    ("P", "P Paare", "Disjunkte Zweiergruppen, die einander vertreten (gerades n ≥ 4).", "n"),
    ("C3", "C3 Dreierketten", "Geschlossene Ketten der Länge 3 (n durch 3 teilbar).", "n"),
    ("C4", "C4 Viererketten", "Geschlossene Ketten der Länge 4 (n durch 4 teilbar).", "n"),
    ("C6", "C6 Sechserketten", "Geschlossene Ketten der Länge 6 (n durch 6 teilbar).", "n"),
    ("R", "R Zufall", "n Zusatzqualifikationen gleichverteilt unter allen n(n − 1) möglichen; eine Ziehung (Zufalls-Seed), daneben das Mittel.", "n"),
    ("R1", "R1 Zufall je Gruppe", "Jede Gruppe genau eine zufällige Zusatzstation.", "n"),
    ("E", "E Eigener Entwurf", "Beliebige Zusatzstationen je Gruppe, Auswahl im Abschnitt „Eigenen Entwurf bauen“.", "frei"),
    ("O", "O bester Entwurf", "Beste Menge aus n Bögen nach vollständiger Aufzählung bis auf Umbenennung (n = 4 live, n = 6 vorgerechnet).", "n"),
    ("F", "F voll", "Jede Gruppe kann jede Station.", "n(n − 1)"),
)
ENTWURF_NAME = {k: name for k, name, _, _ in ENTWURF_TABELLE}
ENTWURF_KURZ = {"D0": "dedicated", "A": "Offene Kette", "D1": "Ring", "D2": "Ring mit 2", "D3": "Ring mit 3", "P": "Paare", "C3": "Dreierketten",
                "C4": "Viererketten", "C6": "Sechserketten", "R": "Zufall", "R1": "Zufall je Gruppe", "E": "Eigener Entwurf",
                "O": "Bester (Aufzählung)", "F": "Voll"}
ANZEIGE_REIHENFOLGE = ("D0", "A", "P", "C3", "C4", "C6", "R", "R1", "E", "D1", "D2", "D3", "O", "F")

SETTING_LABEL = {"n": "Zahl der Stationen", "mu": "Mittlerer Tagesbedarf", "r": "Kapazität im Verhältnis zum Bedarf"}
