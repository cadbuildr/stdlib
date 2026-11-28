---
name: cadbuildr-stdlib
description: The CADbuildr parts catalog — fasteners (screws, nuts, washers, set screws, heat-set inserts, dowel pins, standoffs), bearings (incl. flanged, thrust, pillow blocks), MGN rails, gears + racks, steppers, servos, profiles — every part carries anchors and typed interfaces; place hardware with assembly.connect / connect_with_screw / connect_with_bolt_and_nut / connect_heat_set_insert / mesh_gears / mesh_rack / mount_carriage instead of transform math.
---

# cadbuildr-stdlib

The parts catalog every CADbuildr project stands on. **Never model
standard hardware by hand — import it.** Needs
`cadbuildr-foundation>=0.2.19`.

```python
from cadbuildr.stdlib.fasteners import (
    DIN912Screw, HexBolt, ButtonHeadSocketScrew, CountersunkSocketScrew,
    PanHeadScrew, SetScrew, WoodScrew,           # screws
    HexNut, NylonLockNut, TSlotNut, DIN125Washer, # nuts / washers
    HeatSetInsert, DowelPin, HexStandoff,         # inserts, pins, standoffs
    connect_with_screw, connect_with_bolt_and_nut, connect_heat_set_insert,
)
from cadbuildr.stdlib.bearings import DeepGrooveBearing, FlangedBearing, ThrustBearing, PillowBlock
from cadbuildr.stdlib.linear_motion.rails import LinearRail, RailCarriage, mount_carriage
from cadbuildr.stdlib.power_transmission.gears import SpurGear, GearRack, mesh_gears, mesh_rack
from cadbuildr.stdlib.actuators.servos import Servo, ServoHorn
from cadbuildr.stdlib.power_transmission.pulleys import GT2Pulley, GT2Idler, GT2Belt, belt_drive, gt2_center_distance
from cadbuildr.stdlib.power_transmission.shafts.shaft_collar_part import ShaftCollar
from cadbuildr.stdlib.fasteners.retaining_rings import ExternalCirclip, InternalCirclip
from cadbuildr.stdlib.linear_motion.rollers import VWheel
```

Before building a substitute, list what exists:
`python -m cadbuildr.foundation.library manifest cadbuildr.stdlib`
(or `cadbuildr.stdlib.catalog.get_catalog_entries()`). Every item takes
typed inputs (sizes are table keys: `"M3"`, `"608"`, `"MGN12"`, `"SG90"`);
a wrong key raises `ValueError` listing the valid ones.

## Place parts with interfaces and anchors, not transforms

Every part has named **anchors** (+Z = outward normal of a face, or the
part axis) and typed **interfaces** on its mating sites. Prefer
`assembly.connect(a.interface(x), b.interface(y))`: the mate rule picks
the joint and checks sizes; `assembly.check()` reports what is left.

```python
asm.ground(motor)
asm.connect(motor.interface("shaft_tip"), coupling.interface("bore_a_stop"))  # ShaftEnd -> Bore
asm.connect(screw.interface("end_a"), coupling.interface("bore_b_stop"))
asm.connect(screw.interface("axis"), nut.interface("axis"), offset=120)       # Shaft <-> Bore
asm.connect(carriage.interface("datum"), rail.interface("datum"), offset=80)  # RailBlock <-> RailTrack
```

| Part | Anchors (interfaces) |
|---|---|
| Screws & bolts | `head_seat` (ScrewHead), `tip` (ScrewTip) |
| Nuts, washers | `bottom` (NutSeat), `top`, `axis` (washers: `top` ScrewHole) |
| `DeepGrooveBearing`, `FlangedBearing`, `ThrustBearing` | `bottom` / `top` (BearingFace), `axis` (Bore); flanged + `flange_seat` |
| `HeatSetInsert` | `top` (tapped ScrewHole), `seat` (InsertBody), `bottom`, `axis` |
| `DowelPin`, rods, shafts, `RoundTube` | `end_a` / `end_b` (ShaftEnd / RodEnd), `axis` (Shaft / RodAxis) |
| `HexStandoff` | `bottom` / `top` (NutSeat), male-female + `stud_tip` (ScrewTip) |
| `PillowBlock`, `ShaftSupport` | `bottom` (PlaneFace), `axis` (Bore; +Z = part +Y), `mount_hole_0/1` (ScrewHole); SK: `rod_hole` (RodHole) |
| `LinearRail` | `datum` (RailTrack: +Z along rail, +X up), `bottom`, `top`, `mount_hole_<i>` (ScrewHole at the counterbore floor) |
| `RailCarriage` | `datum` (RailBlock, block centre), `top` (PlaneFace), `mount_hole_0..3` (tapped) |
| `SpurGear` / `GearRack` | `pitch_plane`, `axis` (Bore) / `slide`, `back`, `end_a`, `end_b` |
| `StepperMotor` | `mount_face` (NemaBody), `shaft` (Shaft), `shaft_tip`, `mount_hole_0..3` |
| `Servo` | `mount_face` (ears, outward -Z), `shaft` (Shaft), `horn` (ShaftEnd), `mount_hole_0/1` |
| `ServoHorn` | `spline_stop` (Bore: `connect(servo.interface("horn"), horn.interface("spline_stop"))`), `arm_tip_<i>` |
| `ShaftCollar` | `axis` (Bore, slides on a Shaft by `offset`), `bottom` / `top` (PlaneFace), `set_screw` or `clamp_screw` (ScrewHole) |
| `ExternalCirclip` / `InternalCirclip` | `axis` (Bore d1 on a shaft / Shaft d1 in a bore), `bottom` / `top` |
| `GT2Idler`, `GT2Belt` | idler: `belt_plane`, `axis` (Bore) / belt: `pulley_a`, `pulley_b`, `back` |
| `VWheel` | `axis` (Bore 5), `contact` (V ridge tip, +Z radial) |
| `AluExtrusion` | `end_a`, `end_b`, `axis`, `slot_*` (TSlot); `slot_anchor(name, at=)` slides along |

A component is placed by one joint only and its parent must already be
placed. Keep the part handles: anchors are queried on the part you built.

## Connection helpers

- `connect_with_screw(asm, screw, hole_anchor, drill=True, into=None, into_depth=None)`
  — seats the head on the anchor, drills the clearance hole; `into=` an
  anchor on the part underneath cuts its tap-drill hole (rail on a base).
- `connect_with_bolt_and_nut(asm, bolt, nut, hole_anchor, grip=8, head_washer=..., nut_washer=...)`
  — through-bolt; raises if the bolt is too short.
- `connect_heat_set_insert(asm, insert, face_anchor)` — insert flush in
  the face, pocket cut. Then screw into `insert.anchor("top")` with
  `drill=False`.
- `mesh_gears(asm, driver, driven, angle=0, driver_joint=None)` — `RevoluteJoint`
  at r1 + r2, tooth-in-gap. Pass the driver's own `RevoluteJoint` as
  `driver_joint` and the pair is coupled by a `GearRelation`:
  `driver_joint.set_angle(a)` turns the driven gear `-a·z1/z2` (trains animate).
- `belt_drive(asm, driver_pulley, driven_pulley, center_distance, angle=0)` —
  places the driven pulley on the driver's `belt_plane` and wraps a toothed
  `GT2Belt` (`belt.teeth`, `belt.ratio`); `gt2_center_distance(400, 20, 20)`
  gives the centre distance for a catalogue closed belt.
- `mesh_rack(asm, pinion, rack, pinion_joint)` — rack on a `SliderJoint`
  tangent to the pitch circle plus a `RackPinionRelation`:
  `pinion_joint.set_angle(a)` slides the rack `r·a`. The pinion joint's
  child anchor must be `axis` or `pitch_plane`; modules must match.
- `mount_carriage(asm, rail, carriage, at=)` — `SliderJoint`, `at` = block
  centre along the rail; raises on series mismatch or overhang.
- `tube_tee(asm, branch, main, at=)` — coped tube tee.

## Sizes and lengths

- `length` is the standard's nominal length: **under the head** for cap,
  button, pan, cheese-head screws and hex bolts; **overall** for
  countersunk, wood and set screws (they sit flush).
- `WoodScrew(gauge, length)`: gauges "4"–"12" (#8 × 32 is the workhorse);
  its interfaces carry `#8`, not `M4.2`.
- `SetScrew(size, length, point)`: `flat` / `cone` / `dog` / `cup`; too
  short for its socket + point raises.
- `HexStandoff(size, length, kind)`: `length` is the body (spacing);
  `male-female` adds a stud.
- `GearRack(module, length)` rounds down to an even tooth count (a gap at
  its `slide` origin). Gears and racks have ISO 53 root fillets (0.38 m);
  `SpurGear(..., hub_length=8)` adds a set-screw hub (`hub_end`, `set_screw`).
- `LeadScrewT8(length, lead="8")` is the printer Tr8x8: DIN 103 trapezoidal
  30°, 4 starts, **8 mm per turn** (`lead="2"`: Tr8x2 single start). Use
  `screw.lead` (not `pitch`) for a `ScrewRelation`; the nut takes the same `lead`.
- `GT2Pulley` has a 7 mm set-screw hub by default (`set_screw_0/1`, M3:
  `connect_with_screw(asm, SetScrew("M3", 4, "cup"), p.anchor("set_screw_0"), drill=False)`);
  `hub=False` for a pulley used as an idler.

## Worked examples

`cadbuildr.stdlib.examples`: `bolted_plate`, `motor_leadscrew_stack`,
`gear_pair`, `rack_and_pinion(angle)`, `rail_slide(at)`,
`pcb_on_standoffs(standoff_length)`; `build_<name>()` also returns the part
handles and joints. For wood slat construction prefer
`cadbuildr.woodworking.screwed_overlap`; for T-slot frames, `cadbuildr.tslot`.

## Verify before you claim success

Instantiate the part in Python first; run `assembly.check()`; then
`show(...)` and confirm the render (a wood screw has a point, a machine
screw does not; a placed nut sits on the far face, not in the plate; a
rack's teeth sit in the pinion's gaps).
