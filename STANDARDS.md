---
name: cadbuildr-stdlib-standards
description: Engineering standards data in cadbuildr.stdlib.standards — ISO 286 fits (fit("H7/g6", 10)), metric/UNC/UNF threads with tap drills and ISO 273 clearance holes, counterbores/countersinks, screw lengths, Tr lead-screw / BSP / NPT pipe threads, wood pilot holes, heat-set inserts, self-tapping into plastic, DIN 6885 keys, DIN 471/472 circlips, O-ring glands, preferred numbers/sheet gauges/stock, materials (density, E, yield, cost), surface finish, ISO 2768 general tolerances — plus hole features that bind ScrewHole/Bore interfaces so stdlib screws connect, and shaft cuts (D-flats, keyways, circlip and O-ring grooves, captive-nut pockets).
---

# cadbuildr.stdlib.standards

**Never type a tap drill, clearance diameter, H7 limit, density or O-ring
groove by hand — look it up.** Every number a part needs to be made and
assembled is a cited table plus a small function here. Lengths are mm;
lookups raise `StandardsError` (`UnknownSize` with "did you mean",
`OutOfRange`) instead of guessing.

```python
from cadbuildr.stdlib.standards import (
    fit, tolerance, bearing_fit, printed_clearance,          # ISO 286
    thread, tap_drill, clearance_diameter, counterbore, countersink, screw_length,
    heat_set_insert, self_tap_hole,                           # plastics
    keyway, circlip_shaft, circlip_bore, gland, piston_groove, oring,
    preferred, sheet_gauge, stock_size,
    material, materials_for,
    ra_grade, general_tolerance,
    tapped_hole, clearance_hole, counterbored_hole, countersunk_hole,
    heat_set_insert_hole, self_tap_screw_hole, fitted_bore,  # features
)
```

## Fits (ISO 286)

```python
f = fit("H7/g6", 10)
f.hole.limits, f.shaft.limits     # (10.0, 10.015), (9.986, 9.995)
f.min_clearance, f.max_clearance  # 0.005, 0.029 (negative = interference)
f.kind                            # "clearance" | "transition" | "interference"
tolerance("k6", 8).mean           # 8.0055 -> the size to model
bearing_fit("k6", 8)              # shaft vs the ISO 492 bearing bore (0/-8 µm): interference
bearing_fit("H7", 22, ring="outer")
printed_clearance("sliding", "fdm")  # 0.3 mm diametral for printed parts (not ISO 286)
```

Pick: `H7/g6` sliding, `H7/h6` locating, `H7/k6` bearing inner ring on a
rotating shaft (`BEARING_SEATS` lists the usual cases), `H7/p6` press,
`H8/f7` running, `H11/c11` loose. Model the zone **mean**; printed parts use
`printed_clearance` instead.

## Threads and holes

```python
t = thread("M6")         # also "M10x1.25", "1/4-20", "#10-32"
t.tap_drill              # 5.0   (ISO 2306)
t.clearance("close")     # 6.4   close / normal / loose = ISO 273 fine / medium / coarse
t.minor_internal, t.pitch_diameter, t.stress_area
counterbore("M5")        # Counterbore(diameter=10.0, depth=5.4, hole=5.5)  ISO 4762 heads
countersink("M4")        # Countersink(diameter=8.96, angle=90.0, ...)       ISO 10642 heads
screw_length("M5", grip=8, engagement=1.5)  # 16: next ISO 4762 length
```

Engagement: 1 d into steel, 1.5 d into aluminium / cast iron, 2 d into plastics.

## Lead-screw, pipe and wood threads

```python
trapezoidal("Tr8x2")          # d3 5.5, D1 6.0 (nut drill), d2 7.0 (ISO 2904)
trapezoidal("Tr8x8(P2)")      # printer lead screw: lead 8, pitch 2, 4 starts
pipe_thread("G1/4")           # BSP parallel: 13.157 mm, 19 TPI, drill 11.8
pipe_thread("Rc1/2").taper    # "1:16" (BSP taper); pipe_thread("1/4 NPT") -> drill 7/16 in
wood_pilot("#8", "hardwood")  # pilot 3.17, clearance 4.37, min edge distance
wood_pilot(5.0, "softwood")   # metric: pilot 2.5 (0.5 d), clearance 5.5
```

## Holes that connect (features)

Each feature cuts the hole into the anchor's part **and** binds the
interface, keeping the nominal size on the interface:

```python
holes = plate.anchor("top").offset([-15, 0, 0], name="hole").linear_pattern(2, 30.0)
plate.add_anchors(holes)
for a in holes:
    counterbored_hole(a, "M5", depth=10, group="bolts")   # ScrewHole on the counterbore floor
for a in block_holes:
    tapped_hole(a, "M5", depth=12, group="tapped")        # ScrewHole(thread=True)

asm.ground(block)
asm.connect(plate.interface("bottom"), block.interface("top"))   # PlaneFace <-> PlaneFace
L = screw_length("M5", plate_grip)
asm.connect_all(lambda: DIN912Screw("M5", L, with_thread=False), plate.group("bolts"))
asm.check()   # []
```

`tapped_hole` cuts the real drilled shape: tap-drill bore to `depth` + 3 P
runout (`drill_depth=` to override), 118 degree drill point, 90 degree
countersink to 1.05 d at the mouth (`chamfer=False` to drop it); the helix is
not modelled (cosmetic thread). Also: `clearance_hole(a, "M6", depth, "close")`, `countersunk_hole(a, "M4", depth)`,
`heat_set_insert_hole(a, "M3")` (printed bosses; a screw connects to it like
a tapped hole), `self_tap_screw_hole(a, "M3", material="ABS")`,
`fitted_bore(a, 22, "H7", depth=7)` (binds `Bore(d=22, fit="H7")`). Each
returns `HoleFeature(operation, interface, seat, spec, diameter)`. The anchor
must be registered on the part (`part.add_anchor`) first.

## Plastics, shafts, seals

```python
heat_set_insert("M3")         # hole 4.0, length 5.7, depth 6.7, boss ...
self_tap_hole(3, "PC")        # pilot 2.55 (0.85 d), boss 7.5, engagement 6
keyway(20)                    # DIN 6885 A 6 x 6, t1 3.5 (shaft), t2 2.8 (hub)
circlip_shaft(8); circlip_bore(22)   # DIN 471 / 472 groove Ø, width, ring thickness
gland(1.78, "static_radial")  # depth = cs (1 - squeeze), width from 70 % fill
piston_groove(bore=20, cs=1.78)      # groove Ø + the AS568 ring (stretch 0-5 %)
```

## Shaft, hub, seal and nut cuts

Shaft / hub cuts work in the part frame on a body built along +Z (stdlib
convention), ``z0`` along the axis; each returns the table row it used:

```python
d_flat(shaft, d=5, z0=10, length=15)              # NEMA 17 D-cut, flat at 4.5
shaft_keyway(shaft, d=20, z0=5, length=28)        # DIN 6885 6 x 6, t1 3.5, round ends (form A)
shaft_end_chamfer(shaft, d=20, z=120, size=1)     # 45 deg end chamfer
hub_keyway(hub, bore=20, z0=0, length=25)         # t2 2.8 beyond the bore
circlip_groove(shaft, d=8, z=30)                  # DIN 471; kind="bore" -> DIN 472
oring_groove(piston, bore=20, cs=1.78, z=10)      # gland + the AS568 ring (.ring)
captive_nut_pocket(part.anchor("under"), "M3")    # hex pocket + ScrewHole on its floor
asm.connect(HexNut("M3"), part.interface("under_nut"))   # NutSeat <-> ScrewHole
```

Parts: `ParallelKey(shaft_d, length)`, `ORingSeal(size)` (AS568 torus),
`KeyedShaft` (keyway + 2 circlip grooves + optional D-flat),
`CaptiveNutBlock` / `CaptiveNutDemo` (nuts in pockets, screws through,
`check()` clean) — in `cadbuildr.stdlib.standards.shaft_parts`.

## Materials, stock, finish, general tolerances

```python
m = material("6061-T6")       # also keywords: material("stainless steel A2")
m.density, m.E, m.yield_mpa, m.cost_per_kg, m.processes, m.machinability
m.mass_kg(volume_mm3); m.cost(volume_mm3)
materials_for("fdm")          # PLA, PETG, ABS, ASA, PA-CF, TPU
preferred(37, "R20")          # 35.5 (Renard); "E12" for resistors
sheet_gauge(16, "steel")      # 1.519 mm; stock_size(13, "sheet") -> 15
ra_grade(1.6)                 # "N7"; standards.surface.RA_FOR["bearing seat (shaft)"] = 0.8
general_tolerance(45, "m")    # ±0.3 (ISO 2768-m); flatness_tolerance(200, "K") -> 0.4
```

## Configurable demos (viewer: Stdlib tab, Standards section)

Plain classes until declared: call
`cadbuildr.stdlib.standards.demos.register()` once (top of `main.py`) to make
them `stdlib:<Class>` library items with a configuration bar.

`BearingFitDemo` (bearing / housing_tolerance / shaft_tolerance /
`exaggerate` — the shaft turns green / amber / red with the fit kind),
`BoltedJointDemo` (size / n / plate_thickness / holes / engagement),
`FittedHousing`, `FittedShaft`, `TappedBlock`, `ClampPlate`,
`FitTestCoupon` (print one, measure, pick your clearance), `ParallelKey`,
`ORingSeal`, `KeyedShaft`, `CaptiveNutBlock`, `CaptiveNutDemo`.

## Rules

- Interfaces carry the **nominal** (`ScrewHole(size="M5")`, `Bore(d=22)`);
  geometry carries the toleranced / drilled size.
- Do not copy a table into your library; import it. If a value is missing,
  add it here with its source in the module docstring.
- Values are nominal handbook data for design and estimates, not
  certification: check vendor datasheets (inserts, bearings, prices).
