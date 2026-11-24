# sld – Single-Line Diagram Generator

🇩🇪 **Deutsche Dokumentation: [README.md](README.md)**

Generates electrical single-line diagrams from a configuration file in YAML, JSON or TOML. The focus
is the grid connection of PV systems with battery storage and transformers. Symbols follow
DIN EN 60617 (IEC 60617), and the layout is fully automatic: grid at the top, generators and loads at
the bottom, voltage levels as bands, horizontal busbars, vertical feeders, and no overlapping labels.

> **Note:** Texts drawn on the diagram (parts list, title block, data such as "offen") and the
> messages of the validator are in German.

## Requirements

* **Python 3.10 or newer** ([python.org](https://www.python.org/downloads/); on Windows tick
  "Add python.exe to PATH" during installation). Check with `python --version`.
* **pip** (ships with Python)
* optionally **Git**, if you want to clone the repository

`pip` installs the Python dependencies automatically:

| Package | Purpose | License |
|---|---|---|
| `pydantic` ≥ 2.6 | data model and validation | MIT |
| `pyyaml` ≥ 6.0 | YAML loader | MIT |
| `matplotlib` ≥ 3.7 | drawing (SVG/PNG/PDF) | Matplotlib License (BSD-style) |
| `tomli` ≥ 2.0 | TOML loader, Python 3.10 only | MIT |
| `pytest` ≥ 7 | tests, only with `[dev]` | MIT |

## Installation

### Option A: `git clone`

```bash
git clone https://github.com/TimPaasche/Single-Line-Diagram.git
cd Single-Line-Diagram
```

### Option B: download as ZIP

1. On GitHub choose **Code → Download ZIP**.
2. Extract the ZIP, e.g. to `C:\Tools\Single-Line-Diagram-main` or `~/Single-Line-Diagram-main`.
3. Open a terminal in the extracted folder (the one containing `pyproject.toml`):

```bash
cd Single-Line-Diagram-main
```

### Then (same for both options)

Create a virtual environment, activate it and install the package:

```bash
python -m venv .venv
```

| System | Activate |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| Windows (Git Bash) | `source .venv/Scripts/activate` |
| Linux / macOS | `source .venv/bin/activate` |

```bash
pip install -e ".[dev]"      # with tests; for usage only: pip install .
sld --help                   # check the installation
pytest                       # optional: run the tests
```

> On Windows, PowerShell may block the activation script. Fix once with
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
> It also works without activating: `.venv\Scripts\sld.exe render …` or `python -m sld render …`.

Updating: with option A run `git pull`, with option B download a new ZIP. Then run
`pip install -e ".[dev]"` again.

## Quick start

```bash
sld validate examples/02_pv_speicher_ms.yaml
sld render   examples/02_pv_speicher_ms.yaml -o plan.svg
sld render   examples/03_pv_park_2_trafos.yaml -o park.pdf --theme simple
sld list-components -v
sld schema -o sld.schema.json
```

| Command | Purpose |
|---|---|
| `sld render <file> [-o out.svg] [--format svg/png/pdf] [--theme din/simple] [--paper auto/A5/A4/A3/none] [--orientation auto/landscape/portrait] [--dpi 200] [--strict]` | Draw the diagram. The format is taken from `--format` or the file extension. Nothing is written if there are errors. |
| `sld validate <file> [--strict]` | Check a configuration. Exit code 1 on errors, with `--strict` also on warnings. |
| `sld list-components [-v]` | Show registered components and their parameters |
| `sld schema [-o file]` | Export the JSON schema for editor auto-completion |
| `sld --plugin module …` | Load a Python module with additional components |

From Python:

```python
import sld
diagram = sld.load("plant.yaml")          # YAML, JSON, TOML -> same model
issues = sld.validate(diagram)            # errors + warnings incl. line numbers
layout, issues = sld.render_file("plant.yaml", "plant.svg")
```

### Examples (`examples/`)

| File | Content |
|---|---|
| `01_pv_niederspannung.yaml` | PV 30 kWp directly at the LV house connection, household, wallbox, earthing |
| `02_pv_speicher_ms.yaml` / `.json` / `.toml` | PV 500 kWp + storage via 20/0.4 kV transformer on the MV grid, in all three formats |
| `03_pv_park_2_trafos.yaml` | PV park with 2 transformers, LV bus coupler (normally open), template for inverter feeders, parts list |

## Configuration

```yaml
# yaml-language-server: $schema=./sld.schema.json
diagram:
  title: "PV 500 kWp + Speicher am MS-Netz"
  theme: din              # din | simple
  bom: false              # parts list beside/below the diagram
  label_detail: full      # full | short | id
  show_ids: false         # show IDs on symbols (default: off, use name instead)
  label_width_mm: 32      # wrap labels wider than this (0 = never)
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

* **`nodes`**: nodes of the graph, each with a unique `id` and a `type` from the component library.
* **`connections`**: edges between two nodes. The direction does not matter; the layout is oriented from the grid connections.
  * `via`: series elements (switch, fuse, meter, cable, transformer, inverter) in order from `from` to `to`. Without an `id`, a reference designation according to DIN EN 81346 is assigned automatically (`Q1`, `F1`, `P1`, `W1`, `T1` …).
  * `allow_loop: true`: the connection may deliberately close a ring.
* **`diagram`**: `title`, `subtitle`, `project`, `author`, `date`, `revision` (title block in the DIN theme), `theme`, `bom`, `label_detail`, `show_ids`, `label_width_mm`, `paper`, `orientation`.
* A top-level `$schema` key is ignored so that JSON editors can find the schema.

### Labels: name instead of ID

The `id` is only the internal key for `connections` and is **not** drawn by default. Instead, the
optional `name` is shown on the symbol (bold), followed by `label` and the technical data. With
`diagram.show_ids: true` the ID is additionally shown in the first line and as the "Kennz." column of
the parts list. In templates you can write e.g. `name: "WR ${id}"`.

All labels are wrapped at spaces to `label_width_mm` (default 32 mm) so the diagram does not grow
unnecessarily wide. A `\n` in the text forces a line break. The parts list columns are wrapped as well.

### Paper size (printing)

With `paper: auto` (default) the smallest of **A5, A4, A3** that fits the diagram at full scale is
chosen; the orientation (landscape/portrait) follows the aspect ratio of the diagram. If it does not
even fit on A3, it is scaled down onto A3 in the better orientation (warning W301). `paper: A4` etc.
fixes the format (scaled down if needed), `orientation` fixes landscape/portrait. The parts list is
placed to the right of or below the diagram, whichever fits better. In the DIN theme the sheet has a
frame according to DIN EN ISO 5457 (20 mm filing margin on the left, 10 mm elsewhere); the title block
sits in the bottom-right corner of the frame. `paper: none` restores the previous behaviour: the sheet
is exactly as large as the diagram.

### Common fields of all components

| Field | Meaning |
|---|---|
| `id` | Unique identifier. Required in `nodes`, optional in `via`. |
| `type` | Component type |
| `name` | Display name on the symbol (bold). The `id` is only shown with `diagram.show_ids`. |
| `label` | Free text below the name on the symbol |
| `order` | Layout hint: sort key among sibling feeders (smaller = further left) |
| `pos: {x, y}` | Layout hint: fixed position of the symbol centre in mm, relative to the top-left corner of the diagram content. The subtree moves along. |
| `note` | Remark (appears in the parts list) |

### Component reference

Required fields are **bold**. Kind: *source* (connection at the bottom only), *bus*, *series*
(top/bottom, allowed in `via`), *terminal* (connection at the top only).

| Type | Kind | Fields |
|---|---|---|
| `grid` – grid / point of connection | source | **`voltage_kv`**, `sk_mva` (short-circuit power S″k) |
| `busbar` – busbar | bus | `voltage_kv` (otherwise derived from neighbours/transformer) |
| `transformer` – transformer | series | **`rating_kva`**, `ratio` (`"20/0.4 kV"`) or `hv_kv` + `lv_kv`, `uk_percent`, `vector_group` |
| `circuit_breaker` – circuit breaker | series | `state` (`closed`/`open`), `rating_a` |
| `switch_disconnector` – switch disconnector | series | `state`, `rating_a` |
| `fuse` – fuse | series | `state` (`open` = fuse link removed), `rating_a`, `fuse_type` (`"NH2 gG"`) |
| `meter` – meter | series | `direction` (`import`, `export`, `bidirectional`), `number` |
| `cable` – cable, `line` – overhead line | series | `length_m`, `cross_section_mm2`, `conductors` (`"3×1×"`), `designation` (`"NA2XS2Y"`) |
| `inverter` – inverter | series (AC on top, any number of DC inputs below) | **`kva`**, `inverter_type` (`string`/`central`/`hybrid`), `count` |
| `pv_array` – PV array | terminal (DC) | **`kwp`**, `strings`, `modules` |
| `battery` – battery storage | terminal | **`kwh`**, **`kw`**, `coupling` (`ac`/`dc`), `inverter_kva` (integrated battery inverter, drawn as well) |
| `load` – load | terminal | `kw`, `cos_phi` |
| `generator` – generator | terminal | **`kva`**, `gen_type` (CHP, diesel …) |
| `motor` – motor | terminal | **`kw`**, `starter` |
| `ev_charger` – EV charger (wallbox) | terminal | **`kw`** (per charging point), `points` |
| `grounding` – earthing | terminal | `system` (`TN-C-S` …), `resistance_ohm` |

`sld list-components -v` shows the current list with descriptions.

### Templates / macros

```yaml
templates:
  pv_feeder:
    params: {kwp: null, kva: null, strings: 20}   # null = required parameter
    entry: wr                                     # connection point from outside (default: first node)
    nodes:
      - {id: wr, type: inverter, kva: "${kva}", name: "WR ${id}"}
      - {id: pv, type: pv_array, kwp: "${kwp}", strings: "${strings}"}
    connections:
      - {from: wr, to: pv}

nodes:
  - {id: a1, template: pv_feeder, params: {kwp: 400, kva: 350}}
  - {id: a2, template: pv_feeder, params: {kwp: 400, kva: 350}, order: 1}

connections:
  - {from: nsp_a, to: a1, via: [{type: fuse, rating_a: 630}]}   # ends at a1.wr
```

* Internal nodes are called `<instance>.<id>` (`a1.wr`, `a1.pv`) and can be referenced directly.
* Connections to the instance ID end at the `entry` node. `order` and `pos` of the instance also apply to the `entry` node.
* `"${name}"` as a whole value keeps its type (a number stays a number). Inside text the value is inserted. `${id}` is the instance ID.

### Couplers, rings, multiple infeeds

Multiple `grid` nodes are allowed. A connection that closes a ring (e.g. bus coupler between two
busbars or a backup infeed) is only permitted if it contains an open switching device
(`state: open`) or carries `allow_loop: true`. Couplers between neighbouring busbars are drawn
horizontally between the busbars. A second grid feeding a busbar is routed in from above.

## Validation

Errors and warnings contain file, line and node ID:

```
anlage.yaml:23: FEHLER [E007] Knoten 'nsp': Spannungswechsel ohne Transformator: 'ms' hat 20 kV, 'nsp' hat 0,4 kV, …
anlage.yaml:9: WARNUNG [W101] Knoten 't1': Transformator (630 kVA) kleiner als angeschlossene Erzeugung (1000 kVA)
```

For YAML the line is exact. For JSON and TOML it is determined by a text search for the ID or the `from` value.

| Code | Meaning |
|---|---|
| E000 | syntax or schema error (missing/unknown field, wrong type, unknown component type) |
| E001 | duplicate ID |
| E002 | connection refers to an unknown node |
| E003 | node is not connected to anything |
| E004 | no grid connection point (`grid`) |
| E005 | sub-network not connected to a grid connection point |
| E006 | unintended loop |
| E007 | voltage change without a transformer |
| E008 | transformer ratio does not match the connected levels |
| E009 | too many connections (e.g. terminal with two connections) |
| E010 | non-series element in `via` |
| E011 | connection to itself |
| E012 | template error |
| W101 | transformer smaller than the sum of connected generators (inverters, generators, storage) |
| W102 | battery without inverter |
| W103 | PV array without inverter |
| W104 | DC-coupled battery without hybrid inverter |
| W105 | coupler between non-busbars (simplified drawing) |
| W107 | coupler is routed below the diagram |
| W201/W202 | overlap after manual positioning (`pos`) |
| W301 | diagram does not fit the paper size at full scale and is scaled down |

Voltage levels are derived: boundaries are transformers (according to `ratio`) and inverters
(DC below). A busbar therefore does not necessarily need `voltage_kv`.

## Editor integration (JSON schema)

`sld schema -o sld.schema.json` generates the schema from the pydantic model, including all
registered components and plugins. Usage:

* YAML (VS Code with the Red Hat YAML extension): first line `# yaml-language-server: $schema=./sld.schema.json`
* JSON: `"$schema": "./sld.schema.json"`
* TOML (Taplo/Even Better TOML): `#:schema ./sld.schema.json`

A test checks that the bundled `sld.schema.json` is up to date.

## Architecture

```
src/sld/
  schema/      pydantic v2 model (dynamic union of all components), templates,
               topology (spanning tree, rings), voltage analysis, validation
  io/          loaders YAML / JSON / TOML (chosen by extension) -> raw data + line map
  components/  component library: one component per file, registry with @register
  layout/      automatic layout -> purely geometric layout object (mm), paper composition
  render/      renderer interface, Pen (symbol coordinates), drawing pipeline,
               matplotlib backend (SVG/PNG/PDF)
  themes.py    din (frame, title block, band lines) / simple (coloured bands)
  cli.py
```

* `layout` does not know matplotlib. Text widths come via `TextMetrics`: the backend provides exact values, a conservative estimate is built in.
* `render.base.Renderer` only has primitives (`polyline`, `polygon`, `circle`, `text`, `save`). Another backend, e.g. direct SVG, implements these methods and declares `formats`.
* Freedom from overlaps holds by construction: each subtree occupies an interval including its labels, siblings are placed next to each other without intersection. A final collision check only moves labels if `pos` shifted something.

## Adding a new component

1. Create a new file `src/sld/components/heat_pump.py`. It is loaded automatically, the core stays unchanged:

```python
from pydantic import Field

from sld.components import Component, DrawContext, Kind, register
from sld.util import fmt_num


@register("heat_pump")
class HeatPump(Component):
    """Heat pump."""

    kind = Kind.TERMINAL        # SOURCE / BUS / SERIES / TERMINAL
    title = "Wärmepumpe"        # display name (list-components, parts list)
    ref_letter = "E"            # prefix for automatic IDs
    size = (10.0, 12.0)         # width, height of the symbol in mm

    kw: float = Field(gt=0, description="Electrical power in kW")
    cop: float | None = Field(None, gt=0, description="Coefficient of performance")

    def data_lines(self) -> list[str]:          # label on the symbol / parts list
        return [f"{fmt_num(self.kw)} kW"] + ([f"COP {fmt_num(self.cop)}"] if self.cop else [])

    def draw(self, pen, ctx: DrawContext) -> None:
        # local coordinates in mm: centre (0,0), top connection at y = -h/2, y points down
        pen.line((0, -6), (0, -5))
        pen.circle(0, 0, 5)
        pen.text(0, 0, "WP", size=6, bold=True)
```

2. Optionally override:
   * `explicit_voltage()` if the component defines a voltage level,
   * `is_dc_device()` if it works on the DC side,
   * `generation_kva()` so it counts in the transformer loading warning,
   * `is_open()` if it has a switching state (or inherit from `SwitchingDevice`),
   * `connection_limit()` or `max_connections`.
3. Check `sld list-components` and regenerate `sld schema -o sld.schema.json`.

Components from **external packages** can be added without changing this repository: either via
`sld --plugin my_package.components render …` or via an entry point in the plugin package's
`pyproject.toml`:

```toml
[project.entry-points."sld.components"]
heat_pump = "my_package.components"
```

Pen helpers: `line`, `rect`, `circle`, `ellipse`, `polygon` (`fill="fg"`/`"bg"`), `text`, `arrow`,
`sine` (~), `dc_sign` (=), `hatch`. Shared symbol parts (inverter box, battery cells, machine circle)
live in `components/_draw.py`.

## Tests

```bash
pytest
```

Covered:
* loaders: all three formats produce an identical model, line numbers
* templates
* all validation rules
* layout: no bounding-box overlaps for all examples × themes × text metrics, bands, coupler, `order`/`pos`, second infeed
* sheet: display names/hidden IDs, text wrapping, paper selection A5/A4/A3, scaling
* rendering: smoke test for SVG/PNG/PDF, deterministic SVG output, custom backend
* CLI incl. plugin component and up-to-date schema

## License

[MIT](LICENSE) – © 2026 Tim Paasche. The libraries used are under MIT or BSD-style licenses
(see [Requirements](#requirements)) and are therefore compatible.
