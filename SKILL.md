---
name: cadbuildr-stdlib
description: The CADbuildr parts catalog — fasteners (incl. WoodScrew), bearings, gears, motors, profiles — every part carries mate anchors; place hardware with connect_with_screw / connect_with_bolt_and_nut / mesh_gears and joints instead of transform math.
---

# cadbuildr-stdlib

The parts catalog every CADbuildr project stands on: fasteners,
bearings, gears, motors, extrusion profiles, linear motion. **Never
model standard hardware by hand — import it.** Needs
`cadbuildr-foundation>=0.2.19`.

```python
from cadbuildr.stdlib.fasteners import (
    WoodScrew,             # gauge-sized, pointed, countersunk (wood)
    DIN912Screw,           # socket head cap (machine)
    HexBolt, HexNut, DIN125Washer,
    connect_with_screw,
    connect_with_bolt_and_nut,
)
from cadbuildr.stdlib.power_transmission.gears import SpurGear, mesh_gears
```

## Place parts with anchors, not transforms

Every catalog part has named **mate anchors**. An anchor's +Z is the
outward normal of its face (or the part axis for `axis`-style anchors),
so a default `RigidJoint(parent_anchor=..., child_anchor=...)` brings two
faces into contact. Rotational parts are built along +Z from z=0.

| Part | Anchors |
|---|---|
| All screws & bolts | `head_seat`, `tip` |
| Nuts, washers, `DeepGrooveBearing` | `bottom`, `top`, `axis` |
| `TSlotNut` | + `flange_seat` (`top` = neck top, flush with the slot) |
| `SpurGear` | + `pitch_plane` (mid face width, +X through tooth 0) |
| `GT2Pulley` | + `belt_plane` |
| Rods, shafts, `LeadScrewT8`, `RoundTube` | `end_a`, `end_b`, `axis` |
| `LinearBearing` (LMxUU) | `end_a`, `end_b`, `axis`, `center` |
| `LeadScrewNutT8` | `bottom`, `top`, `axis`, `flange_seat`, `mount_hole_0..3` |
| `ClampCoupling` | `end_a`, `end_b`, `axis`, `bore_a_stop`, `bore_b_stop` |
| `StepperMotor` | `mount_face`, `shaft`, `shaft_tip`, `back`, `mount_hole_0..3` |
| `AluExtrusion` | `end_a`, `end_b`, `axis`, `slot_px_<i>`, `slot_nx_<i>`, `slot_py`, `slot_ny` |

`AluExtrusion.slot_anchor("slot_py", at=50)` slides a slot anchor along
the profile (T-nut `top` mates there). `RoundTube.radial_anchor(at, angle)`
does the same on a tube surface.

```python
assembly.add_component(motor)
assembly.add_joint(RigidJoint(parent_anchor=motor.anchor("shaft_tip"),
                              child_anchor=coupling.anchor("bore_a_stop")))
assembly.add_joint(RigidJoint(parent_anchor=coupling.anchor("bore_b_stop"),
                              child_anchor=lead_screw.anchor("end_a")))
```

A component can be placed by one joint only, and the parent must
already be placed. Keep the part handles: anchors are queried on the
part you built, not on `assembly.components`.

## Screws and the fastener contract

- `WoodScrew(gauge, length)` — gauges "4"/"6"/"8"/"10"/"12" (#8 × 32mm
  is the workhorse). Pointed tip, ~82° countersunk head that seats
  flush. Too-short lengths raise (min ≈ 2.5× the gauge diameter).
- Machine screws: `DIN912Screw` (M2–M24), `HexBolt`, `CheeseHeadSlottedScrew`,
  `CountersunkSlottedScrew`, `CountersunkSocketScrew`,
  `ButtonHeadSocketScrew` (metric M3–M10+). `HexNut` covers M2–M24.
- `length` is the standard's nominal length. **Under the head** for cap,
  button, cheese-head screws and hex bolts (`DIN912Screw("M3", 10)` has a
  10 mm shank + 3 mm head). **Overall, head included** for countersunk and
  wood screws (they sit flush, so `length` is what goes into the part).

Every screw subclasses `Fastener`: `body_radius` / `body_height` attrs +
`head_seat` (under-head face; for countersunk heads the flush head top)
and `tip` anchors. `is_fastener(x)` checks the contract; anything
honouring it works in the helpers below.

## Connection helpers

- `connect_with_screw(assembly, screw, hole_anchor)` — seats the screw
  on the anchor (+Z out of the face) and drills the clearance hole.
- `connect_with_bolt_and_nut(assembly, bolt, nut, hole_anchor, grip=8,
  head_washer=DIN125Washer("M8"), nut_washer=DIN125Washer("M8"))` —
  through-bolt; drills through `grip`, stacks washers, puts the nut on
  the far face (or pass `exit_anchor=`). Raises if the bolt is too short.
- `mesh_gears(assembly, driver, driven, angle=0.0)` — `RevoluteJoint`
  at centre distance r1 + r2 (pitch radii), phased tooth-in-gap.
- For wood slat construction prefer `cadbuildr.woodworking.screwed_overlap`.

Worked examples: `cadbuildr.stdlib.examples` (`bolted_plate`,
`motor_leadscrew_stack`, `gear_pair`).

## Other catalogs

`cadbuildr.stdlib.bearings` (608 and friends), `power_transmission`
(gears, pulleys, couplings, shafts), `profiles` (tubes, extrusions),
`linear_motion`, `actuators`. Check
`cadbuildr.stdlib.catalog.get_catalog_entries()` to enumerate what
exists before building a substitute.

## Verify before you claim success

Instantiate the part in Python first; then `show(...)` and confirm the
render (thread/head shapes are visible — a wood screw has a point, a
machine screw does not; a placed nut sits on the far face, not in the
plate).
