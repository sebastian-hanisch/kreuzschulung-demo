"""Preset-Kriterien: an der Messreihe UND an der gezeigten Einstellung (Live-Rechnung), jedes Kriterium kippt einzeln an seiner Schwelle,
der Beispieltag zeigt, was die Geschichte sagt."""

import numpy as np
import pytest

import kzs_constants as C
import kzs_designs as DS
import kzs_flow as FL
import kzs_pipeline as PL
import kzs_results as R
import kzs_stories as S


def test_five_presets_each_with_help_criteria_and_known_options():
    assert len(S.PRESET_ORDER) == 5 and set(S.PRESETS) == set(S.PRESET_ORDER) == set(S.PRESET_HELP) == set(S.CRITERIA) == set(S.PRESET_TAG)
    keys = {"n", "mu", "r", "dist", "struct", "eff", "q", "seed"}
    for name in S.PRESET_ORDER:
        p = S.PRESETS[name]
        assert set(p) == keys
        assert p["n"] in C.N_OPTIONS and p["mu"] in C.MU_OPTIONS and p["r"] in C.R_OPTIONS and p["dist"] in C.DIST_ORDER
        assert p["struct"] in C.STRUCT_ORDER and p["eff"] in C.EFF_OPTIONS and p["q"] in C.Q_OPTIONS and C.SEED_MIN <= p["seed"] <= C.SEED_MAX
        assert S.PRESET_HELP[name]
        assert C.DAY_MIN <= S.PRESET_TAG[name] <= C.DAY_MAX
    assert S.PRESETS["Ring, Paare, Zufall"] == {"n": 6, "mu": 20, "r": 1.0, "dist": "poisson", "struct": "gleich", "eff": 1.0, "q": 1.0, "seed": C.DEFAULT_SEED}
    assert S.PRESET_TAG["Ring, Paare, Zufall"] == C.DEFAULT_DAY


def test_every_preset_sits_on_a_measured_cell_with_full_efficiency():
    for name in S.PRESET_ORDER:
        s = S.preset_settings(name)
        assert s.eff == 1.0 and R.ist_messpunkt(s), name
        assert R.zustand(s) == "gemessen", name


@pytest.mark.parametrize("name", S.PRESET_ORDER)
def test_criteria_hold_on_the_measurement_series(name):
    res = S.check(name, S.measured_facts(name))
    fehl = [(label, v) for label, ok, v in res if ok is False]
    assert not fehl, fehl
    assert sum(1 for _, ok, _ in res if ok) >= 5


@pytest.mark.parametrize("name", S.PRESET_ORDER)
def test_criteria_hold_on_the_shown_setting_live(name):
    res = S.check(name, S.instance_facts(name))
    fehl = [(label, v) for label, ok, v in res if ok is False]
    assert not fehl, fehl
    assert all(ok is not None for _, ok, _ in res)


@pytest.mark.parametrize("name", S.PRESET_ORDER)
def test_each_criterion_flips_exactly_at_its_threshold(name):
    for i, (label, key, op, thr) in enumerate(S.CRITERIA[name]):
        # alle Kriterien erfüllt: die Mitte des erlaubten Bereichs je Kennzahl
        alle = {}
        for _, k, o, t in S.CRITERIA[name]:
            alle.setdefault(k, []).append((o, t))
        facts = {}
        for k, regeln in alle.items():
            lo = max((t for o, t in regeln if o == ">="), default=-1e9)
            hi = min((t for o, t in regeln if o == "<="), default=1e9)
            facts[k] = (lo + hi) / 2 if lo > -1e9 and hi < 1e9 else (lo + 1.0 if lo > -1e9 else hi - 1.0)
        assert all(ok for _, ok, _ in S.check(name, facts)), name
        # genau dieses Kriterium an der Schwelle: erfüllt; knapp daneben: verletzt, die anderen mit derselben Kennzahl ausgenommen
        facts_a = dict(facts, **{key: thr})
        res_a = dict((l, ok) for l, ok, _ in S.check(name, facts_a))
        assert res_a[label] is True
        eps = 1e-6
        facts_b = dict(facts, **{key: thr - eps if op == ">=" else thr + eps})
        res_b = dict((l, ok) for l, ok, _ in S.check(name, facts_b))
        assert res_b[label] is False, (name, label)


def test_missing_figures_drop_the_criterion_instead_of_failing():
    res = S.check("Ring, Paare, Zufall", {"ring": 100.0})
    assert [ok for _, ok, _ in res][0] is True and all(ok is None for _, ok, _ in res[1:])


def test_the_example_day_shows_what_the_story_says():
    for name in S.PRESET_ORDER:
        s = S.preset_settings(name)
        D = PL.szenarien(s)
        t = S.PRESET_TAG[name]
        d = D[t:t + 1]
        S1 = s.S1
        n = s.n
        um = lambda q, a=1.0: float(d.sum() - FL.bedient(d, S1, q, a)[0])   # noqa: E731
        d0, ring, f = um(DS.ring(n, 0)), um(DS.ring(n, 1), s.q), um(DS.voll(n))
        assert d0 > 0 and f == pytest.approx(0.0, abs=1e-9), name
        if name == "Block-Ungleichgewicht":
            assert ring > 0.5 * d0
            assert um(DS.ring_in_reihenfolge(DS.heiss_neben_kalt(s.skala))) == pytest.approx(0.0, abs=1e-9)
        elif name == "Überstreuung":
            assert ring > 0 and um(DS.ring(n, 2)) == pytest.approx(0.0, abs=1e-9)
        else:
            assert ring == pytest.approx(0.0, abs=1e-9)
