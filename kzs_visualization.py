"""Plotly-Abbildungen: Balken der Entwürfe, Graph (Knoten = Gruppen, Bögen = Zusatzqualifikationen), Kurve der Teilqualifikation,
Gegenfälle der Messreihe, Abdeckungskarte. Alle Achsen fest (fixedrange), feste Figurengrößen, Beschriftungen als Annotationen mit Hintergrund."""

import math

import plotly.graph_objects as go

import kzs_constants as C

GRAPH_SIZE = 300
MATRIX_AB = 40            # ab dieser Zahl Bögen zeigt der Graph eine Matrix statt Pfeile
BG = "rgba(255,255,255,0.88)"


def _fix(fig, height=None, margin=None):
    fig.update_layout(margin=margin or dict(l=10, r=10, t=30, b=10), height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(size=12), legend=dict(orientation="h", y=-0.2))
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _farbe(key):
    return {"D0": C.COLORS["neutral"], "F": C.COLORS["ref"], "D1": C.COLORS["ring"], "D2": C.COLORS["ring"], "D3": C.COLORS["ring"],
            "P": C.COLORS["paare"], "R": C.COLORS["zufall"], "R1": C.COLORS["zufall"], "E": C.COLORS["eigen"], "O": C.COLORS["ring"],
            "A": C.COLORS["kette"], "C3": C.COLORS["kette"], "C4": C.COLORS["kette"], "C6": C.COLORS["kette"]}.get(key, C.COLORS["neutral"])


def build_designs_bar(rows):
    """Anteil am Nutzen je Entwurf (Prozent) mit ± 2 Standardfehlern; bei Zufall zusätzlich das Mittel der Ziehungen (Raute, ± 1 Streuung)."""
    rows = [r for r in rows if r.get("Anteil %") is not None]
    fig = go.Figure()
    if not rows:
        fig.add_annotation(text="Anteil nicht gezeigt (Gewinn von F zu klein)", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return _fix(fig, height=160)
    labels = [f"{r['Kürzel']} {r['Entwurf']}" for r in rows]
    fig.add_trace(go.Bar(y=labels, x=[r["Anteil %"] for r in rows], orientation="h", marker_color=[_farbe(r["Kürzel"]) for r in rows],
                         error_x=dict(type="data", array=[r.get("± 2 SE") or 0.0 for r in rows], thickness=1.2, color="#444"),
                         text=[f"{r['Anteil %']:.1f}".replace(".", ",") + " %" for r in rows], textposition="outside", cliponaxis=False,
                         hovertemplate="%{y}: %{x:.1f} %<extra></extra>", name="Anteil (eine Ziehung)"))
    mean_rows = [r for r in rows if r.get("Mittel der Ziehungen %") is not None]
    if mean_rows:
        fig.add_trace(go.Scatter(y=[f"{r['Kürzel']} {r['Entwurf']}" for r in mean_rows], x=[r["Mittel der Ziehungen %"] for r in mean_rows], mode="markers",
                                 marker=dict(symbol="diamond", size=11, color="#111", line=dict(color="white", width=1)),
                                 error_x=dict(type="data", array=[r.get("Streuung (sd)") or 0.0 for r in mean_rows], thickness=1.2, color="#111"),
                                 name="Mittel der Ziehungen ± Streuung", hovertemplate="%{y}: Mittel %{x:.1f} %<extra></extra>"))
    fig.update_xaxes(range=[0, 118], title="Anteil am Nutzen voller Flexibilität (%)", fixedrange=True, gridcolor=C.COLORS["grid"], dtick=20)
    fig.update_yaxes(autorange="reversed", fixedrange=True)
    return _fix(fig, height=max(240, 34 * len(rows) + 80))


def _kreis(n, r=1.0):
    return [(r * math.sin(2 * math.pi * k / n), r * math.cos(2 * math.pi * k / n)) for k in range(n)]


def build_graph(n, masken, skala=None, unterdeckung=None, fluss=None, titel=""):
    """Graph des Entwurfs: Knoten j = Gruppe j mit ihrer Hauptstation j+1 auf einem Kreis, Pfeil j -> i = Gruppe j kann auch Station i+1.
    Knotenfarbe: mittlerer Bedarf zu Kapazität (heiß, neutral, kalt). Roter, dicker Rand: Unterdeckung an dieser Station (Beispieltag).
    fluss: optional Matrix (Gruppe, Station) mit dem Bogenfluss des Tages; Pfeilstärke ~ Fluss. Ab MATRIX_AB Bögen eine Matrix."""
    bogen = [(j, i) for j in range(n) for i in range(n) if i != j and (masken[j] >> i) & 1]
    if len(bogen) >= MATRIX_AB:
        return build_matrix(n, masken, titel)
    pos = _kreis(n)
    fig = go.Figure()
    rn = 0.12 if n <= 8 else 0.09
    fmax = max([fluss[j][i] for (j, i) in bogen]) if fluss is not None and bogen else 0.0
    for (j, i) in bogen:
        (x0, y0), (x1, y1) = pos[j], pos[i]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        gegen = ((masken[i] >> j) & 1) == 1
        off = 0.035 if gegen else 0.0           # Gegenbögen leicht versetzt, damit beide Richtungen sichtbar bleiben
        px, py = -uy * off, ux * off
        sx, sy = x0 + ux * rn + px, y0 + uy * rn + py
        ex, ey = x1 - ux * (rn + 0.02) + px, y1 - uy * (rn + 0.02) + py
        stark = fluss[j][i] if fluss is not None else 0.0
        breite = 1.2 if fluss is None else (1.0 + 3.0 * stark / fmax if fmax > 0 else 1.0)
        farbe = "#555" if (fluss is None or stark > 1e-9) else "#bbb"
        fig.add_annotation(x=ex, y=ey, ax=sx, ay=sy, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1.1,
                           arrowwidth=breite, arrowcolor=farbe, text="")
    for k, (x, y) in enumerate(pos):
        s = 1.0 if skala is None else skala[k]
        farbe = C.COLORS["heiss"] if s > 1.0 + 1e-9 else (C.COLORS["kalt"] if s < 1.0 - 1e-9 else C.COLORS["neutral"])
        unter = unterdeckung is not None and unterdeckung[k] > 1e-9
        fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text", text=[str(k + 1)], textfont=dict(color="white" if farbe != C.COLORS["neutral"] else "#222", size=13),
                                 marker=dict(size=34 if n <= 8 else 26, color=farbe, line=dict(color=C.COLORS["unter"] if unter else "#333", width=4 if unter else 1)),
                                 hovertemplate=f"Gruppe und Station {k + 1}<extra></extra>", showlegend=False))
    fig.add_trace(go.Scatter(x=[-1.35, 1.35], y=[-1.35, 1.35], mode="markers", marker=dict(opacity=0), hoverinfo="skip", showlegend=False))
    fig.update_xaxes(visible=False, range=[-1.35, 1.35], fixedrange=True)
    fig.update_yaxes(visible=False, range=[-1.35, 1.35], fixedrange=True)
    fig.update_layout(width=GRAPH_SIZE, height=GRAPH_SIZE, margin=dict(l=5, r=5, t=28, b=5), title=dict(text=titel, font=dict(size=13), x=0.5),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def build_matrix(n, masken, titel=""):
    """Matrix (Zeile Gruppe, Spalte Station) für Entwürfe mit vielen Bögen."""
    z = [[(1 if (masken[j] >> i) & 1 else 0) for i in range(n)] for j in range(n)]
    fig = go.Figure(go.Heatmap(z=z, x=[str(i + 1) for i in range(n)], y=[str(j + 1) for j in range(n)], colorscale=[[0, "#f4f4f4"], [1, C.COLORS["ring"]]],
                               showscale=False, xgap=2, ygap=2, hovertemplate="Gruppe %{y} kann Station %{x}: %{z}<extra></extra>"))
    fig.update_xaxes(title="Station", type="category", fixedrange=True, side="top")
    fig.update_yaxes(title="Gruppe", type="category", autorange="reversed", fixedrange=True)
    fig.update_layout(width=GRAPH_SIZE, height=GRAPH_SIZE, margin=dict(l=40, r=5, t=60, b=5), title=dict(text=titel, font=dict(size=13), x=0.5),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def build_teil_kurve(kurven, ziel=C.ZIEL_SCHULUNG, q_aktuell=None):
    """Anteil am Nutzen (Prozent) gegen den geschulten Anteil jeder Gruppe; kurven: {Kürzel: [Anteil je Stufe in Bruchteilen]}."""
    namen = {"D1": "Ring", "P": "Paare", "E": "Eigener Entwurf"}
    stile = {"D1": ("solid", C.COLORS["ring"]), "P": ("dash", C.COLORS["paare"]), "E": ("dot", C.COLORS["eigen"])}
    fig = go.Figure()
    xs = [0.0] + [100.0 * q for q in C.Q_OPTIONS]
    for key, vals in kurven.items():
        ys = [0.0] + [None if v is None else 100.0 * v for v in vals]
        dash, farbe = stile.get(key, ("solid", "#333"))
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=namen.get(key, key), line=dict(dash=dash, color=farbe, width=2.5),
                                 hovertemplate="%{x:.0f} % geschult: %{y:.1f} %<extra>" + namen.get(key, key) + "</extra>"))
    fig.add_hline(y=ziel, line=dict(dash="dot", color="#888", width=1))
    fig.add_annotation(x=100, y=ziel, text=f"{ziel:.0f} %", showarrow=False, xanchor="right", yanchor="bottom", bgcolor=BG)
    if q_aktuell is not None and q_aktuell < 1.0:
        fig.add_vline(x=100 * q_aktuell, line=dict(dash="dot", color="#bbb", width=1))
    fig.update_xaxes(range=[0, 101], title="Anteil jeder Gruppe, der die Zusatzstation lernt (%)", fixedrange=True, gridcolor=C.COLORS["grid"])
    fig.update_yaxes(range=[0, 104], title="Anteil am Nutzen (%)", fixedrange=True, gridcolor=C.COLORS["grid"])
    return _fix(fig, height=340)


def build_gegenfaelle(faelle):
    """Grafik der Gegenfälle: faelle = Liste (Beschriftung, {Kürzel: Prozent}); je Fall D1, D2, P und Zufall (Mittel)."""
    fig = go.Figure()
    namen = (("D1", "Ring", C.COLORS["ring"]), ("D2", "Ring mit 2", "#6baed6"), ("P", "Paare", C.COLORS["paare"]), ("R", "Zufall (Mittel)", C.COLORS["zufall"]))
    for key, name, farbe in namen:
        fig.add_trace(go.Bar(x=[f[0] for f in faelle], y=[f[1].get(key) for f in faelle], name=name, marker_color=farbe,
                             hovertemplate="%{x}: %{y:.1f} %<extra>" + name + "</extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(range=[0, 108], title="Anteil am Nutzen (%)", fixedrange=True, gridcolor=C.COLORS["grid"])
    fig.update_xaxes(tickangle=-30, fixedrange=True)
    return _fix(fig, height=400, margin=dict(l=10, r=10, t=30, b=110))


def build_abdeckung_karte(cov_rows, n, mu, r, eff, messpunkte):
    """Ring-Anteil (Prozent) über Verteilung (Spalten) und Struktur (Zeilen) für feste n, mu, r, Wirkungsgrad; Messpunkte mit ●."""
    import kzs_results as R
    z, text = [], []
    for st_ in C.STRUCT_ORDER:
        zr, tr = [], []
        for dist in C.DIST_ORDER:
            rec = cov_rows.get(R.abdeckung_schluessel(n, mu, r, dist, st_, eff))
            v = None if rec is None else R.abdeckung_ring(rec)
            zr.append(v)
            mark = "● " if (n, mu, r, dist, st_, eff) in messpunkte else ""
            tr.append("–" if v is None else mark + f"{v:.0f}".replace(".", ",") + " %")
        z.append(zr)
        text.append(tr)
    fig = go.Figure(go.Heatmap(z=z, x=[C.DIST_LABELS[d] for d in C.DIST_ORDER], y=[C.STRUCT_LABELS[s] for s in C.STRUCT_ORDER], text=text,
                               texttemplate="%{text}", zmin=30, zmax=100, colorscale="RdYlGn", showscale=False, xgap=2, ygap=2,
                               hovertemplate="%{y}, %{x}: %{z:.1f} %<extra></extra>"))
    fig.update_xaxes(fixedrange=True, side="top", tickangle=-20)
    fig.update_yaxes(fixedrange=True, autorange="reversed")
    return _fix(fig, height=330, margin=dict(l=10, r=10, t=90, b=10))
