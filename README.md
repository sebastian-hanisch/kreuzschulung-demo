# Kreuzschulung: wen anlernen? – Streamlit-Demo

<!-- TODO nach dem Deploy: direkt hierher den Live-Link setzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-kreuzschulung-demo.streamlit.app/)** -->

Fall-Demo für die Website „Sebastian Hanisch – Operations Research und Machine Learning“ (Gruppe Personaleinsatzplanung, Themenseite Schichtplanung). Vehikel: ein Lager
mit Zonen (Wareneingang, Kommissionierung, Verpackung, Versand und weitere), je Zone eine Gruppe mit der Hauptqualifikation. Der Tagesbedarf je Zone ist zufällig; wer einer
Gruppe eine Zusatzzone beibringt, kann Überlast an einer Stelle mit Leerlauf an einer anderen ausgleichen. In der App und hier heißen die Zonen **Stationen**.

Die Demo misst, wie viel vom **Nutzen voller Flexibilität** eine Verkettung holt, dass bei gleicher Zahl Zusatzqualifikationen die **Anordnung** entscheidet, **wann auch der
Ring nicht reicht** und **wie viele Mitarbeitende** überhaupt lernen müssen. Live auf 20.000 gepaarten Szenarien, dazu die vorgerechnete Messreihe (147 Zellen) und die
Abdeckung aller 2.700 Reglerkombinationen.

## Warum dieses Problem

Wer jeder Gruppe eine Zusatzstation beibringt und die Stationen zum Ring schließt, holt bei gleichmäßig streuendem Bedarf (sechs Stationen, mittlerer Bedarf 20, Poisson) fast den
ganzen Nutzen voller Flexibilität; dieselben Qualifikationen als Paare oder zufällig verteilt die Hälfte; und liegt der Bedarf in Blöcken schief (zwölf Stationen, ±50 %), reicht
auch der Ring nicht. Das Ergebnis ist Lehrbuchwissen (Prozessflexibilität, „lange Kette“, siehe Literatur): Die Demo vermisst es an Poisson und Gamma-Poisson, sie entdeckt es nicht.
Der Hook ist die Anordnung, nicht die Zahl der Zusatzqualifikationen, und die interessante Fläche sind die Gegenfälle.

Sie schließt die Lücke, die `shift_demo` („keine Qualifikationen“) und `servicegrad-tag-demo` (Multiskill dort bewusst nicht umgesetzt) ausdrücklich lassen: Wer lernt welche
Zusatzstation, und wie viele müssen es sein?

## Befunde und Korrekturen gegenüber dem Plan

Die Vorab-Messreihe (2026-10-11, 147 Zellen) und der Detailplan sind die Grundlage; beim Bau wurde Folgendes anders oder neu:

- **Die Abdeckung hat die Planungs-Stichprobe korrigiert.** Der Plan nannte, der Ring hole auf 16 von 60 zufällig gezogenen ungemessenen Kombinationen mindestens 95 %. Alle 2.700
  Kombinationen gerechnet: In 1.039 der 2.562 ungemessenen Kombinationen gilt „Ring ≥ 95 %“ (40,6 %), in 1.125 von 2.700 insgesamt; die 60 Kombinationen der Vorschau stimmen
  mit der Abdeckung bis auf n = 3 mit Ungleichgewicht überein (siehe nächster Punkt), die Stichprobe lag also zufällig niedrig. Die Aussage bleibt: Der Hook gilt auf der glatten
  Fläche und ist sonst die Ausnahme, aber auf weniger als der Hälfte der Fläche, nicht auf einem Viertel.
- **Ungleichgewicht bei ungeradem n.** Die Messreihe hat nur gerade n (6 und 12). Bei n = 3 hätte die Vorschau der Planung den Gesamtbedarf geändert (Block: eine heiße und zwei
  kalte Stationen). Die App lässt hier eine Station neutral (Block: die mittlere, abwechselnd: die letzte), damit der Gesamtbedarf gleich bleibt; bei geradem n ist nichts anders.
- **Der Min-Schnitt ist für alle n gruppiert.** Der Plan ließ offen, ob für n = 12 ein Fluss je Szenario nötig ist. Er ist es nicht: Der gruppierte Min-Schnitt rechnet alle n und
  weicht von der vollen Aufzählung nicht ab (Test). Ein Max-Fluss (scipy) rechnet nur den Beispieltag, als Gegenprobe.
- **Anteil geschult als Eigenkapazität zuerst** statt der 2n-Gruppen-Fassung der Messreihe (exakt, gegen die gespeicherten Teil-Zellen und gegen die 2n-Gruppen-Fassung getestet).
  **F bei Wirkungsgrad unter 100 %** in geschlossener Form (gegen das LP getestet). Die erste geschlossene Form der Planung war falsch (g mal min(Rest, Bedarf) statt
  min(g mal Rest, Bedarf)); der LP-Vergleich hat es gezeigt.
- **Heiß neben kalt ist nicht das Optimum.** Die vollständige Aufzählung im Ungleichgewicht (n = 4: 495 Mengen, n = 6: 593.775 Mengen in 17.943 Klassen) findet bei ±50 % eine
  Menge, die 100,0 % holt; die Regel holt 99,8 % (n = 6) bzw. 99,9 % (n = 4). Bei ±25 % ist die Regel bis auf Umbenennung der beste Entwurf. Die Vorlage heißt deshalb
  „Regel, kein Optimum“.
- **Die Streuung über Bedarfsströme** liegt in der Größenordnung des Standardfehlers der Delta-Methode (Median des Verhältnisses 0,90, Maximum 1,52 auf 26 Kombinationen mit
  nennenswertem Standardfehler): Der angezeigte Standardfehler ist nicht nur ein Szenarien-, sondern ein brauchbares Maß für den Strom.
- **Zufalls-Seeds der Presets** sind die Ziehung der Messreihe, die dem Mittel der Zelle am nächsten liegt (Basis 3, Block 1, Überstreuung 10, Kleine Gruppe 1): So zeigt ein
  Preset die typische, nicht die beste oder schlechteste Ziehung; die Streuung (kleinste und größte Ziehung) steht daneben.

## Modell

Siehe den 📐-Expander der App. Kurz: n Stationen, je Station eine Gruppe j mit Kapazität S_j = r mal mittlerer Bedarf (r = 0,9; 1,0; 1,1), qualifiziert für die eigene Station und die
Zusatzstationen Q_j. Ein Tag, Kapazität teilbar (Fluid-Modell, Gruppen statt Personen). Bedarf ganzzahlig, Poisson oder Gamma-Poisson (Varianz mu + mu²/k, k = 10 und 4),
optional mit gemeinsamer Schwankung (Rate = 0,5 E_i + 0,5 C). Bedient wird der größte Fluss Quelle → Gruppen → Stationen → Senke; als Min-Schnitt:
bedient(D) = min über T von [Summe der D_i außerhalb von T + Summe der S_j aller Gruppen, die T berühren]. Servicegrad = bedient / Bedarf (Verhältnis der Erwartungen).

**Kennzahl:** Anteil am vollen Flexibilitätsnutzen = (SG(Entwurf) − SG(D0)) / (SG(F) − SG(D0)), Standardfehler per Delta-Methode auf den Szenario-Paaren; daneben immer der
absolute Gewinn in Servicegrad-Punkten und Personentagen je Tag. **Entwürfe:** D0 dedicated, A offene Kette, D1 Ring, D2 und D3 Ring mit 2 und 3 Zusatzstationen je Gruppe,
P Paare, C3, C4, C6 geschlossene Ketten, R n zufällige Bögen (eine Ziehung, daneben das Mittel), R1 eine je Gruppe, F voll, O bester Entwurf (Aufzählung), E Eigener Entwurf.
**Teilqualifikation:** nur der Anteil q jeder Gruppe lernt die Zusatzstationen. **Wirkungsgrad:** Gruppe j liefert auf einer Zusatzstation g = 0,8 je Einheit.

**Drei Zustände einer Einstellung:** *gemessen* (Messpunkt der Messreihe: 138 von 2.700 Kombinationen), *nicht gemessen* (kein Messpunkt, live exakt gerechnet, Abdeckung
vorgerechnet), *bedingt* (die Kombination ist ein Messpunkt, der Anteil geschult unter 100 % aber nur in neun Zellen gemessen). Je Aussage steht daneben „gilt / gilt nicht /
unklar“ mit zwei Standardfehlern Abstand zur Schwelle.

## Methodik

- **Zufall:** eigener ganzzahliger SplitMix64 (zählerbasiert, vektorisiert bitgleich zur skalaren Klasse), Zufalls-Seeds über `zlib.crc32` eines Schlüsseltextes, nie `hash()`,
  nie numpy-Ströme; Poisson per Inversion, Gamma als Summe von Exponentialen. Die Szenarien einer kleineren Zahl sind die ersten Zeilen der 20.000 der Messreihe.
- **Gruppierter Min-Schnitt:** Der bipartite Graph zerfällt in Komponenten, die sich addieren; je Komponente genügen die abgeschlossenen Teilmengen, weil bei gleicher Gruppenmenge
  das größte T den kleinsten Wert liefert. Das ersetzt die Aufzählung aller 2^n Teilmengen (n = 12: 4.096).
- **Wirkungsgrad:** verallgemeinerter Fluss als LP je Szenario (HiGHS, alle Szenarien als ein blockdiagonales LP), 800 Szenarien wie die Messreihe; F geschlossen.
- **Stufen:** Stufe 1 sofort (Bezugspunkte, alle festen Entwürfe, Eigener Entwurf), Stufe 2 mit Spinner (Streuung der Zufallsentwürfe), Stufe 3 mit Spinner (Kurve der
  Teilqualifikation); Ergebnis-Cache je Einstellung.
- **Vorgerechnet** (nie im Browser): die Messreihe (`data/kzs_results.json`, `tools/build_results.py`), die Abdeckung (`data/kzs_coverage.json`, `tools/sweep_coverage.py`),
  das Auswahlverfahren O für n = 6, die Aufzählung im Ungleichgewicht (`data/kzs_heisskalt.json`), die Streuung über Bedarfsströme (`data/kzs_streams.json`).

## Befunde (gemessen, keine Behauptungen)

Basiszelle: n = 6 Stationen, mittlerer Bedarf 20 Personentage je Station und Tag, Poisson, Kapazität gleich Bedarf, 20.000 gepaarte Szenarien; Anteil in Prozent des Nutzens
voller Flexibilität, in Klammern der Standardfehler. Jede Zahl dieser Tabelle ist in `tests/test_claims.py` aus den Daten nachgerechnet.

| Frage | Befund |
|---|---|
| Basiszelle | Servicegrad D0 91,1 %, F 96,4 %; Gewinn von F 5,25 Servicegrad-Punkte oder 6,29 Personentage je Tag (von 120); der Ring holt 99,996 % (SE 0,002); Gewinn je Zusatzqualifikation des Rings 1,05 Personentage je Tag |
| Anordnung statt Zahl | Gleiche 6 Bögen: Ring 100,0 %, Dreierketten 71,5 %, offene Kette (5 Bögen) 66,5 %, eine je Gruppe zufällig 66,0 %, zufällig 51,4 % (Streuung 8,6; 41,3 bis 74,0), Paare 49,9 % (SE 0,3) |
| Der letzte Bogen schließt | n = 6: jeder der fünf Bögen der offenen Kette bringt 13,3 Punkte, der schließende 33,5; n = 12: offene Kette 74,8 %, Ring 99,6 % |
| Zahl der Stationen | Paare bei n = 4, 6, 8, 12: 58,7 / 49,9 / 45,0 / 41,1 % (Näherung 58,6 / 49,5 / 45,3 / 41,2; Grenzwert 29,3 %); Gewinn von F 4,40 / 5,25 / 5,76 / 6,31 Punkte; n = 12: C3 59,3, C4 70,1, C6 83,0, Ring 99,6 % |
| Block-Ungleichgewicht | n = 12, ±50 %: Ring 37,3 %, D2 73,7 %, D3 97,9 %, Paare 0,5 %, offene Kette 0,5 %, Zufall im Mittel 45,0 % (Streuung 18,2); n = 6: Ring 75,1 %, D2 100,0 %; Zufall im Mittel über dem Ring in 2 von 138 Messpunkten |
| Heiß neben kalt | Derselbe Block-Fall (n = 12, ±50 %) mit denselben 12 Bögen als Ring in der Reihenfolge heiß, kalt, heiß, kalt: 98,1 % (SE 0,03) statt 37,3 %; Paare 83,5 % statt 0,5 %; n = 6: 99,8 % statt 75,1 %; n = 12, ±25 %: 99,3 % statt 75,9 % |
| Überstreuung | n = 6: k = 10 Ring 98,7 %, k = 4 Ring 93,3 %, D2 100,0 %; n = 8, k = 4: 88,6 %; n = 12, k = 4: Ring 81,8 %, D2 98,4 %; Gewinn von F n = 6: 5,25 (Poisson), 8,96 (k = 10), 12,57 Punkte (k = 4); gemeinsame Schwankung halbiert ihn (5,14 und 6,24) |
| Kleiner Bedarf | Mittlerer Bedarf 5, kleinster Ring-Anteil über r: n = 3, 4, 6, 8, 12: 99,8 / 99,1 / 96,4 / 93,2 / 88,2 %; D2 holt bei n = 12 den Rest (99,6 %) |
| Wirkungsgrad 0,8 | 800 Szenarien je Zelle: n = 6 Ring 86,9 % (SE 0,5), n = 12 Ring 78,0 %; D2 96,0 / 91,0 %; Paare 49,2 / 40,7 %; Gewinn von F n = 6: 4,59 statt 5,25 Punkte |
| Wenige Stationen | n = 2: Ring gleich F per Konstruktion, kleinster Gewinn 1,12 Punkte (mittlerer Bedarf 50, r = 0,9); n = 3: Ring 100,0 %, Zufall 65,6 %, Gewinn von F 3,77 Punkte oder 2,26 Personentage je Tag |
| Teilqualifikation | Ring n = 6 bei q = 0,1 / 0,2 / 0,3 / 0,5: 39,8 / 66,3 / 83,1 / 97,1 %; Paare erreichen ihre Obergrenze 49,9 % schon bei q = 0,5; geschulter Anteil für 50 / 80 / 90 %: n = 6 14 / 28 / 40, n = 12 18 / 41 / 55, n = 6 mit k = 4 33 / 69 / 91, n = 6 mit mittlerem Bedarf 5 28 / 58 / 74 % |
| Poisson ist für den Ring entartet | n = 6, 20.000 Szenarien: D1 und D2 weichen in 1 Szenario ab (mittlerer Bedarf 20), in 1.183 (mittlerer Bedarf 5), 3.406 (k = 4) und 4.960 (mittlerer Bedarf 5 und k = 4); D2 und D3 in 0 / 1 / 46 / 187 |
| Aussagen der Messreihe | Auf 138 Messpunkten: „Ring ≥ 95 %“ gilt in 86, gilt nicht in 52; „Paare ≤ 60 %“ in 102 / 15 / 3 unklar (18 nicht anwendbar); „Ring ≥ Zufall + 20 Punkte“ in 125 / 4 (9 nicht anwendbar); „D2 ≥ Ring + 5 Punkte“ in 49 / 86 / 3 unklar |
| Abdeckung | Alle 2.700 Kombinationen: „Ring ≥ 95 %“ gilt in 1.125, gilt nicht in 1.442, unklar in 133; ungemessen (2.562) gilt es in 1.039; in den 36 glatten Kombinationen (Poisson, mittlerer Bedarf ≥ 20, Wirkungsgrad 100 %, gleich) liegt der Ring bei mindestens 99,6 % |
| Bester Entwurf | Vollständige Aufzählung bis auf Umbenennung, Auswahl auf 3.000 eigenen Szenarien: in 59 von 59 Zellen (n = 4: 9, n = 6: 50) ist der beste der Ring, Unterschied −0,23 bis 0,11 Punkte; n = 4 exakt (mittlerer Bedarf 3): Ring 97,3 %, Paare 57,8 %, schlechtester Entwurf 44,1 % |
| Heiß neben kalt gegen die Aufzählung | Im Ungleichgewicht, n = 6, mittlerer Bedarf 20, Poisson: bester Entwurf 100,0 %, Regel 99,8 % bei ±50 % (Block und abwechselnd); bei ±25 % ist die Regel bis auf Umbenennung der beste (99,98 % bei Block, 99,97 % bei abwechselnd) |
| Streuung über Bedarfsströme | 30 zufällige Kombinationen, je 6 Ströme: Streuung des Ring-Anteils über die Ströme gegen den Standardfehler: Median 0,90, Maximum 1,52 (26 Kombinationen); größte Streuung 0,66 Punkte |
| Selbst-Reproduktion | Der Live-Pfad rechnet alle 147 Zellen der Messreihe nach: 10.348 Zahlen, größte Abweichung unter 1e-13 (`tools/reproduce_messreihe.py`) |
| Rechenzeit | Stufe 1 (240 zufällige Reglerkombinationen, Median / P90 / Maximum in Sekunden): Wirkungsgrad 100 %: 0,04 / 0,31 / 0,57; Wirkungsgrad 80 %: 0,37 / 0,84 / 1,77; alle drei Stufen zusammen 0,20 / 1,50 / 2,30 und 1,44 / 2,82 / 4,83; Messreihe 912 s |

Das Maß hat zwei Schwächen, die in der App neben jedem Anteil stehen: Er sagt nichts über die absolute Größe (kleinster Gewinn von F 1,12 Punkte), und er ist für F ≈ D0
instabil (kam in den 139 Zellen mit Wirkungsgrad 100 % nicht vor; die App zeigt den Anteil nicht, wenn der Gewinn von F unter 0,5 Punkten liegt, in der Abdeckung nie der Fall).

## Ehrliche Grenzen

- **Lehrbuchergebnis, nicht entdeckt:** Prozessflexibilität und die lange Kette sind bekannt; die Demo vermisst sie.
- **Der Hook gilt nur auf der glatten Fläche** (Poisson, mittlerer Bedarf ≥ 20, Wirkungsgrad 100 %, kein Ungleichgewicht). Wirkungsgrad 0,8 liegt in allen acht Messpunkten unter 95 %.
- **Poisson ist für den Ring entartet:** D1 = D2 = F fast pfadweise; „der zweite Bogen bringt nichts“ gilt dort, nicht allgemein.
- **Der Preis der Schulung ist nicht modelliert:** keine Lernkurve, kein Qualifikationsverfall, kein Wechsel. Die App nennt den Gewinn je Zusatzqualifikation in Personentagen.
- **Kein Optimum als Rahmung:** Der Ring ist per Aufzählung nur für n = 4 und n = 6 und nur bei austauschbarem Bedarf als bester Entwurf belegt; „heiß neben kalt“ ist eine Regel,
  im Ungleichgewicht nicht das Optimum (100,0 % gegen 99,8 % bei ±50 %).
- **Fluid-Modell ohne Zeit:** ein Tag, keine Schichtlage, kein Wochenmuster, teilbare Kapazität (S = 4,5 bei mittlerem Bedarf 5 und r = 0,9), Gruppen statt Personen. Das ist die
  Bedienung nach Realisierung des Bedarfs, nicht die Dienstplanung, die davor kommt.
- **Alle Parameter sind erfunden**, der Bedarf symmetrisch außer im Ungleichgewichtsfall (zwei hart gesetzte Anordnungen); keine Prognose für Ihren Betrieb.
- **Streuung:** Der Standardfehler ist die über die Szenarien (Delta-Methode); bei Wirkungsgrad 0,8 nur 800 Szenarien und 4 Ziehungen der Zufallsentwürfe (Streuung dort ein Richtwert).
- **Streamlit Cloud ist nicht gemessen:** die Zeiten gelten für das Entwicklungsgerät.
- **Aussagen mit Voraussetzungen:** „Es müssen nur 28 % lernen“ gilt für n = 6, mittleren Bedarf 20, Poisson, Wirkungsgrad 100 % (n = 12: 41 %, k = 4: 69 %).

## Verwandte Demos mit demselben mathematischen Modell

Kernmodell: zweistufig mit Rückgriff (Stufe 1 wählt den bipartiten Qualifikationsgraphen bei gegebenem Budget, Stufe 2 bedient nach Realisierung des Bedarfs den größten Fluss).
Neu ist nicht der Fluss, nicht das Pooling und nicht die Szenariotechnik, sondern die Struktur des Graphen als Entscheidung, das Maß „Anteil am vollen Flexibilitätsnutzen“ über
Entwurfsfamilien, die Kurve der Teilqualifikation und die Gegenfälle.

| Demo | Was dort steht | Abgrenzung |
|---|---|---|
| `netzdesign-unsicherheit-demo` | Netzdesign mit Fixkosten, Szenarien, Rückgriff-LP | gleiche Familie „Design + Rückgriff“; dort entscheidet ein Design mit Fixkosten, hier nur die Anordnung der Verbindungen bei gleichem Budget |
| `newsvendor-evpi-demo` | Umlagerung als Fluss zwischen allen Standorten (voll und fest) | dort ist der Umlagergraph voll; welche Verbindungen es geben soll, kommt nicht vor |
| `mmc-queue-demo`, `standort-bestand-demo` | Pooling: getrennte Schlangen gegen eine gemeinsame, Risk Pooling im Bestand | entspricht D0 gegen F; kein Zwischenentwurf; die gemeinsame Schwankung halbiert den Gewinn auch hier |
| `servicegrad-tag-demo` | Servicegrad über den Tag mit Schichten und Warteschlange; Multiskill nicht umgesetzt | die dort gelassene Lücke, hier als Tagesbilanz ohne Warteschlange |
| `shift_demo` | Überdeckung eines gegebenen Stundenbedarfs; keine Qualifikationen | die dort gelassene Lücke; hier ist der Bedarf zufällig und die Qualifikation die Entscheidung |
| `hungarian-demo`, `hopcroft-karp-demo`, `network-flow-demo`, `auction-demo` | Zuordnung und Max-Fluss als Verfahren | deterministisch, ohne Bedarf als Zufallsgröße; hier nur die Auswerteroutine (Min-Schnitt) |

## Literatur

Per Suche bestätigt (Treffer der Vorab-Messreihe vom 2026-10-11, Abstracts, Volltexte nicht gelesen):

- Jordan und Graves (1995), Principles on the benefits of manufacturing process flexibility, *Management Science* 41(4), 577 bis 594.
- Graves und Tomlin (2003), Process flexibility in supply chains, *Management Science* 49(7), 907 bis 919.
- Chou, Chua, Teo und Zheng (2010), Design for process flexibility: efficiency of the long chain and sparse structure, *Operations Research* 58(1), 43 bis 58; dieselben
  (2011), Process flexibility revisited: the graph expander and its applications, *Operations Research* 59(5), 1090 bis 1105.
- Simchi-Levi und Wei (2015), Worst-case analysis of process flexibility designs, *Operations Research* 63(1), 166 bis 185 (nur aus dem Suchtreffer).
- Wallace und Whitt (2005), A staffing algorithm for call centers with skill-based routing, *MSOM* 7(4), 276 bis 294 (ob die Arbeit Ketten ausdrücklich nennt, nicht geprüft).
- Bhulai, Koole und Pot (2008), Simple methods for shift scheduling in multiskill call centers, *MSOM* 10(3), 411 bis 420; Avramidis, Chan, Gendreau, L'Ecuyer und
  Pisacane (2010), Optimizing daily agent scheduling in a multiskill call center, *European Journal of Operational Research* 200(3), 822 bis 832.

## Tests

Siehe `tests/`; die Suite läuft ohne Netz und ohne Wanduhr-Zusagen.

- **Einheiten von Hand (Mini-Instanzen):** Generator gegen die veröffentlichten Referenzwerte, Verteilungen gegen scipy.stats, Entwürfe, abgeschlossene Teilmengen an der Kette
  A → B → C, Komponenten, Teilqualifikation (q = 0 und q = 1), LP gegen Einzel-LP, Max-Fluss des Beispieltags.
- **Orakel** (`tests/test_oracle_kreuzschulung.py`): Min-Schnitt gegen Edmonds-Karp, scipy.maximum_flow, LP und Brute Force; geschlossene Extreme D0, F und Paare bei Poisson;
  der beste Entwurf bei n = 4 durch Aufzählung aller 495 Mengen; Wirkungsgrad gegen eine unabhängig formulierte LP und das Gegenbeispiel 16,4; Teilqualifikation gegen die 2n-Gruppen-Fassung.
- **Selbst-Reproduktion:** sieben Zellen der Messreihe (Basis, Block, Überstreuung, Korrelation, Wirkungsgrad, Teil, kleiner Bedarf) bis 1e-11; alle 147 mit `tools/reproduce_messreihe.py`.
- **Claims** (`tests/test_claims.py`): jede Zahl dieser README aus `data/*.json` nachgerechnet. **Presets** (`tests/test_stories.py`): Kriterien an der Messreihe und live, jedes
  Kriterium kippt einzeln an seiner Schwelle, der Beispieltag zeigt die Geschichte.
- **Oberfläche** (`tests/test_app.py`): jedes Preset, jeder Regler an Minimum und Maximum, Permalink mit unbekannten Werten, String und Liste, Eigener Entwurf mit Wechsel von n,
  jede Vorlage, die drei Zustände, PDF. **Fehler-Einbau** (`tools/mutation_check.py`).

## Dateistruktur

| Datei | Zweck |
|---|---|
| `app.py` | Streamlit-App: Skelett, fünf Abschnitte, Selbstbau, Messreihe, Expander |
| `kzs_constants.py` | Regler-Stufen, Szenarienzahlen, Schwellen, Farben, Texte der Entwürfe |
| `kzs_rng.py`, `kzs_demand.py` | SplitMix64 und Zufalls-Seeds; Poisson, Gamma-Poisson, Struktur des Bedarfs |
| `kzs_designs.py` | Entwürfe als Bitmasken, Eigener Entwurf, Vorlagen, Reihenfolge heiß neben kalt |
| `kzs_flow.py` | Komponenten, abgeschlossene Teilmengen, gruppierter Min-Schnitt, Teilqualifikation, Batch-LP, F geschlossen, Tagesfluss |
| `kzs_stats.py` | Anteil, Standardfehler, Streuung der Ziehungen |
| `kzs_pipeline.py` | Einstellungen (nur Schlüsselwörter), Stufe 1 bis 3, bester Entwurf n = 4, Beispieltag, Satz für die Abdeckung |
| `kzs_evaluation.py` | Meldungen in drei Zuständen, Diagnose, Tabelle der Entwürfe |
| `kzs_results.py` | Laden und Auswerten von Messreihe und Abdeckung, Aussagen A1 bis A5 |
| `kzs_visualization.py`, `kzs_pdf_export.py` | Plotly-Abbildungen (Achsen gesperrt), Auswertungs-PDF |
| `kzs_presets.py`, `kzs_stories.py` | Permalink, Callbacks, Vorlagen; Presets, Geschichten, Abnahmekriterien |
| `data/kzs_results.json`, `data/kzs_coverage.json` | Messreihe (147 Zellen) und Abdeckung (2.700 Kombinationen) |
| `data/kzs_heisskalt.json`, `kzs_streams.json`, `kzs_n4_exakt.json`, `kzs_timing.json`, `kzs_reproduction.json` | Aufzählung im Ungleichgewicht, Streuung über Ströme, exakte Werte n = 4, Zeitmessung, Reproduktion |
| `tools/` | `build_results.py`, `sweep_coverage.py`, `reproduce_messreihe.py`, `heiss_kalt_aufzaehlung.py`, `stream_spread.py`, `exakt_n4.py`, `seed_search.py`, `live_timing.py`, `mutation_check.py` |
| `tests/` | Mini-Instanzen, Orakel, Claims, Presets, AppTest, Footer |
| `requirements.txt`, `requirements-dev.txt`, `.github/workflows/tests.yml` | Laufzeit (mit scipy wegen HiGHS), Tests, CI |

## Bewusst nicht umgesetzt

Ein Preis der Schulung (Kostenregler, Amortisation); Warteschlange und Skill-based Routing (Multiskill-Staffing); Zeitverlauf und Schichtlage; Personen statt Gruppen (Ganzzahligkeit,
Dienstplanung); mehrere Wirkungsgrade je Bogen; ein Suchverfahren für den besten Entwurf bei n ≥ 8; Unsicherheit der Parameter; Gleichverteilung und Mehrgipfligkeit des
Bedarfs; mehrstufige Ketten (Graves und Tomlin); Lernkurve und Verlust durch Wechsel.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, NumPy, SciPy (HiGHS) und fpdf2.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Schichtplanung optimieren](https://sebastianhanisch.net/schichtplanung-optimierung.html).
