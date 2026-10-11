"""Fehler-Einbau-Test: baut einzelne Fehler in die Rechenmodule ein und prüft, ob die Tests (ohne AppTests) sie finden.

Aufruf (Projektordner, Test-venv): python tools/mutation_check.py [Teilstring des Dateinamens] [--jobs N] [--indices 5,8-12] [--with-app] [--dry-run]
Jeder Mutant ersetzt genau eine Stelle in einer KOPIE des Projektordners (temporärer Ordner je Mutant, das Original bleibt unberührt);
PYTHONDONTWRITEBYTECODE=1, damit veralteter Bytecode keine Überlebenden vortäuscht; Quelltexte als LF. Vor den Mutanten läuft die unveränderte Kopie:
Ist sie nicht grün, bricht das Werkzeug ab. Ein Mutant kann in eine Endlosschleife laufen; nach TIMEOUT Sekunden gilt er als gefunden. Überlebende sind
entweder gleichwertig (kein sichtbarer Unterschied, dann mit Begründung als viertes Element des Eintrags markiert) oder eine Lücke der Tests.
`--with-app` nimmt die AppTests hinzu, `--dry-run` prüft nur, ob jede Zeichenkette genau einmal vorkommt."""
import concurrent.futures
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
WITH_APP = "--with-app" in sys.argv
TIMEOUT = 900
FIRST = ["test_rng.py", "test_demand.py", "test_designs.py", "test_stats.py", "test_flow.py", "test_oracle_kreuzschulung.py", "test_pipeline.py",
         "test_evaluation.py", "test_presets.py", "test_stories.py", "test_coverage.py", "test_claims.py", "test_visualization.py"]
SKIP = {"test_app.py", "test_footer.py"}   # AppTests (Streamlit) nur mit --with-app

# (Datei, alter Text, neuer Text[, Begründung, warum der Mutant gleichwertig ist])
MUTANTS = [
    # ---------------------------------------------------------------- kzs_rng.py
    ("kzs_rng.py", "        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64", "        z = ((z ^ (z >> 31)) * 0xBF58476D1CE4E5B9) & M64"),            # falsche Mischung
    ("kzs_rng.py", "        return lo + self.next() % (hi - lo + 1)", "        return lo + self.next() % (hi - lo)"),                          # Obergrenze nie erreicht
    ("kzs_rng.py", "    return ((z >> np.uint64(11)).astype(np.float64) + 0.5) / 9007199254740992.0", "    return ((z >> np.uint64(11)).astype(np.float64) + 0.0) / 9007199254740992.0"),   # vektorisiert: 0 möglich
    ("kzs_rng.py", "    return zlib.crc32(\"|\".join(str(t) for t in teile).encode(\"utf-8\"))", "    return zlib.crc32(\"\".join(str(t) for t in teile).encode(\"utf-8\"))"),   # Trenner fehlt
    ("kzs_rng.py", "    return SplitMix64(seed_aus(\"neue_ziehung\", zaehler)).randint(0, hi)", "    return SplitMix64(seed_aus(\"neue_ziehung\", zaehler)).randint(0, hi + 1)"),   # Zufallsknopf über die Grenze
    # ---------------------------------------------------------------- kzs_demand.py
    ("kzs_demand.py", "        p = p * rate / k\n", "        p = p * rate / (k + 1)\n"),                                                    # Poisson-Rekursion
    ("kzs_demand.py", "    return (-np.log(u)).sum(axis=1) / k0", "    return (-np.log(u)).sum(axis=1) / (k0 + 1)"),                                    # Gamma-Mittel
    ("kzs_demand.py", "            g[:, i] = (1.0 - korr) * e + korr * c", "            g[:, i] = (1.0 - korr) * e + c"),                                          # gemeinsamer Anteil zu groß
    ("kzs_demand.py", "        k0 = disp // 2\n", "        k0 = disp\n"),                                                                 # Form der Anteile
    ("kzs_demand.py", "(1.0 - delta if i >= n - n // 2 else 1.0)", "(1.0 - delta)"),                                                   # keine neutrale Station
    ("kzs_demand.py", "        s[n - 1] = 1.0", "        s[n - 1] = 1.0 + delta"),                                                       # Gesamtbedarf nicht ausgeglichen
    ("kzs_demand.py", "seed_aus(schluessel, n, mu, \"p\", block)", "seed_aus(schluessel, n, mu, \"p\", 0)"),                         # Block-Nummer ignoriert
    # ---------------------------------------------------------------- kzs_designs.py
    ("kzs_designs.py", "for t in range(k + 1)]) for j in range(n))", "for t in range(k)]) for j in range(n))"),                       # Ring mit k statt k + 1
    ("kzs_designs.py", "        q.append(bits(j, b0 + ((j - b0 + 1) % laenge)))", "        q.append(bits(j, b0 + ((j - b0 + 2) % laenge)))"),   # Kette überspringt
    ("kzs_designs.py", "    return tuple(bits(j, j + 1) if j < n - 1 else bits(j) for j in range(n))", "    return tuple(bits(j, j + 1) if j < n else bits(j) for j in range(n))"),   # letzte Gruppe mit Bogen
    ("kzs_designs.py", "        if i >= j:\n            i += 1", "        if i > j:\n            i += 1"),                                # Zufall je Gruppe darf die eigene Station treffen
    ("kzs_designs.py", "            if 0 <= int(i) < n and int(i) != j:", "            if 0 <= int(i) < n or int(i) != j:"),                                 # ungültige Station zugelassen
    ("kzs_designs.py", "key=lambda i: (-skala[i], i))", "key=lambda i: (skala[i], i))"),                                               # kalt vor heiß
    ("kzs_designs.py", "        q[j] = bits(j, order[(k + 1) % n])", "        q[j] = bits(j, order[(k + 1) % (n - 1)])"),                                  # Ring nicht geschlossen
    ("kzs_designs.py", "        if n - 1 > k:\n", "        if n - 1 >= k:\n"),                                                           # D_{n-1} = F als eigene Zeile
    ("kzs_designs.py", "        return n % 2 == 0 and n >= 4", "        return n % 2 == 0"),                                                     # Paare bei n = 2
    # ---------------------------------------------------------------- kzs_flow.py
    ("kzs_flow.py", "            if ra != rb:\n                parent[ra] = rb", "            if ra == rb:\n                parent[ra] = rb"),                   # Komponenten nie verbunden
    ("kzs_flow.py", "            Tp |= ((serv[a] & ~G) == 0).astype(np.int64) << a", "            Tp |= ((serv[a] & G) == 0).astype(np.int64) << a"),    # „abgeschlossen“ ohne Anbieterbedingung
    ("kzs_flow.py", "        hit = ((tg[:, None] & qarr[None, gr]) != 0).astype(np.float64)", "        hit = ((tg[:, None] & qarr[None, gr]) == 0).astype(np.float64)"),   # berührende Gruppen invertiert
    ("kzs_flow.py", "        tot += (D[:, sts] @ notin.T + cap[None, :]).min(axis=1)", "        tot += (D[:, sts] @ notin.T + cap[None, :]).max(axis=1)"),   # Maximum statt Minimum
    ("kzs_flow.py", "        cap = hit @ S[gr]\n        tot +=", "        cap = hit.sum(axis=1)\n        tot +="),                                   # Kapazität ignoriert
    ("kzs_flow.py", "    tot = np.zeros(D.shape[0])\n    for sts, notin, gr, hit in struktur(tuple(q), n):", "    tot = np.zeros(D.shape[0]) + 1.0\n    for sts, notin, gr, hit in struktur(tuple(q), n):"),   # Komponentensumme mit Offset
    ("kzs_flow.py", "    return eigen + np.minimum(g * frei, offen)", "    return eigen + g * np.minimum(frei, offen)"),                                     # der Fehler der Planung
    ("kzs_flow.py", "    gew = np.array([1.0 if j == i else g for (j, i) in bogen])\n    ng = len(q)", "    gew = np.array([1.0 for (j, i) in bogen])\n    ng = len(q)"),   # Wirkungsgrad 1 für alle Bögen
    ("kzs_flow.py", "        u = (1.0 - anteil) * S1\n        basis = np.minimum(D, u).sum(1)", "        u = anteil * S1\n        basis = np.minimum(D, u).sum(1)"),   # q statt 1 - q für die Eigenkapazität
    ("kzs_flow.py", "        S2 = anteil * S1\n    else:\n        basis, D2, S2 = 0.0, D, S1", "        S2 = S1\n    else:\n        basis, D2, S2 = 0.0, D, S1"),   # geschulte Kapazität ohne q
    ("kzs_flow.py", "        basis = np.minimum(D, u).sum(1)\n        D2 = np.maximum(D - u, 0.0)", "        basis = np.minimum(D, u).sum(1)\n        D2 = D"),                           # Bedarf nicht um die Eigenkapazität gekürzt
    ("kzs_flow.py", "    d0 = np.minimum(D, S1).sum(1)\n    if g >= 1.0:", "    d0 = np.minimum(D, S1).max(1)\n    if g >= 1.0:"),     # D0 falsch
    ("kzs_flow.py", "        served = fluss.sum(axis=0)", "        served = fluss.sum(axis=1)"),                                                 # bedient je Station falsch summiert
    ("kzs_flow.py", "        T += [sts[a] for a in range(len(sts)) if notin[z, a] == 0.0]", "        T += [sts[a] for a in range(len(sts)) if notin[z, a] == 1.0]"),   # T und Komplement vertauscht
    # ---------------------------------------------------------------- kzs_stats.py
    ("kzs_stats.py", "    se = math.sqrt(float(resid.var(ddof=1)) / len(a)) / abs(mb)", "    se = math.sqrt(float(resid.var(ddof=0)) / len(a)) / abs(mb)"),   # Varianz ohne Bessel
    ("kzs_stats.py", "    resid = a - ratio * b", "    resid = a"),                                                                       # Delta-Methode ohne Residuum
    ("kzs_stats.py", "\"sd\": float(a.std(ddof=1)) if len(a) > 1 else 0.0", "\"sd\": float(a.std(ddof=0)) if len(a) > 1 else 0.0"),   # Streuung ohne Bessel
    # ---------------------------------------------------------------- kzs_pipeline.py
    ("kzs_pipeline.py", "        return self.r * self.mu\n", "        return self.mu\n"),                                                       # Kapazität ohne r
    ("kzs_pipeline.py", "return C.N_SZENARIEN if self.eff >= 1.0 else C.N_SZENARIEN_LP", "return C.N_SZENARIEN if self.eff > 1.0 else C.N_SZENARIEN_LP"),
    ("kzs_pipeline.py", "return C.N_ZIEHUNGEN_KLEIN if self.n <= 8 else C.N_ZIEHUNGEN_GROSS", "return C.N_ZIEHUNGEN_KLEIN if self.n < 8 else C.N_ZIEHUNGEN_GROSS"),
    ("kzs_pipeline.py", "\"gewinn_punkte\": 100.0 * (fk[\"sg\"] - d0k[\"sg\"])", "\"gewinn_punkte\": 100.0 * (d0k[\"sg\"] - fk[\"sg\"])"),   # Vorzeichen
    ("kzs_pipeline.py", "\"gewinn_pt\": d0k[\"unterdeckung\"] - fk[\"unterdeckung\"]", "\"gewinn_pt\": fk[\"unterdeckung\"] - d0k[\"unterdeckung\"]"),   # Vorzeichen
    ("kzs_pipeline.py", "            return q0 + (q1 - q0) * (ziel - a0) / (a1 - a0) if a1 > a0 else q1", "            return q0 + (ziel - a0) / (a1 - a0) if a1 > a0 else q1"),   # Interpolation
    ("kzs_pipeline.py", "|r=%s|g=%s|imb=%s|teil=%s\" % (n, mu, disp, korr, r, g, imb, teil)", "|r=%s|g=%s|imb=%s|teil=%s\" % (n, mu, disp, korr, g, r, imb, teil)"),   # Schlüssel vertauscht
    ("kzs_pipeline.py", "            for dr in range(s.n_ziehungen):", "            for dr in range(s.n_ziehungen - 1):"),                                  # eine Ziehung weniger
    ("kzs_pipeline.py", "    ents = {\"D1\": DS.ring(s.n, 1)}", "    ents = {\"D1\": DS.ring(s.n, 2)}"),                                                     # Kurve für den falschen Ring
    ("kzs_pipeline.py", "        if w > best_w + 1e-12:", "        if w < best_w - 1e-12:"),                                                    # schlechtester statt bester
    ("kzs_pipeline.py", "    d = int(tag) % D.shape[0]", "    d = int(tag) % 20000"),                                                        # Tag über die Szenarienzahl
    ("kzs_pipeline.py", "        w = FL.bedient(Dsel, s.S1, DS.aus_bogen(n, bogen), s.q, 1.0).mean()", "        w = FL.bedient(D, s.S1, DS.aus_bogen(n, bogen), s.q, 1.0).mean()"),   # Gewinnerfluch
    # ---------------------------------------------------------------- kzs_results.py
    ("kzs_results.py", "        if wert - C.SE_FAKTOR * s >= schwelle:", "        if wert >= schwelle:"),                                                         # ohne Standardfehler-Bedingung
    ("kzs_results.py", "    if s.q < 1.0 and kombi not in teil_kombinationen():", "    if s.q < 1.0 and kombi in teil_kombinationen():"),                             # Zustand „bedingt“ vertauscht
    ("kzs_results.py", "        out[\"A5\"] = \"gilt\" if r_mittel > d1 else \"gilt nicht\"", "        out[\"A5\"] = \"gilt\" if r_mittel < d1 else \"gilt nicht\""),               # Richtung A5
    ("kzs_results.py", "(100.0 if n <= 3 else None)", "(100.0 if n <= 2 else None)"),                                                   # D2 = F bei n = 3 fehlt
    ("kzs_results.py", "    return 100.0 * (c[\"entwuerfe\"][\"F\"][\"sg\"] - c[\"entwuerfe\"][\"D0\"][\"sg\"])", "    return 100.0 * (c[\"entwuerfe\"][\"D0\"][\"sg\"] - c[\"entwuerfe\"][\"F\"][\"sg\"])"),
    # ---------------------------------------------------------------- kzs_evaluation.py
    ("kzs_evaluation.py", "    if d1 - C.SE_FAKTOR * se1 >= C.RING_HOCH:", "    if d1 >= C.RING_HOCH:"),                                                   # Zustand 1 ohne Standardfehler
    ("kzs_evaluation.py", "    if d1 + C.SE_FAKTOR * se1 < C.RING_MITTEL:", "    if d1 < C.RING_MITTEL:"),                                                    # Zustand 3 ohne Standardfehler
    ("kzs_evaluation.py", "    if rm is not None and rm[0] > d1 + C.SE_FAKTOR * se1:", "    if rm is not None and rm[0] > d1:"),                                      # Zufall schlägt den Ring ohne Standardfehler
    ("kzs_evaluation.py", "    if d1 - pv - C.SE_FAKTOR * diff_se >= C.ABSTAND_PAARE:", "    if d1 - pv >= C.ABSTAND_PAARE:"),                                               # Abstand ohne Standardfehler
    ("kzs_evaluation.py", "    if q80 is not None and q80 <= C.SCHULUNG_WENIG + 1e-12:", "    if q80 is not None and q80 < C.SCHULUNG_WENIG:"),                                # Grenze 40 % exklusiv
    ("kzs_evaluation.py", "    if s.mu == 5 and s.n >= 8:", "    if s.mu == 5 and s.n >= 6:"),                                                     # kleiner Bedarf schon ab n = 6
    ("kzs_evaluation.py", "    if g < C.KUCHEN_KLEIN:", "    if g <= C.KUCHEN_KLEIN:"),                                                         # Grenze 3 Punkte
    ("kzs_evaluation.py", "    if s.eff < 1.0 and s.n >= C.ZEITHINWEIS_N:", "    if s.eff < 1.0 and s.n >= 8:"),                                                   # Zeithinweis zu früh
    ("kzs_evaluation.py", "        je = (s1[\"designs\"][\"D0\"][\"unterdeckung\"] - ring[\"unterdeckung\"]) / ring[\"bogen\"]", "        je = (s1[\"designs\"][\"D0\"][\"unterdeckung\"] - ring[\"unterdeckung\"]) / s.n",
     "Der Ring hat immer n Bögen (Zahl der Stationen), beide Nenner sind gleich"),
    # ---------------------------------------------------------------- kzs_stories.py
    ("kzs_stories.py", "        out.append((label, v >= thr if op == \">=\" else v <= thr, v))", "        out.append((label, v > thr if op == \">=\" else v < thr, v))"),               # Schwelle exklusiv
    # ---------------------------------------------------------------- kzs_presets.py
    ("kzs_presets.py", "        return min(spec.options, key=lambda o: (abs(o - value), o))", "        return min(spec.options, key=lambda o: (abs(o - value), -o))"),           # Gleichstand nach oben
    ("kzs_presets.py", "            if i >= n or i == j or i in sel:", "            if i >= n or i in sel:"),                                                   # eigene Station im Permalink
    ("kzs_presets.py", "    if len(parts) != n:\n        return None", "    if len(parts) < n:\n        return None"),                                       # zu viele Gruppen zugelassen
    ("kzs_presets.py", "    _leere_auswahl(p[\"n\"])", "    pass"),                                                                          # Preset lässt den Eigenen Entwurf stehen
    ("kzs_presets.py", "                    dist=str(values[\"kzs_dist_select\"]), struct=str(values[\"kzs_imb_select\"]), eff=float(values[\"kzs_eff_select\"]),\n                    q=float(values[\"kzs_q_select\"])",
     "                    dist=str(values[\"kzs_dist_select\"]), struct=str(values[\"kzs_imb_select\"]), eff=float(values[\"kzs_q_select\"]),\n                    q=float(values[\"kzs_eff_select\"])"),   # Regler vertauscht
]


def test_files(base: pathlib.Path):
    alle = sorted(p.name for p in (base / "tests").glob("test_*.py"))
    erste = [f for f in FIRST if f in alle]
    rest = [f for f in alle if f not in erste and (WITH_APP or f not in SKIP)]
    return ["tests/" + f for f in erste + rest]


def check_unique():
    bad = []
    for n, m in enumerate(MUTANTS, 1):
        text = (ROOT / m[0]).read_bytes().decode("utf-8").replace("\r\n", "\n")
        c = text.count(m[1])
        if c != 1:
            bad.append((n, m[0], m[1][:70], c))
    return bad


def run_tests(tmp: pathlib.Path):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([PY, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "-k", "not test_readme_has_no_placeholders_left", *test_files(tmp)],
                          cwd=tmp, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT)


def run_one(args):
    n, name, old, new, base = args
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"kzs_mut{n}_"))
    try:
        shutil.copytree(base, tmp, dirs_exist_ok=True)
        path = tmp / name
        original = path.read_bytes().decode("utf-8")
        path.write_bytes(original.replace(old, new).encode("utf-8"))
        try:
            r = run_tests(tmp)
            return n, name, old, new, r.returncode == 0, False
        except subprocess.TimeoutExpired:
            return n, name, old, new, False, True       # Endlosschleife oder zu langsam: gilt als gefunden
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def make_base() -> pathlib.Path:
    base = pathlib.Path(tempfile.mkdtemp(prefix="kzs_mut_base_"))
    for f in ROOT.glob("*.py"):
        (base / f.name).write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    shutil.copytree(ROOT / "tests", base / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "tools", base / "tools", ignore=shutil.ignore_patterns("__pycache__", "_coverage_teil.json"))
    shutil.copytree(ROOT / "data", base / "data")
    for extra in ("README.md", "requirements.txt", "requirements-dev.txt"):
        if (ROOT / extra).exists():
            shutil.copy(ROOT / extra, base / extra)
    if (ROOT / ".streamlit").exists():
        shutil.copytree(ROOT / ".streamlit", base / ".streamlit")
    for f in (base / "tests").glob("*.py"):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    return base


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows-Konsole (cp1252) vertrüge Umlaute sonst nicht
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = args[0] if args else ""
    jobs = 4
    if "--jobs" in sys.argv:
        jobs = min(6, int(sys.argv[sys.argv.index("--jobs") + 1]))
        only = "" if only == str(jobs) else only
    wanted = None
    if "--indices" in sys.argv:
        spec = sys.argv[sys.argv.index("--indices") + 1]
        only = "" if only == spec else only
        wanted = set()
        for part in spec.split(","):
            lo, _, hi = part.partition("-")
            wanted.update(range(int(lo), int(hi or lo) + 1))
    bad = check_unique()
    for b in bad:
        print("FEHLER (Stelle nicht eindeutig gefunden):", b)
    if "--dry-run" in sys.argv:
        print(f"{len(MUTANTS)} Mutanten, {len(bad)} Fehler in der Mutantenliste")
        return
    base = make_base()
    try:
        r = run_tests(base)
        if r.returncode != 0:
            print("Die unveränderte Kopie besteht die Tests nicht; Abbruch.\n" + r.stdout[-3000:])
            sys.exit(2)
        bad_ids = {b[0] for b in bad}
        work = [(n, m[0], m[1], m[2], base) for n, m in enumerate(MUTANTS, 1)
                if n not in bad_ids and (not only or only in m[0]) and (wanted is None or n in wanted)]
        survivors, equivalent, killed = [], [], 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            for n, name, old, new, survived, timeout in pool.map(run_one, work):
                reason = MUTANTS[n - 1][3] if len(MUTANTS[n - 1]) > 3 else ""
                if timeout:
                    print(f"[{n:3d}] Zeitüberschreitung (als gefunden gezählt)  {name}", flush=True)
                if survived and reason:
                    equivalent.append(n)
                    print(f"[{n:3d}] überlebt, gleichwertig  {name}: {old[:60]!r} -> {new[:60]!r}\n        Begründung: {reason}", flush=True)
                elif survived:
                    survivors.append(n)
                    print(f"[{n:3d}] ÜBERLEBT  {name}: {old[:70]!r} -> {new[:70]!r}", flush=True)
                else:
                    killed += 1
                    print(f"[{n:3d}] gefunden  {name}", flush=True)
        print(f"\n{killed} gefunden, {len(survivors)} überlebt (Lücken), {len(equivalent)} gleichwertig (begründet), {len(bad)} Fehler in der Mutantenliste")
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
