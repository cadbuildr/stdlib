# CADbuildr Stdlib

## Summary

Standard library of reusable, parametric CAD parts built on top of
[`cadbuildr-foundation`](https://pypi.org/project/cadbuildr-foundation/) — screws,
nuts, washers, inserts, pins, standoffs, bearings, rails, gears, racks, motors,
servos, pulleys, extrusions and more, grounded in DIN/ISO standards and common
hardware-store sizes. Every item is a `cadbuildr.foundation.library`
configurable (`@part` / `@assembly` with typed inputs and named
configurations), carries named **anchors** and typed **interfaces**, and is
placed with joints / `assembly.connect(...)` / the connection helpers — never by
transform math.

**Browse and configure every part in your browser →
[cadbuildr.github.io/stdlib](https://cadbuildr.github.io/stdlib/)** (the
catalogue manifest made visual; `github-io/`).

```bash
pip install cadbuildr-stdlib
```

```python
from cadbuildr.foundation import show
from cadbuildr.stdlib.fasteners import DIN912Screw, HexNut, HeatSetInsert, SetScrew
from cadbuildr.stdlib.bearings import DeepGrooveBearing, PillowBlock
from cadbuildr.stdlib.linear_motion.rails import LinearRail, RailCarriage
from cadbuildr.stdlib.power_transmission.gears import SpurGear, GearRack, mesh_rack
from cadbuildr.stdlib.examples import rack_and_pinion

show(DIN912Screw(size="M8", length=30))
show(rack_and_pinion(angle=0.5))
```

| Category | Items |
|---|---|
| Fasteners — screws & bolts | DIN 912 / ISO 4762 cap, DIN 933/931 hex bolt, ISO 7380 button, DIN 7991 countersunk socket, DIN 84 / 963 slotted, ISO 7045 pan head, ISO 4026-4029 set screws, wood screws |
| Fasteners — nuts | DIN 934 hex, **ISO 4032** hex, **ISO 4035** thin, DIN 439 thin, DIN 985 / **ISO 7040 / ISO 10511** nylon insert, **DIN 1587** cap, **DIN 6923** flange, DIN 557 square, DIN 315 wing, T-slot nuts |
| Fasteners — washers | DIN 125 / ISO 7089, **ISO 7090** chamfered, **DIN 433 / ISO 7092** small, DIN 9021 / ISO 7093, DIN 127 split lock, **DIN 6798 A / J** serrated lock |
| Fasteners — pins & clips | ISO 8734 dowel, **ISO 2338** parallel, **ISO 8752** slotted spring, **ISO 8750** coiled, **ISO 1234** split, **ISO 2341** clevis (A / B), **DIN 11024** R-clip — each with `pin_hole` |
| Fasteners — rivets | **ISO 15977 / 15983** blind rivets (drill, grip range), **DIN 660 / 661** solid rivets — with `rivet_hole` |
| Fasteners — inserts, studs, rods | heat-set inserts, **DIN 8140** wire thread inserts (`wire_thread_insert_hole`), **DIN 938 / 939** studs, **DIN 976-1** and DIN 975 threaded rod, hex standoffs, DIN 471 / 472 circlips |
| Springs | **DIN 2095 / EN 13906-1** compression (ground / closed ends, rate, solid length, stroke check), **DIN 2097 / EN 13906-2** extension (German loop / hook), **EN 13906-3** torsion — real swept helices |
| Hardware | **DIN 319** ball knobs, **DIN 39** fixed handles, levelling feet |
| Bearings | deep groove 6xx/68xx, flanged F6xx, thrust 511xx, KP pillow blocks |
| Linear motion | smooth rods, LMxUU bearings, SK shaft supports, T8 lead screw + nut, MGN7–15 and HGR15/20 rails + carriages, V-wheels |
| Power transmission | spur gears, gear racks, GT2 pulleys / idlers / closed belts, clamp couplings, shafts, shaft collars |
| Actuators | NEMA 14/17/23 steppers, SG90 / MG90S / MG996R servos + horns |
| Profiles | 2020 / 2040 T-slot extrusion, round tube (`tube_tee`) |
| Kits | motion-kit plates / carriages / brackets, spur gear stage + gearbox plates |
| Standards | `cadbuildr.stdlib.standards`: ISO 286 fits, threads and holes, inserts, keys, circlips, O-rings, materials, surface / general tolerances |

Items in **bold** are new in 0.5.0 (standard parts wave 2).

### Quickstart: a pinned clevis and a checked spring

```python
from cadbuildr.foundation import Assembly, show
from cadbuildr.stdlib.fasteners import ClevisPin, CotterPin
from cadbuildr.stdlib.springs import CompressionSpring

pin = ClevisPin("8", 30, "B")              # ISO 2341 form B, split-pin hole d1 = 2
asm = Assembly()
asm.ground(pin)
asm.connect(CotterPin("2", 16), pin.interface("split_pin"))   # ISO 1234 into the hole

spring = CompressionSpring(wire_diameter=1.6, mean_diameter=12, free_length=40,
                           active_coils=7, ends="ground", stroke=22)
spring.rate            # 5.52 N/mm  (EN 13906-1: G d^4 / 8 D^3 n)
spring.solid_length    # 14.4 mm    (nt d, ground)
spring.check()         # warning: stroke 22 mm is 86 % of the travel to solid
show(asm)
```

Connection helpers: `connect_with_screw` (incl. `into=` tapped hole in the part
underneath), `connect_with_bolt_and_nut`, `connect_heat_set_insert`,
`mesh_gears` (`driver_joint=` couples a gear train by `GearRelation`), `mesh_rack`
(rack-and-pinion joint relation), `belt_drive` (pulley pair + GT2 belt), `mount_carriage`,
`tube_tee`. Worked examples: `cadbuildr.stdlib.examples` (`bolted_plate`,
`motor_leadscrew_stack`, `gear_pair`, `rack_and_pinion`, `rail_slide`,
`pcb_on_standoffs`).

The machine-readable list is the library manifest:

```bash
python -m cadbuildr.foundation.library manifest cadbuildr.stdlib
```

(`cadbuildr.stdlib.catalog.get_catalog_manifest()` is the showcase's view of
the same registry.) What belongs here vs a domain library:
[`STDLIB_PROMOTION_CRITERIA.md`](STDLIB_PROMOTION_CRITERIA.md). Agent-facing
usage: [`SKILL.md`](SKILL.md).

## Tags

cad, python, library, parts-catalog, fasteners, springs, rivets, pins, bearings, linear-motion, gears, motors, interfaces, din, iso

## Status

green

## Guidelines

- Declare every item with `@part` / `@assembly`: typed inputs, category, catalog_id, docstring Args.
- Dimensions come from a standard's table keyed by designation; unknown keys raise naming choices.
- Every part has anchors (+Z = outward normal or axis) and an interface where a type exists.
- Place parts with joints, `assembly.connect` and connection helpers — never translate / tf=.
- New items need an anchor contract in tests/test_anchors.py; every option must build a DAG.
- Units are millimetres; rotational parts are built along +Z from z=0.
- Every dimension is cited in the docstring (standard table or datasheet URL); values that are not are listed under `Estimated:`.
- Threads, holes, fits and materials come from `cadbuildr.stdlib.standards`, not literals.
- Design checks go in a `__checks__` hook (never override `check()`); tests check geometry (volumes, extents) against the tables.
- Keep the public API backward-compatible: deprecate (DeprecationWarning), do not break.

## Dependencies

### Upstream

- `cadbuildr-foundation`

### Downstream

- `cadbuildr-woodworking` (wood screws, connections)
- `cadbuildr-electronics`
- `cadbuildr-tslot` (aluminium extrusion interop)
- `cadbuildr-demo-skate` (bearing table)
- CADbuildr example projects (sesame_robot, playground, lego, puzzle)
- the CADbuildr curated library registry
