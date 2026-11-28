# Changelog

All notable changes to `cadbuildr-stdlib`. Versions follow semver; the
package pins `cadbuildr-foundation` to one minor series.

## 0.5.0 (unreleased)

### Standard parts (wave 2)

- `cadbuildr.stdlib.springs`: `CompressionSpring` (DIN 2095 / EN 13906-1,
  ground or closed ends, rate, solid length, `__checks__` stroke > 80 % of
  the travel to solid, index, buckling), `ExtensionSpring` (DIN 2097 / EN
  13906-2, German loop or hook), `TorsionSpring` (EN 13906-3, tangential
  legs, arbor check); wire swept along helices; `SPRING_WIRES` moduli.
- Nuts: `ISO4032Nut`, `ISO4035Nut`, `NylonInsertNut` (ISO 7040 / 10511),
  `CapNut` (DIN 1587), `FlangeNut` (DIN 6923), 30° face chamfers.
- Washers: `ISO7090Washer`, `DIN433Washer`, `ToothLockWasher` (DIN 6798 A / J).
- Pins: `ParallelPin` (ISO 2338), `SpringPin` (ISO 8752), `CoiledPin`
  (ISO 8750), `CotterPin` (ISO 1234), `ClevisPin` (ISO 2341 A / B),
  `RClip` (DIN 11024), and `pin_hole()` with the standard's fit.
- Rivets: `BlindRivet` (ISO 15977 / 15983, drill and grip range),
  `SolidRivet` (DIN 660 / 661), `rivet_hole()`.
- `WireThreadInsert` (DIN 8140) + `wire_thread_insert_hole()` (STI),
  `StudBolt` (DIN 938 / 939), `DIN976Rod` (DIN 976-1 form A).
- `cadbuildr.stdlib.hardware`: `BallKnob` (DIN 319), `FixedHandle`
  (DIN 39), `LevellingFoot` (GN 343.1 base).
- `standards.materials`: spring steel (EN 10270-1), 1.4310 (EN 10270-3),
  AlMg3 rivet alloy.
- `common.lathe_revolve` accepts profiles that lie entirely below z=0.
- CI: `.github/workflows/python.yml` (uv, Python 3.11 / 3.12, pytest).

### Sync from the monorepo (Nov-27 refactor)

- Every item is a typed `cadbuildr.foundation.library` configurable
  (`@part` / `@assembly` with `OneOf` / `Num` / `bool` inputs, named
  configurations, docstring Args); the legacy `@catalog_part` decorator is
  deprecated.
- Typed interfaces on every part (`NutSeat`, `ScrewHole`, `Shaft`, `Bore`,
  new stdlib `InsertPocket` / `InsertBody`, `RailTrack` / `RailBlock`), so
  parts connect with `assembly.connect(...)`.
- New items: set screws (ISO 4026-4029), pan-head screws (ISO 7045),
  heat-set inserts, ISO 8734 dowel pins, hex standoffs, DIN 471 / 472
  circlips, flanged / thrust bearings, KP pillow blocks, SK shaft supports,
  MGN rails + carriages, V-wheels, gear racks (`mesh_rack`), GT2 belts and
  idlers, shaft collars, RC servos + horns, motion kits, spur gear stage.
- `cadbuildr.stdlib.standards`: ISO 286 fits, ISO 261 / 724 / 2306 / 273
  threads and holes, DIN 974 counterbores, heat-set inserts, DIN 6885 keys,
  O-rings (AS568 / ISO 3601), Renard / E series, materials, ISO 1302 /
  2768, Tr / BSP / NPT threads, wood pilots, hole features and cuts.
- `examples/` package (bolted plate, motor + lead screw, gear pair, rack and
  pinion, rail slide, PCB on standoffs); library manifest entry point.
- Requires `cadbuildr-foundation>=0.3.0,<0.4.0` (`__checks__`, `owner_of`,
  compact geometry, joints / interfaces).

## 0.4.0

- Anchors on every fastener, connection helpers, involute spur gears.
