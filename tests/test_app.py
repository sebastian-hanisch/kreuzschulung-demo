"""End-to-end-Tests über Streamlits AppTest: Seite lädt, jedes Preset, jeder Regler an Minimum und Maximum, Permalink (auch unbekannte Werte,
String und Liste), Eigener Entwurf mit Wechsel von n, Vorlagen, angezeigte Zahlen gegen die Rechnung mit denselben Reglerwerten, PDF."""

import os

import pytest
from streamlit.testing.v1 import AppTest

import kzs_constants as C
import kzs_evaluation as E
import kzs_pipeline as PL
import kzs_stories as S

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = 240


def fresh(query=None):
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    for k, v in (query or {}).items():
        at.query_params[k] = v
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def metric_values(at):
    return {m.label: m.value for m in at.metric}


def messages(at):
    return [x.value for x in list(at.success) + list(at.info) + list(at.warning)]


def qp(at, key):
    v = at.query_params[key]
    return v[0] if isinstance(v, list) else v        # ab Streamlit 1.65 str, vorher Liste


def widget(at, key):
    for coll in (at.select_slider, at.slider, at.number_input, at.multiselect, at.button, at.selectbox):
        for w in coll:
            if w.key == key:
                return w
    raise KeyError(key)


def test_app_loads_with_four_headline_numbers_the_sections_and_one_sidebar_header():
    at = fresh()
    assert at.title[0].value.startswith("🎓")
    vals = metric_values(at)
    assert set(vals) == {"Der Ring (D1) holt", "Servicegrad", "Zusatzqualifikationen (Bögen)", "Gewinn voller Flexibilität"}
    assert vals["Der Ring (D1) holt"] == "100,0 %" and vals["Gewinn voller Flexibilität"].startswith("6,29 PT")
    heads = [h.value for h in at.markdown if h.value.startswith("### ")]
    assert [h[:3] for h in heads].count("###") >= 6
    assert len(at.sidebar.header) == 1
    assert any("gemessen" in c.value for c in at.caption)
    assert len(at.get("download_button")) == 1
    bars = [b.label for b in at.button]
    assert all(f"preset_{n}" in [b.key for b in at.button] for n in S.PRESET_ORDER)
    assert bars


def test_displayed_numbers_come_from_the_sidebar_values_for_the_right_settings():
    """Vertauschte Reglerwerte wären still: die angezeigten Zahlen müssen der Rechnung mit denselben Werten entsprechen (Schlüsselwörter)."""
    q = {"n": "8", "mu": "50", "r": "1.1", "dist": "k10", "imb": "alt25", "eff": "1.0", "q": "0.5", "seed": "5"}
    at = fresh(q)
    s = PL.Settings(n=8, mu=50, r=1.1, dist="k10", struct="alt25", eff=1.0, q=0.5, seed=5)
    s1 = PL.stufe1(s)
    vals = metric_values(at)
    d = s1["designs"]["D1"]
    assert vals["Der Ring (D1) holt"] == f"{E.de(100 * d['anteil'])} %"
    assert vals["Gewinn voller Flexibilität"].startswith(f"{E.de(s1['gewinn_pt'], 2)} PT")
    assert vals["Zusatzqualifikationen (Bögen)"] == "8"


@pytest.mark.parametrize("name", S.PRESET_ORDER)
def test_every_preset_loads_without_exception_and_sets_the_controls(name):
    at = fresh()
    next(b for b in at.button if b.key == f"preset_{name}").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    p = S.PRESETS[name]
    assert at.session_state["kzs_n_select"] == p["n"] and at.session_state["kzs_dist_select"] == p["dist"]
    assert at.session_state["kzs_imb_select"] == p["struct"] and at.session_state["kzs_q_select"] == p["q"]
    assert at.session_state["kzs_seed_input"] == p["seed"] and at.session_state["kzs_day_number"] == S.PRESET_TAG[name]
    ring = PL.stufe1(S.preset_settings(name))["designs"]["D1"]["anteil"]
    assert metric_values(at)["Der Ring (D1) holt"] == f"{E.de(100 * ring)} %"


def test_every_control_at_its_extremes_does_not_raise_and_changes_the_numbers():
    base = metric_values(fresh())
    controls = {"kzs_n_select": C.N_OPTIONS, "kzs_mu_select": C.MU_OPTIONS, "kzs_cap_select": C.R_OPTIONS, "kzs_dist_select": C.DIST_ORDER,
                "kzs_imb_select": C.STRUCT_ORDER, "kzs_eff_select": C.EFF_OPTIONS, "kzs_q_select": C.Q_OPTIONS}
    for key, opts in controls.items():
        for value in (opts[0], opts[-1]):
            at = fresh()
            widget(at, key).set_value(value).run(timeout=TIMEOUT)
            assert not at.exception, (key, value, [str(e) for e in at.exception])
    for value in (C.SEED_MIN, C.SEED_MAX):
        at = fresh()
        widget(at, "kzs_seed_input").set_value(value).run(timeout=TIMEOUT)
        assert not at.exception
    for key, value in (("kzs_dist_select", "k4"), ("kzs_imb_select", "block50"), ("kzs_q_select", 0.1), ("kzs_eff_select", 0.8)):
        at = fresh()
        widget(at, key).set_value(value).run(timeout=TIMEOUT)
        assert metric_values(at) != base, key


def test_seed_changes_the_shown_random_draw_but_not_the_ring():
    at = fresh()
    zeilen0 = [d.value for d in at.dataframe][0]
    widget(at, "kzs_seed_input").set_value(4).run(timeout=TIMEOUT)
    assert not at.exception
    zeilen1 = [d.value for d in at.dataframe][0]
    r0 = float(zeilen0[zeilen0["Kürzel"] == "R"]["Anteil %"].iloc[0])
    r1 = float(zeilen1[zeilen1["Kürzel"] == "R"]["Anteil %"].iloc[0])
    assert r0 != r1
    assert float(zeilen0[zeilen0["Kürzel"] == "D1"]["Anteil %"].iloc[0]) == float(zeilen1[zeilen1["Kürzel"] == "D1"]["Anteil %"].iloc[0])


def test_permalink_writes_back_snaps_values_and_ignores_unknown_ones():
    at = fresh({"n": "5", "mu": "20", "dist": "gauss", "imb": "block50", "q": "0.31", "seed": "500", "eff": "0.8", "day": "7"})
    assert at.session_state["kzs_n_select"] == 4                  # eingerastet (Gleichstand: der kleinere)
    assert at.session_state["kzs_dist_select"] == C.DEFAULT_DIST    # unbekannt: Vorgabe
    assert at.session_state["kzs_imb_select"] == "block50" and at.session_state["kzs_q_select"] == 0.3
    assert at.session_state["kzs_seed_input"] == C.SEED_MAX and at.session_state["kzs_eff_select"] == 0.8
    assert at.session_state["kzs_day_number"] == 7
    assert qp(at, "n") == "4" and qp(at, "imb") == "block50" and qp(at, "seed") == str(C.SEED_MAX)


def test_permalink_tolerates_garbage():
    at = fresh({"n": "abc", "seed": "zzz", "q": "", "own": "x-y"})
    assert at.session_state["kzs_n_select"] == C.DEFAULT_N and at.session_state["kzs_seed_input"] == C.DEFAULT_SEED
    assert at.session_state["kzs_q_select"] == C.DEFAULT_Q


def test_own_design_from_the_address_is_applied_and_written_back():
    at = fresh({"n": "6", "own": "1-2-3-4-5-0"})
    assert metric_values(at)["Dein Entwurf holt"] == "100,0 %"
    assert metric_values(at)["Zusatzqualifikationen (Bögen)"] == "6"
    assert qp(at, "own") == "1-2-3-4-5-0"
    assert [list(widget(at, f"kzs_own_6_{j}").value) for j in range(6)] == [[1], [2], [3], [4], [5], [0]]
    assert any("Dein Entwurf" in m for m in messages(at))


def test_template_buttons_fill_the_own_design_and_changing_n_keeps_no_foreign_state():
    at = fresh()
    widget(at, "kzs_tpl_paare").click().run(timeout=TIMEOUT)
    assert not at.exception
    assert [list(widget(at, f"kzs_own_6_{j}").value) for j in range(6)] == [[1], [0], [3], [2], [5], [4]]
    assert metric_values(at)["Dein Entwurf holt"].endswith("%")
    widget(at, "kzs_n_select").set_value(12).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert all(widget(at, f"kzs_own_12_{j}").value == [] for j in range(12))
    assert "Der Ring (D1) holt" in metric_values(at)
    widget(at, "kzs_tpl_heiss_kalt").click().run(timeout=TIMEOUT)
    assert not at.exception
    widget(at, "kzs_imb_select").set_value("block50").run(timeout=TIMEOUT)
    widget(at, "kzs_tpl_heiss_kalt").click().run(timeout=TIMEOUT)
    assert metric_values(at)["Dein Entwurf holt"].startswith("98,")        # heiß neben kalt im Block-Fall


def test_templates_that_do_not_exist_for_the_setting_are_not_shown():
    at = fresh({"n": "3"})
    keys = [b.key for b in at.button]
    assert "kzs_tpl_paare" not in keys and "kzs_tpl_ring" in keys
    at = fresh({"n": "2"})
    assert "kzs_tpl_zufall" not in [b.key for b in at.button]


def test_every_template_runs_for_every_n():
    for n in C.N_OPTIONS:
        at = fresh({"n": str(n)})
        for name in ("ring", "kette", "zufall", "heiss_kalt", "paare", "leer"):
            k = f"kzs_tpl_{name}"
            if k in [b.key for b in at.button]:
                widget(at, k).click().run(timeout=TIMEOUT)
                assert not at.exception, (n, name, [str(e) for e in at.exception])


def test_pdf_download_and_the_explanation_table_are_on_the_page():
    at = fresh({"n": "4"})
    md = " ".join(m.value for m in at.markdown)
    assert "Mathematische Formulierung" in " ".join(e.label for e in at.expander)
    frames = [d.value for d in at.dataframe]
    assert any("Beispielspur" in df.columns and "Was es ist" in df.columns for df in frames)
    erkl = next(df for df in frames if "Beispielspur" in df.columns)
    assert set(erkl["Kürzel"]) >= {"D0", "D1", "P", "O", "F"}
    assert len(at.get("download_button")) == 1 and md


def test_the_three_states_of_a_setting_are_shown():
    assert any("gemessen" in c.value and "Messpunkt" in c.value for c in fresh().caption)
    assert any("nicht gemessen" in c.value for c in fresh({"n": "8", "dist": "k4", "mu": "50"}).caption)
    assert any("bedingt" in c.value for c in fresh({"n": "4", "q": "0.3"}).caption)


def test_example_day_tab_checks_min_cut_against_max_flow_in_the_app():
    at = fresh({"n": "6", "imb": "block50", "day": "17260"})
    assert any(s.value == "Beide Werte sind gleich." for s in at.success)
    at = fresh({"n": "6", "eff": "0.8"})
    assert any("kein Min-Schnitt" in i.value or "keinen Min-Schnitt" in i.value for i in at.info)


def test_slow_corner_shows_the_time_hint():
    at = fresh({"n": "12", "eff": "0.8"})
    assert any("⏱️" in c.value for c in at.caption)
