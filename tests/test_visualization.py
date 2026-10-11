"""Plotly-Abbildungen: feste Achsen, feste Größen, Zahl der Pfeile, Matrix ab 40 Bögen, Rand bei Unterdeckung; PDF mit den Sonderzeichen."""

import pytest

import kzs_constants as C
import kzs_designs as DS
import kzs_pdf_export as PDF
import kzs_visualization as V


def fixed(fig):
    return all(ax.fixedrange is True for ax in (fig.layout.xaxis, fig.layout.yaxis))


def test_graph_has_one_arrow_per_arc_and_fixed_square_size():
    fig = V.build_graph(6, DS.ring(6, 1), [1.0] * 6)
    pfeile = [a for a in fig.layout.annotations if a.showarrow]
    assert len(pfeile) == 6
    assert fig.layout.width == fig.layout.height == V.GRAPH_SIZE
    assert fixed(fig)
    assert fig.layout.xaxis.range == fig.layout.yaxis.range == (-1.35, 1.35)


def test_graph_nodes_are_coloured_by_demand_and_marked_at_a_shortfall():
    skala = [1.5, 1.5, 1.5, 0.5, 0.5, 0.5]
    fig = V.build_graph(6, DS.ring(6, 0), skala, unterdeckung=[0, 3.0, 0, 0, 0, 0])
    knoten = [t for t in fig.data if t.mode == "markers+text"]
    assert [t.marker.color for t in knoten][:3] == [C.COLORS["heiss"]] * 3 and [t.marker.color for t in knoten][3:] == [C.COLORS["kalt"]] * 3
    breiten = [t.marker.line.width for t in knoten]
    assert breiten == [1, 4, 1, 1, 1, 1]
    assert knoten[1].marker.line.color == C.COLORS["unter"]
    assert not [a for a in fig.layout.annotations if a.showarrow]


def test_opposite_arcs_are_both_drawn_and_flow_scales_the_arrow_width():
    q = DS.eigener_entwurf(3, ((1,), (0,), ()))
    fluss = [[5.0, 4.0, 0], [0.0, 5.0, 0], [0, 0, 5.0]]
    fig = V.build_graph(3, q, None, fluss=fluss)
    pfeile = [a for a in fig.layout.annotations if a.showarrow]
    assert len(pfeile) == 2
    breiten = sorted(a.arrowwidth for a in pfeile)
    assert breiten[0] == pytest.approx(1.0) and breiten[1] == pytest.approx(4.0)


def test_many_arcs_switch_to_a_matrix():
    fig = V.build_graph(12, DS.voll(12), [1.0] * 12)
    assert fig.data[0].type == "heatmap" and fig.layout.width == V.GRAPH_SIZE
    z = fig.data[0].z
    assert sum(sum(r) for r in z) == 144 and all(z[i][i] == 1 for i in range(12))
    assert V.build_graph(12, DS.ring(12, 2), None).data[0].type == "scatter"       # 24 Bögen: Pfeile


def test_design_bar_chart_keys_and_fixed_axes():
    rows = [{"Kürzel": "D1", "Entwurf": "Ring", "Anteil %": 99.9, "± 2 SE": 0.1}, {"Kürzel": "P", "Entwurf": "Paare", "Anteil %": 49.9, "± 2 SE": 0.5},
            {"Kürzel": "R", "Entwurf": "Zufall", "Anteil %": 51.2, "± 2 SE": 0.6, "Mittel der Ziehungen %": 51.4, "Streuung (sd)": 8.6}]
    fig = V.build_designs_bar(rows)
    assert fixed(fig) and list(fig.data[0].x) == [99.9, 49.9, 51.2]
    assert len(fig.data) == 2 and fig.data[1].x[0] == 51.4
    assert fig.layout.xaxis.range[0] == 0
    leer = V.build_designs_bar([{"Kürzel": "D1", "Entwurf": "Ring", "Anteil %": None}])
    assert len(leer.layout.annotations) == 1


def test_training_curve_starts_at_the_origin_and_shows_the_goal_line():
    kurven = {"D1": [0.2, 0.4, 0.66, 0.83, 0.97, 0.998, 1.0], "P": [0.2, 0.33, 0.46, 0.49, 0.5, 0.5, 0.5]}
    fig = V.build_teil_kurve(kurven, q_aktuell=0.3)
    assert fixed(fig) and fig.data[0].x[0] == 0.0 and fig.data[0].y[0] == 0.0 and fig.data[0].x[-1] == 100.0
    assert len(fig.data) == 2 and any(abs(s.y0 - 80.0) < 1e-9 for s in fig.layout.shapes if s.type == "line")


def test_counter_case_and_coverage_charts_have_fixed_axes():
    fall = [("Basis", {"D1": 100.0, "D2": 100.0, "P": 49.9, "R": 51.4}), ("Block", {"D1": 37.3, "D2": 73.7, "P": 0.5, "R": 45.0})]
    assert fixed(V.build_gegenfaelle(fall))
    import kzs_results as R
    cov = R.load_coverage()
    fig = V.build_abdeckung_karte(cov["rows"], 6, 20, 1.0, 1.0, R.messpunkte())
    assert fixed(fig) and fig.data[0].type == "heatmap" and len(fig.data[0].z) == 5 and len(fig.data[0].z[0]) == 5
    assert fig.data[0].text[0][0].startswith("●")


def test_pdf_cleans_the_characters_that_crash_fpdf2():
    text = "Ring – Paare — Zufall ≥ 95 % → „Zufall“ ± 2 × 3 € −1 … ● ①"
    clean = PDF._clean(text)
    clean.encode("latin-1")
    assert "–" not in clean and "−" not in clean and "€" not in clean and "EUR" in clean


def test_pdf_is_generated_with_umlauts_and_special_characters():
    rows = [["Entwurf", "Bögen", "Anteil %"], ["D1 Ring", 6, "100,0"], ["P Paare", 6, "49,9"]]
    pdf = PDF.generate_pdf("Kreuzschulung: wen anlernen?", ["Zeile mit Umlauten: größer, Maß, über – und ≥ Zeichen"], rows,
                           ["Der Ring holt 100,0 % – das ist „fast alles“."] * 40, ["Beispielwerte, keine Prognose."])
    assert pdf[:5] == b"%PDF-" and len(pdf) > 1500
