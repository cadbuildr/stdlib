# Changelog

All notable changes to `cadbuildr-stdlib`. Versions follow semver; the
package pins `cadbuildr-foundation` to one minor series.

## 0.5.0 (unreleased)

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
