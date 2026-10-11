"""Generator: Referenzwerte, vektorisiert gleich skalar, Zufalls-Seeds über zlib.crc32, Zähler-Knopf."""

import zlib

import numpy as np

import kzs_rng as RNG


def test_splitmix64_matches_the_published_reference_values_for_seed_zero():
    g = RNG.SplitMix64(0)
    assert [g.next() for _ in range(3)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F]


def test_vectorised_uniforms_are_bit_identical_to_the_scalar_class():
    for seed in (0, 1, 12345, 2 ** 63 + 17, RNG.seed_aus("a", 1), RNG.seed_aus("sw", 6, 20, "p", 0)):
        g = RNG.SplitMix64(seed)
        skalar = np.array([g.uniform() for _ in range(300)])
        assert np.array_equal(skalar, RNG.uniformen(seed, 300))
        assert 0.0 < skalar.min() and skalar.max() < 1.0


def test_prefix_property_the_first_values_do_not_depend_on_the_count():
    assert np.array_equal(RNG.uniformen(5, 10), RNG.uniformen(5, 1000)[:10])


def test_seed_aus_is_crc32_of_the_joined_key_and_not_python_hash():
    assert RNG.seed_aus("R", 6, 3) == zlib.crc32(b"R|6|3")
    assert RNG.seed_aus("R", 6, 3) != RNG.seed_aus("R", 6, 4)
    assert RNG.seed_aus("a", 1) == RNG.seed_aus("a", 1)


def test_randint_bounds_are_inclusive_and_all_values_occur():
    g = RNG.SplitMix64(7)
    vals = {g.randint(2, 5) for _ in range(400)}
    assert vals == {2, 3, 4, 5}


def test_new_draw_button_is_deterministic_and_in_bounds():
    vals = [RNG.neuer_zufalls_seed(k, 99) for k in range(1, 200)]
    assert all(0 <= v <= 99 for v in vals)
    assert len(set(vals)) > 50
    assert vals == [RNG.neuer_zufalls_seed(k, 99) for k in range(1, 200)]
