"""Anteil und Standardfehler (Delta-Methode) an einer Handrechnung; Streuung der Ziehungen."""

import math

import numpy as np
import pytest

import kzs_stats as ST


def test_anteil_and_standard_error_by_hand():
    d0 = np.array([0.0, 0.0, 0.0, 0.0])
    f = np.array([2.0, 2.0, 2.0, 2.0])
    x = np.array([1.0, 2.0, 1.0, 0.0])
    # a = x - d0 = (1, 2, 1, 0), b = 2: Mittel a = 1, Mittel b = 2, ratio 0,5; Residuum a - 0,5 b = (0, 1, 0, -1), Var (n-1) = 2/3
    anteil, se, mb = ST.stat_anteil(x, d0, f)
    assert anteil == pytest.approx(0.5) and mb == pytest.approx(2.0)
    assert se == pytest.approx(math.sqrt((2 / 3) / 4) / 2.0)


def test_anteil_of_the_reference_points_is_zero_and_one_with_zero_error():
    d0 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    f = d0 + np.array([1.0, 0.5, 2.0, 0.0, 1.0])
    assert ST.stat_anteil(d0, d0, f)[0] == pytest.approx(0.0)
    a, se, _ = ST.stat_anteil(f, d0, f)
    assert a == pytest.approx(1.0) and se == pytest.approx(0.0, abs=1e-12)


def test_anteil_is_undefined_when_full_flexibility_gains_nothing():
    d0 = np.array([1.0, 2.0, 3.0])
    assert ST.stat_anteil(d0 + 0.5, d0, d0) == (None, None, 0.0)


def test_kennzahlen_servicegrad_and_unterdeckung_by_hand():
    D = np.array([[10.0, 10.0], [20.0, 0.0]])
    served = np.array([15.0, 15.0])
    kz = ST.kennzahlen(served, D, np.array([10.0, 10.0]), np.array([20.0, 20.0]))
    assert kz["unterdeckung"] == pytest.approx(5.0)
    assert kz["sg"] == pytest.approx(1 - 5.0 / 20.0)
    assert kz["anteil"] == pytest.approx(0.5)


def test_streuung_ignores_none_and_uses_n_minus_1():
    s = ST.streuung([0.2, 0.4, None, 0.6])
    assert s["mittel"] == pytest.approx(0.4) and s["sd"] == pytest.approx(0.2) and s["min"] == 0.2 and s["max"] == 0.6 and s["ziehungen"] == 3
    assert ST.streuung([None])["mittel"] is None
    assert ST.streuung([0.3])["sd"] == 0.0
