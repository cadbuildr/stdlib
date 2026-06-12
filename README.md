# CADbuildr Stdlib

Standard library of reusable, parametric CAD parts built on top of
[`cadbuildr-foundation`](https://pypi.org/project/cadbuildr-foundation/) — screws,
nuts, washers, bearings, motors, pulleys, extrusions and more, grounded in DIN/ISO
standards and common hardware-store sizes.

## 🔩 Live catalogue

**Browse and configure every part in your browser → [cadbuildr.github.io/stdlib](https://cadbuildr.github.io/stdlib/)**

The showcase renders each part live (it's the catalogue manifest below, made visual);
click a part to dial in its size and copy the exact `import` + call.

## Installation

```bash
pip install cadbuildr-stdlib
```

## Quick usage

```python
from cadbuildr.foundation import show
from cadbuildr.stdlib.fasteners.screws_and_bolts.din912_part import DIN912Screw
from cadbuildr.stdlib.fasteners.nuts.hex_din934_part import HexNut
from cadbuildr.stdlib.linear_motion.linear_bearings.lm_bearing_part import LinearBearing
from cadbuildr.stdlib.actuators.stepper_motors.nema_stepper_part import StepperMotor

show(DIN912Screw(size="M8", length=30))
show(HexNut(size="M8"))
show(LinearBearing(model="LM8UU"))
show(StepperMotor(frame="NEMA17", body_length=40, shaft_length=24))
```

## Categories

- **Fasteners** — socket-cap (DIN 912), hex bolts (DIN 933/931), countersunk &
  button & cheese heads, slotted screws; hex / thin / nylon-lock / square / wing /
  T-slot nuts; flat / split-lock / fender washers; threaded rods.
- **Linear Motion** — smooth rods, LMxUU linear bearings, T8 lead screw + nut.
- **Bearings** — deep-groove ball bearings (608 / 623 / 625 / 688 / 6800 …).
- **Power Transmission** — shafts, GT2 pulleys, spur gears, shaft couplings.
- **Actuators** — NEMA 14 / 17 / 23 stepper motors.
- **Profiles** — 2020 / 2040 aluminium T-slot extrusion.

The full, machine-readable list (every part, its parameters and example config) is
the catalogue manifest:

```python
from cadbuildr.stdlib.catalog import get_catalog_manifest
get_catalog_manifest()   # -> list of parts the showcase is built from
```

## Documentation

See the CADbuildr docs at [documentation.cadbuildr.com](https://documentation.cadbuildr.com).
