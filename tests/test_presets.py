"""Permalink, Presets, Vorlagen und Einstellungen: Einrasten, unbekannte Werte, Schlüsselwörter, Wirkung jedes Presets."""

import pytest
import streamlit as st

import kzs_constants as C
import kzs_presets as SP
import kzs_stories as S
from kzs_pipeline import Settings


def spec(key):
    return SP.SETTING_SPECS[key]


def test_every_widget_key_has_a_unique_url_parameter():
    params = [s.url_param for s in SP.SETTING_SPECS.values()] + [SP.OWN_PARAM]
    assert len(params) == len(set(params))


def test_coerce_snaps_numbers_to_the_nearest_step_and_rejects_unknown_texts():
    assert SP._coerce(spec("kzs_n_select"), "6") == 6
    assert SP._coerce(spec("kzs_n_select"), "5") == 4          # Gleichstand zwischen 4 und 6: der kleinere
    assert SP._coerce(spec("kzs_n_select"), "100") == 12 and SP._coerce(spec("kzs_n_select"), "1") == 2
    assert SP._coerce(spec("kzs_mu_select"), "30") == 20
    assert SP._coerce(spec("kzs_cap_select"), "1.04") == 1.0 and SP._coerce(spec("kzs_cap_select"), "0") == 0.9
    assert SP._coerce(spec("kzs_eff_select"), "0.8") == 0.8 and SP._coerce(spec("kzs_eff_select"), "0.5") == 0.8
    assert SP._coerce(spec("kzs_q_select"), "0.3") == 0.3 and SP._coerce(spec("kzs_q_select"), "0.35") == 0.3
    assert SP._coerce(spec("kzs_dist_select"), "k4") == "k4" and SP._coerce(spec("kzs_dist_select"), "gauss") is None
    assert SP._coerce(spec("kzs_imb_select"), "block50") == "block50" and SP._coerce(spec("kzs_imb_select"), "x") is None
    assert SP._coerce(spec("kzs_cap_select"), "nan") is None
    with pytest.raises(ValueError):
        SP._coerce(spec("kzs_n_select"), "nan")


def test_coerce_clamps_integers_and_tolerates_str_and_list():
    assert SP._coerce(spec("kzs_seed_input"), "500") == C.SEED_MAX and SP._coerce(spec("kzs_seed_input"), "-3") == C.SEED_MIN
    assert SP._coerce(spec("kzs_seed_input"), ["7"]) == 7 and SP._coerce(spec("kzs_seed_input"), "7") == 7
    assert SP._coerce(spec("kzs_day_number"), "99999") == C.DAY_MAX
    with pytest.raises(ValueError):
        SP._coerce(spec("kzs_seed_input"), "abc")


def test_own_design_permalink_round_trip_and_invalid_values():
    auswahl = ((1, 2), (), (0,), (), (5,), (3, 4))
    text = SP.format_own(auswahl)
    assert text == "1.2--0--5-3.4"
    assert SP.parse_own(text, 6) == auswahl
    assert SP.parse_own([text], 6) == auswahl
    assert SP.parse_own(text, 4) is None                     # falsche Zahl Gruppen
    assert SP.parse_own("1-0-0-0", 3) is None                # eine Gruppe zu viel, alle Stationen gültig
    assert SP.parse_own("1-0", 3) is None                    # eine Gruppe zu wenig
    assert SP.parse_own("1-0-9", 3) is None                  # Station außerhalb
    assert SP.parse_own("0-0-0", 3) is None                  # eigene Station
    assert SP.parse_own("a-b-c", 3) is None
    assert SP.parse_own("1.1-0-0", 3) is None                # doppelt
    assert SP.parse_own("--", 3) == ((), (), ())


def test_settings_from_state_uses_keywords_and_types():
    values = {"kzs_n_select": 8, "kzs_mu_select": 50, "kzs_cap_select": 1.1, "kzs_dist_select": "k10", "kzs_imb_select": "alt25",
              "kzs_eff_select": 0.8, "kzs_q_select": 0.5, "kzs_seed_input": 17}
    s = SP.settings_from_state(values, own=((1,),) + ((),) * 7)
    assert s == Settings(n=8, mu=50, r=1.1, dist="k10", struct="alt25", eff=0.8, q=0.5, seed=17, own=((1,),) + ((),) * 7)
    assert s.disp == 10 and s.imb == ("alt", 0.25)


def test_preset_keys_cover_exactly_the_settings_fields_of_a_preset():
    assert set(SP.PRESET_KEYS) == set(S.PRESETS["Ring, Paare, Zufall"])


def test_apply_preset_writes_all_widget_keys_and_clears_the_own_design(monkeypatch):
    state = {"kzs_own_12_0": [3], "kzs_own_6_0": [1]}
    monkeypatch.setattr(st, "session_state", state)
    SP.apply_preset("Block-Ungleichgewicht")
    p = S.PRESETS["Block-Ungleichgewicht"]
    for key, wkey in SP.PRESET_KEYS.items():
        assert state[wkey] == p[key]
    assert state["kzs_day_number"] == S.PRESET_TAG["Block-Ungleichgewicht"]
    assert all(state[f"kzs_own_12_{j}"] == [] for j in range(12))


def test_template_callback_fills_the_multiselects_of_the_current_n(monkeypatch):
    state = {"kzs_n_select": 4, "kzs_imb_select": "gleich", "kzs_seed_input": 3}
    monkeypatch.setattr(st, "session_state", state)
    SP.apply_template("ring")
    assert [state[f"kzs_own_4_{j}"] for j in range(4)] == [[1], [2], [3], [0]]
    SP.apply_template("leer")
    assert all(state[f"kzs_own_4_{j}"] == [] for j in range(4))
    SP.apply_template("zufall")
    assert sum(len(state[f"kzs_own_4_{j}"]) for j in range(4)) == 4
    own = SP.own_from_state(4)
    assert sum(len(a) for a in own) == 4 and SP.own_key(4, 2) == "kzs_own_4_2"


def test_hot_next_to_cold_template_uses_the_current_structure(monkeypatch):
    state = {"kzs_n_select": 6, "kzs_imb_select": "block50", "kzs_seed_input": 3}
    monkeypatch.setattr(st, "session_state", state)
    SP.apply_template("heiss_kalt")
    sel = [state[f"kzs_own_6_{j}"] for j in range(6)]
    heiss = {0, 1, 2}
    for j, a in enumerate(sel):
        assert len(a) == 1 and ((j in heiss) != (a[0] in heiss))      # jede Gruppe verkettet heiß mit kalt


def test_random_draw_button_stays_in_bounds_and_counts(monkeypatch):
    state = {}
    monkeypatch.setattr(st, "session_state", state)
    seen = set()
    for _ in range(50):
        SP.randomize_seed()
        assert C.SEED_MIN <= state["kzs_seed_input"] <= C.SEED_MAX
        seen.add(state["kzs_seed_input"])
    assert state["kzs_draw_counter"] == 50 and len(seen) > 20
    SP.randomize_day()
    assert C.DAY_MIN <= state["kzs_day_number"] <= C.DAY_MAX


def test_own_from_state_ignores_foreign_values(monkeypatch):
    monkeypatch.setattr(st, "session_state", {"kzs_own_3_0": [1, 2], "kzs_own_3_1": [1, 7], "kzs_own_3_2": []})
    assert SP.own_from_state(3) == ((1, 2), (), ())
