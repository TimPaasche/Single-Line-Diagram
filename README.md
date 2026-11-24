# sld – Einlinienschaltplan-Generator

🇬🇧 **English documentation: [README.en.md](README.en.md)**

Erzeugt elektrische Einlinienschaltpläne (Single-Line Diagrams) aus einer Konfigurationsdatei
in YAML, JSON oder TOML. Schwerpunkt ist der Netzanschluss von PV-Anlagen mit Batteriespeicher
und Transformatoren. Die Symbole folgen DIN EN 60617, das Layout entsteht automatisch: Netz oben,
Erzeuger und Verbraucher unten, Spannungsebenen als Bänder, Sammelschienen waagerecht, Abgänge
senkrecht und keine überlappenden Beschriftungen.

## Voraussetzungen

* **Python 3.10 oder neuer** ([python.org](https://www.python.org/downloads/); unter Windows bei der
  Installation „Add python.exe to PATH“ anhaken). Prüfen mit `python --version`.
* **pip** (ist bei Python dabei)
* optional **Git**, wenn das Repository geklont werden soll

Die Python-Abhängigkeiten werden von `pip` automatisch installiert:

| Paket | Zweck | Lizenz |
|---|---|---|
| `pydantic` ≥ 2.6 | Datenmodell und Validierung | MIT |
| `pyyaml` ≥ 6.0 | YAML-Loader | MIT |
| `matplotlib` ≥ 3.7 | Zeichnen (SVG/PNG/PDF) | Matplotlib License (BSD-artig) |
| `tomli` ≥ 2.0 | TOML-Loader, nur Python 3.10 | MIT |
| `pytest` ≥ 7 | Tests, nur mit `[dev]` | MIT |

## Installation

### Variante A: mit `git clone`

```bash
git clone https://github.com/TimPaasche/Single-Line-Diagram.git
cd Single-Line-Diagram
```

### Variante B: als ZIP herunterladen

1. Auf GitHub **Code → Download ZIP** wählen.
2. ZIP entpacken, z. B. nach `C:\Tools\Single-Line-Diagram-main` bzw. `~/Single-Line-Diagram-main`.
3. Im entpackten Ordner (dort, wo die `pyproject.toml` liegt) ein Terminal öffnen:

```bash
cd Single-Line-Diagram-main
```

### Danach (für beide Varianten gleich)

Virtuelle Umgebung anlegen, aktivieren und das Paket installieren:

```bash
python -m venv .venv
```

| System | Aktivieren |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| Windows (Git Bash) | `source .venv/Scripts/activate` |
| Linux / macOS | `source .venv/bin/activate` |

```bash
pip install -e ".[dev]"      # mit Tests; nur zum Benutzen reicht: pip install .
sld --help                   # Installation prüfen
pytest                       # optional: Tests ausführen
```

> Unter Windows blockiert PowerShell das Aktivierungsskript eventuell. Abhilfe einmalig:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
> Ohne Aktivieren geht es auch: `.venv\Scripts\sld.exe render …` bzw. `python -m sld render …`.

Aktualisieren: bei Variante A `git pull`, bei Variante B neues ZIP herunterladen. Danach jeweils
erneut `pip install -e ".[dev]"`.

## Schnellstart

```bash
sld validate examples/02_pv_speicher_ms.yaml
sld render   examples/02_pv_speicher_ms.yaml -o plan.svg
sld render   examples/03_pv_park_2_trafos.yaml -o park.pdf --theme simple
sld list-components -v
sld schema -o sld.schema.json
```

| Befehl | Zweck |
|---|---|
| `sld render <datei> [-o out.svg] [--format svg/png/pdf] [--theme din/simple] [--paper auto/A5/A4/A3/none] [--orientation auto/landscape/portrait] [--dpi 200] [--strict]` | Plan zeichnen. Das Format ergibt sich aus `--format` oder der Dateiendung. Bei Fehlern wird nichts geschrieben. |
| `sld validate <datei> [--strict]` | Konfiguration prüfen. Exit-Code 1 bei Fehlern, mit `--strict` auch bei Warnungen. |
| `sld list-components [-v]` | Registrierte Komponenten mit Parametern anzeigen |
| `sld schema [-o datei]` | JSON-Schema für die Autovervollständigung im Editor exportieren |
| `sld --plugin modul …` | Python-Modul mit eigenen Komponenten laden |

Aus Python:

```python
import sld
diagram = sld.load("anlage.yaml")         # YAML, JSON, TOML -> dasselbe Modell
issues = sld.validate(diagram)            # Fehler + Warnungen inkl. Zeilennummer
layout, issues = sld.render_file("anlage.yaml", "anlage.svg")
```

### Beispiele (`examples/`)

| Datei | Inhalt |
|---|---|
| `01_pv_niederspannung.yaml` | PV 30 kWp direkt am NS-Hausanschluss, Haushalt, Wallbox, Erdung |
| `02_pv_speicher_ms.yaml` / `.json` / `.toml` | PV 500 kWp + Speicher über 20/0,4-kV-Trafo am MS-Netz, in allen drei Formaten |
| `03_pv_park_2_trafos.yaml` | PV-Park mit 2 Trafos, NS-Bus-Kupplung (normal offen), Template für Wechselrichter-Abgänge, Stückliste |

## Konfiguration

```yaml
# yaml-language-server: $schema=./sld.schema.json
diagram:
  title: "PV 500 kWp + Speicher am MS-Netz"
  theme: din              # din | simple
  bom: false              # Stückliste neben/unter dem Plan
  label_detail: full      # full | short | id
  show_ids: false         # IDs am Symbol anzeigen (Vorgabe: aus, stattdessen name)
  label_width_mm: 32      # Beschriftungen ab dieser Breite umbrechen (0 = nie)
  paper: auto             # auto | A5 | A4 | A3 | none
  orientation: auto       # auto | landscape | portrait

nodes:
  - {id: netz, type: grid, voltage_kv: 20, label: "EVU Mittelspannung"}
  - {id: ms_bus, type: busbar, voltage_kv: 20}
  - {id: t1, name: "Trafo 1", type: transformer, rating_kva: 1250, ratio: "20/0.4 kV", vector_group: Dyn5}
  - {id: nsp_bus, type: busbar, voltage_kv: 0.4}
  - {id: wr1, name: "WR 1", type: inverter, kva: 500}
  - {id: pv1, name: "PV-Feld Dach Süd", type: pv_array, kwp: 500}

connections:
  - from: netz
    to: ms_bus
    via: [{type: circuit_breaker, id: Q1}, {type: meter, id: P1}]
  - {from: ms_bus, to: t1, via: [{type: circuit_breaker}]}
  - {from: t1, to: nsp_bus}
  - {from: nsp_bus, to: wr1, via: [{type: fuse}]}
  - {from: wr1, to: pv1}
```

* **`nodes`**: Knoten des Graphen, jeder mit eindeutiger `id` und einem `type` aus der Komponentenbibliothek.
* **`connections`**: Kanten zwischen zwei Knoten. Die Richtung spielt keine Rolle, das Layout orientiert sich ab den Netzanschlüssen.
  * `via`: Reihenelemente (Schalter, Sicherung, Zähler, Kabel, Trafo, Wechselrichter) in Reihenfolge von `from` nach `to`. Ohne `id` wird automatisch ein Kennzeichen nach DIN EN 81346 vergeben (`Q1`, `F1`, `P1`, `W1`, `T1` …).
  * `allow_loop: true`: Die Verbindung darf bewusst einen Ring schließen.
* **`diagram`**: `title`, `subtitle`, `project`, `author`, `date`, `revision` (Schriftfeld im DIN-Theme), `theme`, `bom`, `label_detail`, `show_ids`, `label_width_mm`, `paper`, `orientation`.
* Ein `$schema`-Schlüssel auf oberster Ebene wird ignoriert, damit JSON-Editoren das Schema finden.

### Beschriftung: Name statt ID

Die `id` ist nur noch der interne Schlüssel für `connections` und wird standardmäßig **nicht** gezeichnet.
Am Symbol erscheint stattdessen der optionale `name` (fett), darunter `label` und die technischen Daten.
Mit `diagram.show_ids: true` steht die ID zusätzlich in der ersten Zeile und als Spalte „Kennz.“ in der
Stückliste. In Templates funktioniert z. B. `name: "WR ${id}"`.

Alle Beschriftungen werden an Leerzeichen auf `label_width_mm` (Vorgabe 32 mm) umbrochen, damit der Plan
nicht unnötig in die Breite wächst. Ein `\n` im Text erzwingt einen Umbruch. Auch die Spalten der
Stückliste werden umbrochen.

### Blattformat (Druck)

Mit `paper: auto` (Vorgabe) wird das kleinste Format aus **A5, A4, A3** gewählt, auf das der Plan
unverkleinert passt; die Ausrichtung (quer/hoch) folgt dem Seitenverhältnis des Plans. Passt er nicht
einmal auf A3, wird er auf A3 in der günstigeren Ausrichtung verkleinert (Warnung W301). Mit `paper: A4`
o. ä. wird das Format fest vorgegeben (bei Bedarf ebenfalls verkleinert), `orientation` legt quer/hoch
fest. Die Stückliste wird rechts neben oder unter den Plan gesetzt, je nachdem was besser passt.
Im DIN-Theme hat das Blatt einen Rahmen nach DIN EN ISO 5457 (20 mm Heftrand links, sonst 10 mm),
das Schriftfeld sitzt unten rechts im Rahmen. `paper: none` ergibt das frühere Verhalten: Das Blatt ist
genau so groß wie der Plan.

### Gemeinsame Felder aller Komponenten

| Feld | Bedeutung |
|---|---|
| `id` | Eindeutiges Kennzeichen. Pflicht bei `nodes`, optional in `via`. |
| `type` | Komponententyp |
| `name` | Anzeigename am Symbol (fett). Die `id` wird nur mit `diagram.show_ids` gezeigt. |
| `label` | Freitext unter dem Namen am Symbol |
| `order` | Layout-Hinweis: Sortierschlüssel unter Geschwister-Abgängen (kleiner = weiter links) |
| `pos: {x, y}` | Layout-Hinweis: feste Position der Symbolmitte in mm, relativ zur linken oberen Ecke des Planinhalts. Der Teilbaum wandert mit. |
| `note` | Bemerkung (erscheint in der Stückliste) |

### Komponentenreferenz

Pflichtfelder sind **fett**. Art: *Quelle* (nur Anschluss unten), *Schiene*, *Reihe* (oben/unten, darf in `via` stehen), *Endgerät* (nur Anschluss oben).

| Typ | Art | Felder |
|---|---|---|
| `grid` – Netz / Netzanschlusspunkt | Quelle | **`voltage_kv`**, `sk_mva` (Kurzschlussleistung S″k) |
| `busbar` – Sammelschiene | Schiene | `voltage_kv` (wird sonst über Nachbarn/Trafo abgeleitet) |
| `transformer` – Transformator | Reihe | **`rating_kva`**, `ratio` (`"20/0.4 kV"`) oder `hv_kv` + `lv_kv`, `uk_percent`, `vector_group` |
| `circuit_breaker` – Leistungsschalter | Reihe | `state` (`closed`/`open`), `rating_a` |
| `switch_disconnector` – Lasttrennschalter | Reihe | `state`, `rating_a` |
| `fuse` – Sicherung | Reihe | `state` (`open` = Einsatz gezogen), `rating_a`, `fuse_type` (`"NH2 gG"`) |
| `meter` – Zähler | Reihe | `direction` (`import` = Bezug, `export` = Einspeisung, `bidirectional`), `number` |
| `cable` – Kabel, `line` – Freileitung | Reihe | `length_m`, `cross_section_mm2`, `conductors` (`"3×1×"`), `designation` (`"NA2XS2Y"`) |
| `inverter` – Wechselrichter | Reihe (AC oben, beliebig viele DC-Eingänge unten) | **`kva`**, `inverter_type` (`string`/`central`/`hybrid`), `count` |
| `pv_array` – PV-Generator | Endgerät (DC) | **`kwp`**, `strings`, `modules` |
| `battery` – Batteriespeicher | Endgerät | **`kwh`**, **`kw`**, `coupling` (`ac`/`dc`), `inverter_kva` (integrierter Batteriewechselrichter, wird mitgezeichnet) |
| `load` – Verbraucher | Endgerät | `kw`, `cos_phi` |
| `generator` – Generator | Endgerät | **`kva`**, `gen_type` (BHKW, Diesel …) |
| `motor` – Motor | Endgerät | **`kw`**, `starter` |
| `ev_charger` – Ladeeinrichtung (Wallbox) | Endgerät | **`kw`** (je Ladepunkt), `points` |
| `grounding` – Erdung | Endgerät | `system` (`TN-C-S` …), `resistance_ohm` |

Die aktuelle Liste mit Beschreibungen zeigt `sld list-components -v`.

### Templates / Makros

```yaml
templates:
  pv_feeder:
    params: {kwp: null, kva: null, strings: 20}   # null = Pflichtparameter
    entry: wr                                     # Anschlusspunkt von außen (Vorgabe: erster Knoten)
    nodes:
      - {id: wr, type: inverter, kva: "${kva}", name: "WR ${id}"}
      - {id: pv, type: pv_array, kwp: "${kwp}", strings: "${strings}"}
    connections:
      - {from: wr, to: pv}

nodes:
  - {id: a1, template: pv_feeder, params: {kwp: 400, kva: 350}}
  - {id: a2, template: pv_feeder, params: {kwp: 400, kva: 350}, order: 1}

connections:
  - {from: nsp_a, to: a1, via: [{type: fuse, rating_a: 630}]}   # landet an a1.wr
```

* Interne Knoten heißen `<instanz>.<id>` (`a1.wr`, `a1.pv`) und können direkt referenziert werden.
* Verbindungen auf die Instanz-ID landen am `entry`-Knoten. `order` und `pos` der Instanz gelten ebenfalls für den `entry`-Knoten.
* `"${name}"` als ganzer Wert behält den Typ (Zahl bleibt Zahl). In Texten wird der Wert eingesetzt. `${id}` ist die Instanz-ID.

### Kupplungen, Ringe, mehrere Einspeisungen

Mehrere `grid`-Knoten sind erlaubt. Eine Verbindung, die einen Ring schließt (z. B. Bus-Kupplung
zweier Sammelschienen oder Reserveeinspeisung), ist nur zulässig, wenn sie ein offenes Schaltgerät
enthält (`state: open`) oder `allow_loop: true` trägt. Kupplungen zwischen benachbarten
Sammelschienen werden waagerecht zwischen den Schienen gezeichnet. Ein zweites Netz, das auf eine
Schiene einspeist, wird von oben herangeführt.

## Validierung

Fehler und Warnungen enthalten Datei, Zeile und Knoten-ID:

```
anlage.yaml:23: FEHLER [E007] Knoten 'nsp': Spannungswechsel ohne Transformator: 'ms' hat 20 kV, 'nsp' hat 0,4 kV, …
anlage.yaml:9: WARNUNG [W101] Knoten 't1': Transformator (630 kVA) kleiner als angeschlossene Erzeugung (1000 kVA)
```

Bei YAML ist die Zeile exakt. Bei JSON und TOML bestimmt sie eine Textsuche nach der ID bzw. dem `from`.

| Code | Bedeutung |
|---|---|
| E000 | Syntax- oder Schemafehler (fehlendes/unbekanntes Feld, falscher Typ, unbekannter Komponententyp) |
| E001 | ID doppelt vergeben |
| E002 | Verbindung verweist auf unbekannten Knoten |
| E003 | Knoten ist mit nichts verbunden |
| E004 | kein Netzanschlusspunkt (`grid`) |
| E005 | Teilnetz nicht mit einem Netzanschlusspunkt verbunden |
| E006 | unbeabsichtigte Schleife |
| E007 | Spannungswechsel ohne Transformator |
| E008 | Trafo-Übersetzung passt nicht zu den angeschlossenen Ebenen |
| E009 | zu viele Anschlüsse (z. B. Endgerät mit zwei Verbindungen) |
| E010 | Nicht-Reihenelement in `via` |
| E011 | Verbindung auf sich selbst |
| E012 | Template-Fehler |
| W101 | Transformator kleiner als die Summe der angeschlossenen Erzeuger (Wechselrichter, Generatoren, Speicher) |
| W102 | Batterie ohne Wechselrichter |
| W103 | PV-Generator ohne Wechselrichter |
| W104 | DC-gekoppelte Batterie ohne Hybrid-Wechselrichter |
| W105 | Kupplung zwischen Nicht-Sammelschienen (vereinfachte Darstellung) |
| W107 | Kupplung wird unterhalb des Plans geführt |
| W201/W202 | Überlappung nach manueller Positionierung (`pos`) |
| W301 | Plan passt nicht unverkleinert auf das Blattformat und wird verkleinert |

Spannungsebenen werden abgeleitet: Grenzen sind Transformatoren (laut `ratio`) und Wechselrichter
(darunter DC). Eine Sammelschiene braucht deshalb nicht zwingend `voltage_kv`.

## Editor-Integration (JSON-Schema)

`sld schema -o sld.schema.json` erzeugt das Schema aus dem pydantic-Modell, inkl. aller
registrierten Komponenten und Plugins. Einbindung:

* YAML (VS Code mit der Red-Hat-YAML-Erweiterung): erste Zeile `# yaml-language-server: $schema=./sld.schema.json`
* JSON: `"$schema": "./sld.schema.json"`
* TOML (Taplo/Even Better TOML): `#:schema ./sld.schema.json`

Die mitgelieferte `sld.schema.json` wird von einem Test auf Aktualität geprüft.

## Architektur

```
src/sld/
  schema/      pydantic-v2-Modell (dynamische Union aller Komponenten), Templates,
               Topologie (Spannbaum, Ringe), Spannungsanalyse, Validierung
  io/          Loader YAML / JSON / TOML (Erkennung über Endung) -> Rohdaten + Zeilenkarte
  components/  Komponentenbibliothek: je Datei eine Komponente, Registry mit @register
  layout/      automatisches Layout -> rein geometrisches Layout-Objekt (mm)
  render/      Renderer-Schnittstelle, Pen (Symbol-Koordinaten), Zeichenablauf,
               matplotlib-Backend (SVG/PNG/PDF)
  themes.py    din (Rahmen, Schriftfeld, Bandlinien) / simple (farbige Bänder)
  cli.py
```

* `layout` kennt kein matplotlib. Textbreiten kommen über `TextMetrics`: Das Backend liefert exakte Werte, eine konservative Schätzung ist eingebaut.
* `render.base.Renderer` hat nur Primitive (`polyline`, `polygon`, `circle`, `text`, `save`). Ein weiteres Backend, z. B. direktes SVG, implementiert diese Methoden und deklariert `formats`.
* Überlappungsfreiheit gilt konstruktionsbedingt: Jeder Teilbaum belegt ein Intervall inkl. seiner Beschriftungen, Geschwister liegen ohne Überschneidung nebeneinander. Ein abschließender Kollisionstest versetzt Labels nur, wenn `pos` etwas verschoben hat.

## Neue Komponente hinzufügen

1. Neue Datei `src/sld/components/heat_pump.py` anlegen. Sie wird automatisch geladen, der Kern bleibt unverändert:

```python
from pydantic import Field

from sld.components import Component, DrawContext, Kind, register
from sld.util import fmt_num


@register("heat_pump")
class HeatPump(Component):
    """Wärmepumpe."""

    kind = Kind.TERMINAL        # SOURCE / BUS / SERIES / TERMINAL
    title = "Wärmepumpe"        # Anzeigename (list-components, Stückliste)
    ref_letter = "E"            # Präfix für automatische IDs
    size = (10.0, 12.0)         # Breite, Höhe des Symbols in mm

    kw: float = Field(gt=0, description="Elektrische Leistung in kW")
    cop: float | None = Field(None, gt=0, description="Leistungszahl")

    def data_lines(self) -> list[str]:          # Beschriftung am Symbol / Stückliste
        return [f"{fmt_num(self.kw)} kW"] + ([f"COP {fmt_num(self.cop)}"] if self.cop else [])

    def draw(self, pen, ctx: DrawContext) -> None:
        # lokale Koordinaten in mm: Mitte (0,0), Anschluss oben bei y = -h/2, y zeigt nach unten
        pen.line((0, -6), (0, -5))
        pen.circle(0, 0, 5)
        pen.text(0, 0, "WP", size=6, bold=True)
```

2. Optional überschreiben:
   * `explicit_voltage()`, wenn die Komponente eine Spannungsebene festlegt,
   * `is_dc_device()`, wenn sie auf der DC-Seite arbeitet,
   * `generation_kva()`, damit sie in der Trafo-Auslastungswarnung zählt,
   * `is_open()`, wenn sie einen Schaltzustand hat (oder von `SwitchingDevice` erben),
   * `connection_limit()` bzw. `max_connections`.
3. `sld list-components` prüfen und `sld schema -o sld.schema.json` neu erzeugen.

Komponenten aus **externen Paketen** lassen sich ohne Änderung an diesem Repository einbinden:
entweder per `sld --plugin mein_paket.komponenten render …` oder über einen Entry-Point in der
`pyproject.toml` des Plugin-Pakets:

```toml
[project.entry-points."sld.components"]
waermepumpe = "mein_paket.komponenten"
```

Hilfsfunktionen des Pens: `line`, `rect`, `circle`, `ellipse`, `polygon` (`fill="fg"`/`"bg"`),
`text`, `arrow`, `sine` (~), `dc_sign` (=), `hatch`. Gemeinsame Symbolteile (Wechselrichterkasten,
Batteriezellen, Maschinenkreis) liegen in `components/_draw.py`.

## Tests

```bash
pytest
```

Abgedeckt sind:
* Loader: alle drei Formate liefern ein identisches Modell, Zeilennummern
* Templates
* alle Validierungsregeln
* Layout: keine Überlappung der Bounding-Boxes für alle Beispiele × Themes × Textmetriken, Bänder, Kupplung, `order`/`pos`, zweite Einspeisung
* Blatt: Anzeigenamen/ausgeblendete IDs, Textumbruch, Formatwahl A5/A4/A3, Verkleinerung
* Rendering: Smoke-Test für SVG/PNG/PDF, deterministische SVG-Ausgabe, eigenes Backend
* CLI inkl. Plugin-Komponente und Aktualität des Schemas

## Lizenz

[MIT](LICENSE) – © 2026 Tim Paasche. Die verwendeten Bibliotheken stehen unter MIT- bzw.
BSD-artigen Lizenzen (siehe [Voraussetzungen](#voraussetzungen)) und sind damit kompatibel.
