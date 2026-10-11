"""SETTING_SPECS, Permalink (Begrenzen und Einrasten), Presets, Vorlagen des Selbstbaus und der Knopf „Neue Zufallsziehung“.

Alle Regler haben feste Stufen (select_slider mit Optionen): kein berechneter Bereich, kein min == max. Der Eigene Entwurf liegt je
Gruppe in einem Multiselect mit dem Schlüssel kzs_own_{n}_{j}; der Schlüssel enthält n, damit ein Wechsel von n keinen Zustand fremder
Optionen erbt. Zustand wird nur in Callbacks (Preset, Vorlage, Zufallsknopf) oder vor dem Zeichnen (Permalink, Standardwerte) gesetzt."""

from dataclasses import dataclass

import streamlit as st

import kzs_constants as C
import kzs_designs as DS
import kzs_stories as S
from kzs_demand import skala_aus
from kzs_pipeline import Settings
from kzs_rng import neuer_zufalls_seed


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: type
    default: object
    options: tuple | None = None
    lo: int | None = None
    hi: int | None = None


SETTING_SPECS = {
    "kzs_n_select": SettingSpec("n", int, C.DEFAULT_N, C.N_OPTIONS),
    "kzs_mu_select": SettingSpec("mu", int, C.DEFAULT_MU, C.MU_OPTIONS),
    "kzs_cap_select": SettingSpec("r", float, C.DEFAULT_R, C.R_OPTIONS),
    "kzs_dist_select": SettingSpec("dist", str, C.DEFAULT_DIST, C.DIST_ORDER),
    "kzs_imb_select": SettingSpec("imb", str, C.DEFAULT_STRUCT, C.STRUCT_ORDER),
    "kzs_eff_select": SettingSpec("eff", float, C.DEFAULT_EFF, C.EFF_OPTIONS),
    "kzs_q_select": SettingSpec("q", float, C.DEFAULT_Q, C.Q_OPTIONS),
    "kzs_seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, None, C.SEED_MIN, C.SEED_MAX),
    "kzs_day_number": SettingSpec("day", int, C.DEFAULT_DAY, None, C.DAY_MIN, C.DAY_MAX),
}
# Preset-Schlüssel -> Widget-Schlüssel (der Beispieltag ist reine Anzeigewahl und gehört nicht zum Preset)
PRESET_KEYS = {"n": "kzs_n_select", "mu": "kzs_mu_select", "r": "kzs_cap_select", "dist": "kzs_dist_select", "struct": "kzs_imb_select",
               "eff": "kzs_eff_select", "q": "kzs_q_select", "seed": "kzs_seed_input"}
OWN_PARAM = "own"


def own_key(n, j):
    return f"kzs_own_{n}_{j}"


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def _coerce(spec, raw):
    """Wert aus der Adresszeile: Zahlenoptionen rasten auf die nächste erlaubte Stufe ein, Texte nur, wenn bekannt (sonst None),
    ganze Zahlen werden auf Grenzen begrenzt."""
    if isinstance(raw, (list, tuple)):    # Streamlit liefert je nach Version str oder list
        raw = raw[0] if raw else ""
    value = spec.caster(raw)
    if spec.options is not None:
        if spec.caster is str:
            return value if value in spec.options else None
        if value != value:      # NaN
            return None
        return min(spec.options, key=lambda o: (abs(o - value), o))
    return int(max(spec.lo, min(spec.hi, value)))


def parse_own(raw, n):
    """Eigener Entwurf aus der Adresszeile: Gruppen mit „-“ getrennt, Stationen mit „.“ (z. B. 1-2.3-4-5-0-) ; ungültig: None."""
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else ""
    parts = str(raw).split("-")
    if len(parts) != n:
        return None
    out = []
    for j, p in enumerate(parts):
        sel = []
        for tok in (t for t in p.split(".") if t != ""):
            if not tok.isdigit():
                return None
            i = int(tok)
            if i >= n or i == j or i in sel:
                return None
            sel.append(i)
        out.append(tuple(sorted(sel)))
    return tuple(out)


def format_own(auswahl):
    return "-".join(".".join(str(i) for i in a) for a in auswahl)


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, auf zulässige Stufen eingerastet (Unbekanntes wird ignoriert)."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = _coerce(spec, qp[spec.url_param])
            except (ValueError, TypeError):
                continue
            if value is not None:
                st.session_state[state_key] = value
    n = st.session_state.get("kzs_n_select", C.DEFAULT_N)
    if OWN_PARAM in qp:
        own = parse_own(qp[OWN_PARAM], n)
        if own is not None:
            for j in range(n):
                st.session_state[own_key(n, j)] = list(own[j])
    st.session_state["permalink_loaded"] = True


def own_from_state(n):
    """Auswahl je Gruppe aus dem Zustand der Multiselects des aktuellen n (fehlt der Schlüssel: leer)."""
    out = []
    for j in range(n):
        v = st.session_state.get(own_key(n, j), [])
        out.append(tuple(sorted(int(i) for i in v if int(i) != j and 0 <= int(i) < n)))
    return tuple(out)


def sync_query_params(values, own=None):
    """`values`: {Widget-Schlüssel: aktueller Wert}; die Adresszeile spiegelt die Konfiguration (auch den Eigenen Entwurf)."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
        if own is not None and any(len(a) for a in own):
            st.query_params[OWN_PARAM] = format_own(own)
        elif OWN_PARAM in st.query_params:
            del st.query_params[OWN_PARAM]
    except Exception:
        pass


def _leere_auswahl(n):
    for j in range(n):
        st.session_state[own_key(n, j)] = []


def apply_preset(name):
    """Callback: Einstellungen des Presets, Eigener Entwurf leer, Beispieltag auf den Anfang."""
    p = S.PRESETS[name]
    for key, state_key in PRESET_KEYS.items():
        st.session_state[state_key] = p[key]
    st.session_state["kzs_day_number"] = S.PRESET_TAG.get(name, C.DEFAULT_DAY)
    _leere_auswahl(p["n"])


def apply_template(name):
    """Callback der Vorlagen-Knöpfe: füllt die Multiselects des aktuellen n (vor dem Zeichnen, daher kein Zustand ohne Widget)."""
    n = st.session_state.get("kzs_n_select", C.DEFAULT_N)
    struct = st.session_state.get("kzs_imb_select", C.DEFAULT_STRUCT)
    skala = skala_aus(n, C.STRUCT_PARAMS[struct])
    seed = st.session_state.get("kzs_seed_input", C.DEFAULT_SEED)
    zaehler = st.session_state.get("kzs_template_counter", 0) + 1
    st.session_state["kzs_template_counter"] = zaehler
    auswahl = DS.vorlage(name, n, skala, seed, zaehler)
    for j in range(n):
        st.session_state[own_key(n, j)] = list(auswahl[j])


def randomize_seed():
    """Callback: neuer Zufalls-Seed aus einem Zähler (SplitMix64, nicht random)."""
    zaehler = st.session_state.get("kzs_draw_counter", 0) + 1
    st.session_state["kzs_draw_counter"] = zaehler
    st.session_state["kzs_seed_input"] = neuer_zufalls_seed(zaehler, C.SEED_MAX)


def randomize_day():
    """Callback: anderer Beispieltag (SplitMix64 aus einem Zähler)."""
    zaehler = st.session_state.get("kzs_day_counter", 0) + 1
    st.session_state["kzs_day_counter"] = zaehler
    st.session_state["kzs_day_number"] = neuer_zufalls_seed(("tag", zaehler), C.DAY_MAX)


def settings_from_state(values, own=()):
    """Settings (immer mit Schlüsselwörtern) aus den Widget-Werten."""
    return Settings(n=int(values["kzs_n_select"]), mu=int(values["kzs_mu_select"]), r=float(values["kzs_cap_select"]),
                    dist=str(values["kzs_dist_select"]), struct=str(values["kzs_imb_select"]), eff=float(values["kzs_eff_select"]),
                    q=float(values["kzs_q_select"]), seed=int(values["kzs_seed_input"]), own=tuple(own))
