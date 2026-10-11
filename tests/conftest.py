"""Gemeinsame Fixtures: die Mini-Instanzen, an denen jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def kette3():
    """Drei Stationen A, B, C (0, 1, 2); Gruppe A kann A und B, B kann B und C, C nur C. Kapazität 10 je Gruppe.

    Handrechnung: Bedarf (0, 10, 10): A bedient B (10), B bedient C (10): bedient 20 (vollständig). Bedarf (30, 0, 0): nur A kann A: 10.
    Bedarf (0, 0, 30): B und C können C: 20. Bedarf (0, 30, 0): A und B können B: 20."""
    import kzs_designs as DS
    q = (DS.bits(0, 1), DS.bits(1, 2), DS.bits(2))
    D = np.array([[0.0, 10.0, 10.0], [30.0, 0.0, 0.0], [0.0, 0.0, 30.0], [0.0, 30.0, 0.0]])
    erwartet = np.array([20.0, 10.0, 20.0, 20.0])
    return q, np.full(3, 10.0), D, erwartet
