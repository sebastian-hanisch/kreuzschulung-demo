"""Ganzzahliger Zufallsgenerator SplitMix64 und Zufalls-Seeds aus Schlüsseltexten (zlib.crc32, nie Python hash(), nie numpy-Ströme).

Der Generator ist zählerbasiert: Ausgabe k hängt nur von Zufalls-Seed + k * GAMMA ab. Deshalb ist die vektorisierte Fassung `uniformen`
bitgleich zur skalaren Klasse, und die Szenarien einer kleineren Zahl sind die ersten Zeilen der größeren."""

import zlib

import numpy as np

M64 = (1 << 64) - 1
GAMMA64 = 0x9E3779B97F4A7C15


class SplitMix64:
    """Skalarer Generator (Referenzwerte für den Zufalls-Seed 0: E220A8397B1DCDAF, 6E789E6AA1B965F4, 06C45D188009454F)."""

    def __init__(self, seed):
        self.s = seed & M64

    def next(self):
        self.s = (self.s + GAMMA64) & M64
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        return z ^ (z >> 31)

    def randint(self, lo, hi):
        """Ganze Zahl in [lo, hi] (beide Grenzen eingeschlossen)."""
        return lo + self.next() % (hi - lo + 1)

    def uniform(self):
        """Gleichverteilte Zahl in (0, 1), nie exakt 0 oder 1."""
        return ((self.next() >> 11) + 0.5) / 9007199254740992.0


def seed_aus(*teile):
    """Zufalls-Seed aus einem Schlüsseltext (zlib.crc32 über die mit | verbundenen Teile)."""
    return zlib.crc32("|".join(str(t) for t in teile).encode("utf-8"))


def uniformen(seed, anzahl):
    """Die ersten `anzahl` Werte von SplitMix64(seed).uniform(), vektorisiert; bitgleich zur skalaren Klasse."""
    k = np.arange(1, anzahl + 1, dtype=np.uint64)
    z = np.uint64(seed & M64) + k * np.uint64(GAMMA64)
    z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    z = z ^ (z >> np.uint64(31))
    return ((z >> np.uint64(11)).astype(np.float64) + 0.5) / 9007199254740992.0


def neuer_zufalls_seed(zaehler, hi=99):
    """Nächster Zufalls-Seed des Knopfs „Neue Zufallsziehung“: SplitMix64 aus einem Zähler (nicht random), Wert in [0, hi]."""
    return SplitMix64(seed_aus("neue_ziehung", zaehler)).randint(0, hi)
