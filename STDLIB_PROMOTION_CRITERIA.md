# Stdlib promotion criteria

What goes into `cadbuildr-stdlib` (L1, the generic parts catalogue), what stays
in a domain library (L2: woodworking, metal, frames, tslot, electronics…) or a
project, and the bar an item must clear to graduate.

## Layers

| Layer | Package | Owns |
|---|---|---|
| L0 | `cadbuildr-foundation` | schema types, kernel client, library decorators, interface *vocabulary* + core mate rules, joints / relations, patterns, holes wizard |
| L1 | `cadbuildr-stdlib` | **purchasable, standardised hardware** any domain uses: fasteners, bearings, linear motion, power transmission, motors, profiles; their connection helpers; worked examples |
| L2 | domain libraries | process- or domain-specific parts and joinery (wood joints, weldments, sheet-metal brackets, T-slot systems, PCBs), built *on* stdlib hardware |
| L3 | tool libraries | BOM, drafting, CAM — capabilities over assemblies |
| — | projects | one product's parts (`cadbuildr_projects/*`) |

## An item belongs in stdlib when

1. **It is bought, not made** — you order it by a designation from a
   catalogue (McMaster, Misumi, a DIN/ISO/ANSI standard, a de-facto series
   like MGN, NEMA, GT2, KP08, SG90). Things you *make* (a plate, a bracket
   cut from stock, a joint) belong in a domain library or a project.
   Exception: small reference kits (motion kits, gear stage) that exist to
   show stdlib hardware working together, kept under their own category.
2. **Its dimensions come from a published table** keyed by designation
   (`OneOf[TABLE]`), with free numbers only where the catalogue has them
   (lengths). Cite the standard in `standard=`; values marked nominal when a
   de-facto series varies by maker.
3. **At least two domains need it**, or one domain needs it and it is a
   standard catalogue item (seen hand-rolled in a project or L2 library is
   the usual trigger: e.g. `PanHeadScrew`, `Servo` were hand-rolled in
   `sesame_robot`).

## The bar to merge (every item)

- `@part` / `@assembly` from `cadbuildr.foundation.library`: `category`
  (`Top/Sub`), `name`, `standard`, `description`, `catalog_id`, typed inputs
  (`OneOf`, `Num(min, max, step)`, `bool`, `Literal`) with docstring `Args:`,
  named `configurations=` for the common catalogue picks when inputs are
  numeric.
- Unknown designations / out-of-range values raise `ValueError` naming the
  choices (`common.require_option` / `require_range`); no silent clamping
  that changes what was ordered.
- Built in millimetres, rotational parts along +Z from z=0; named anchors
  whose +Z is the outward normal (faces) or the axis; an anchor contract in
  `tests/test_anchors.py`.
- An **interface** on every mating site where a type exists (foundation's
  vocabulary first; a new type goes in `cadbuildr/stdlib/interfaces.py` with
  its `@mate_rule`, and is proposed upstream to foundation once a second
  library needs it).
- Placement helpers use joints / connections / relations, never transforms.
- Every option of every input builds a DAG (`tests/test_catalog.py` does this
  automatically); presets build (`tests/test_library_practices.py`).
- `python -m cadbuildr.foundation.library manifest cadbuildr.stdlib` stays
  error-free; README category table, SKILL.md (+ mirror) and the showcase
  category order updated.

## Promotion path from a domain library or project

1. Open a funnel feature item naming the hand-rolled copies.
2. Move the class into stdlib meeting the bar above; leave a re-export (or a
   deprecated alias with `DeprecationWarning`) at the old path for one
   release.
3. Bump the stdlib minor version; publish; then bump the open mirror and the
   dependants' lower bounds (publish-first rule).

## Demotion

An item that turns out domain-specific (only one library uses it, it is
made not bought) moves out with the same deprecation window.
