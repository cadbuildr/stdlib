"""Engineering materials: density, stiffness, strength, indicative cost, process flags.

::

    m = material("6061-T6")          # Material(density=2700 kg/m³, E=68.9 GPa, ...)
    m.mass_kg(125_000)               # 0.3375 kg for 125 cm³
    m.cost(125_000)                  # 1.52 (USD, indicative)
    material("stainless steel A2")   # keyword match -> stainless_304
    materials_for("fdm")             # [PLA, PETG, ABS, ASA, ...]

Values are nominal room-temperature handbook figures (MatWeb / supplier
datasheets / ASM; EN 10025 / EN 10088 / EN 573 / EN 485 grades), to size
and estimate, not to certify: yield is the 0.2 % proof stress in the stated
temper (``None`` for brittle or elastomeric materials), printed-polymer
values are for typical FDM parts along the layers. ``cost_per_kg`` is an
indicative small-quantity USD price (2025 stock / filament), only for
early cost roll-ups; override it with your supplier's price.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional

from ._common import UnknownSize

__all__ = [
    "MATERIALS",
    "Material",
    "material",
    "materials_for",
]

PROCESSES = ("cnc", "sheet", "weld", "cast", "laser", "fdm", "sla", "sls", "wood")


@dataclass(frozen=True)
class Material:
    """One material. Units: density kg/m³, ``E`` GPa, ``yield_mpa`` / ``uts_mpa`` MPa."""

    key: str
    name: str
    family: str  # steel / stainless / aluminium / copper / titanium / iron / polymer / composite / wood / elastomer
    density: float
    E: float
    yield_mpa: Optional[float]
    uts_mpa: Optional[float]
    cost_per_kg: float
    processes: FrozenSet[str] = field(default_factory=frozenset)
    machinability: str = "n/a"  # excellent / good / fair / poor / n/a
    keywords: tuple = ()
    sheet_metal: Optional[str] = None  # foundation.sheet_metal_materials key
    color: Optional[str] = None  # a render colour (hex)

    @property
    def printable(self) -> bool:
        """True for FDM / SLA / SLS materials."""
        return bool(self.processes & {"fdm", "sla", "sls"})

    @property
    def machinable(self) -> bool:
        return "cnc" in self.processes

    @property
    def specific_stiffness(self) -> float:
        """E / density, MN·m/kg (higher = stiffer for the weight)."""
        return round(self.E * 1e3 / self.density, 3)

    def mass_kg(self, volume_mm3: float) -> float:
        """Mass of ``volume_mm3`` mm³ in kg."""
        return float(volume_mm3) * 1e-9 * self.density

    def cost(self, volume_mm3: float) -> float:
        """Indicative raw-material cost (USD) of ``volume_mm3`` mm³ (no scrap / machining)."""
        return round(self.mass_kg(volume_mm3) * self.cost_per_kg, 4)


def _m(
    key,
    name,
    family,
    density,
    E,
    ys,
    uts,
    cost,
    processes,
    mach="n/a",
    keywords=(),
    sheet=None,
    color=None,
):
    return Material(
        key=key,
        name=name,
        family=family,
        density=float(density),
        E=float(E),
        yield_mpa=ys,
        uts_mpa=uts,
        cost_per_kg=float(cost),
        processes=frozenset(processes),
        machinability=mach,
        keywords=tuple(keywords),
        sheet_metal=sheet,
        color=color,
    )


# fmt: off
_ALL: List[Material] = [
    # Steels
    _m("s235", "Structural steel S235JR (EN 10025-2)", "steel", 7850, 210, 235, 360, 1.2,
       {"cnc", "sheet", "weld", "laser"}, "good", ("s235", "mild steel", "a36", "structural steel", "steel"),
       "hot_rolled_steel", "#7d8288"),
    _m("dc01", "Cold-rolled steel DC01 / SAE 1008", "steel", 7870, 210, 170, 300, 1.4,
       {"sheet", "weld", "laser"}, "good", ("dc01", "crs", "cold rolled", "1008"), "cold_rolled_steel", "#8a9096"),
    _m("c45", "Carbon steel C45 / 1045 (normalised)", "steel", 7850, 210, 340, 620, 1.8,
       {"cnc", "weld"}, "good", ("c45", "1045", "ck45"), None, "#8e949a"),
    _m("42crmo4", "Alloy steel 42CrMo4 / 4140 (Q+T)", "steel", 7850, 210, 750, 1000, 3.0,
       {"cnc"}, "fair", ("42crmo4", "4140", "chromoly"), None, "#6f757b"),
    _m("11smnpb30", "Free-machining steel 11SMnPb30 / 12L14", "steel", 7850, 205, 300, 450, 1.8,
       {"cnc"}, "excellent", ("11smnpb30", "12l14", "free machining"), None, "#9ea4ab"),
    _m("stainless_304", "Stainless steel 1.4301 / 304 (A2)", "stainless", 8000, 193, 215, 505, 4.0,
       {"cnc", "sheet", "weld", "laser"}, "fair", ("304", "1.4301", "a2", "stainless", "inox", "18/8"),
       "stainless_304", "#b7bcc2"),
    _m("stainless_316", "Stainless steel 1.4401 / 316 (A4)", "stainless", 8000, 193, 205, 515, 5.0,
       {"cnc", "sheet", "weld", "laser"}, "fair", ("316", "1.4401", "a4", "marine stainless"),
       "stainless_316", "#b9bec4"),
    # Spring wire (EN 10270-1 SH/DH, EN 10270-3 1.4310): density and E per
    # EN 13906-1 Table 2; tensile strength for ~2 mm wire (EN 10270-1 SH, EN
    # 10270-3 NS, minimum of the range).
    _m("spring_steel", "Patented spring steel wire EN 10270-1 (SH / DH)", "steel", 7850, 206, None, 1980, 3.5,
       set(), "n/a", ("en 10270", "spring steel", "music wire", "piano wire"), None, "#5f6368"),
    _m("stainless_301", "Stainless spring steel 1.4310 / 301 (EN 10270-3)", "stainless", 7900, 185, None, 1900, 9.0,
       set(), "n/a", ("1.4310", "301", "stainless spring"), None, "#b3b8be"),
    # Blind-rivet body alloy (ISO 15977 AlA = AlMg 2.5..3.5 / EN AW-5754-type)
    _m("almg3", "Aluminium AlMg3 / EN AW-5754 (rivet bodies)", "aluminium", 2670, 70, 80, 190, 5.0,
       {"sheet"}, "good", ("almg3", "5754", "rivet aluminium"), None, "#c9ced3"),
    _m("gjl250", "Grey cast iron EN-GJL-250", "iron", 7200, 110, None, 250, 2.0,
       {"cast", "cnc"}, "good", ("gjl", "cast iron", "grey iron", "gg25"), None, "#55595e"),
    # Aluminium
    _m("6061_t6", "Aluminium 6061-T6", "aluminium", 2700, 68.9, 276, 310, 4.5,
       {"cnc", "sheet", "weld"}, "good", ("6061", "aluminium", "aluminum", "alu"), "aluminum_6061_t6", "#c7ccd1"),
    _m("6082_t6", "Aluminium EN AW-6082-T6", "aluminium", 2700, 70, 260, 310, 4.0,
       {"cnc", "weld"}, "good", ("6082", "almgsi1"), None, "#c5cacf"),
    _m("6063_t5", "Aluminium 6063-T5 (extrusions)", "aluminium", 2700, 68.9, 145, 185, 4.0,
       {"cnc"}, "fair", ("6063", "extrusion"), None, "#cfd3d7"),
    _m("7075_t6", "Aluminium 7075-T6", "aluminium", 2810, 71.7, 503, 572, 9.0,
       {"cnc"}, "good", ("7075", "ergal", "aircraft aluminium"), None, "#bcc1c6"),
    _m("5052_h32", "Aluminium 5052-H32 (sheet)", "aluminium", 2680, 70.3, 193, 228, 5.0,
       {"sheet", "weld", "laser"}, "fair", ("5052",), "aluminum_5052_h32", "#cdd2d6"),
    # Copper alloys, titanium
    _m("brass_cw614n", "Free-cutting brass CW614N / C360", "copper", 8500, 97, 250, 400, 9.0,
       {"cnc"}, "excellent", ("brass", "cw614n", "c360", "cuzn39pb3"), "brass_260", "#b5a642"),
    _m("copper_c110", "Copper Cu-ETP / C110", "copper", 8940, 117, 70, 220, 11.0,
       {"cnc", "sheet"}, "poor", ("copper", "c110", "cu-etp"), "copper_c110", "#b87333"),
    _m("bronze_cusn8", "Bearing bronze CuSn8 / SAE 841 (sintered: oilite)", "copper", 8800, 110, 200, 400, 14.0,
       {"cnc"}, "good", ("bronze", "cusn8", "oilite"), None, "#a97142"),
    _m("ti6al4v", "Titanium Ti-6Al-4V (grade 5)", "titanium", 4430, 113.8, 880, 950, 40.0,
       {"cnc"}, "poor", ("titanium", "ti6al4v", "grade 5", "ti64"), None, "#8b8f94"),
    # Engineering plastics (machined / moulded)
    _m("pom", "Acetal POM-C (Delrin-type)", "polymer", 1410, 2.8, 65, 67, 7.0,
       {"cnc"}, "excellent", ("pom", "acetal", "delrin"), None, "#f2f0ea"),
    _m("pa6", "Nylon PA6 (cast / extruded)", "polymer", 1140, 2.8, 70, 80, 7.0,
       {"cnc"}, "good", ("nylon", "pa6", "polyamide"), None, "#e8e4d8"),
    _m("pc", "Polycarbonate PC", "polymer", 1200, 2.4, 62, 65, 6.0,
       {"cnc", "laser"}, "good", ("polycarbonate", "pc", "lexan"), None, "#dfe8ee"),
    _m("pmma", "Acrylic PMMA (cast sheet)", "polymer", 1180, 3.2, None, 70, 5.0,
       {"laser", "cnc"}, "fair", ("acrylic", "pmma", "perspex", "plexiglas"), None, "#d6eef5"),
    _m("ptfe", "PTFE", "polymer", 2200, 0.5, 10, 25, 25.0,
       {"cnc"}, "good", ("ptfe", "teflon"), None, "#f7f7f5"),
    _m("uhmwpe", "UHMW-PE", "polymer", 930, 0.7, 20, 40, 8.0,
       {"cnc"}, "good", ("uhmw", "uhmwpe", "pe-1000"), None, "#f4f4f0"),
    # 3D-printing polymers (typical FDM part properties)
    _m("pla", "PLA (FDM)", "polymer", 1240, 3.5, 50, 55, 20.0,
       {"fdm"}, "n/a", ("pla",), None, "#e0e0e0"),
    _m("petg", "PETG (FDM)", "polymer", 1270, 2.1, 45, 50, 22.0,
       {"fdm"}, "n/a", ("petg",), None, "#cfe3e8"),
    _m("abs", "ABS (FDM)", "polymer", 1040, 2.2, 38, 42, 22.0,
       {"fdm"}, "n/a", ("abs",), None, "#f0efe9"),
    _m("asa", "ASA (FDM)", "polymer", 1070, 2.0, 42, 47, 28.0,
       {"fdm"}, "n/a", ("asa",), None, "#ecebe5"),
    _m("pa_cf", "Carbon-fibre nylon PA-CF (FDM)", "polymer", 1150, 6.0, 70, 80, 70.0,
       {"fdm"}, "n/a", ("pa-cf", "pacf", "carbon nylon"), None, "#2b2d30"),
    _m("tpu_95a", "TPU 95A (FDM)", "elastomer", 1210, 0.026, None, 35, 35.0,
       {"fdm"}, "n/a", ("tpu", "flex", "95a"), None, "#3a3d42"),
    _m("pa12_sls", "PA12 (SLS / MJF)", "polymer", 1010, 1.7, None, 48, 90.0,
       {"sls"}, "n/a", ("pa12", "sls", "mjf"), None, "#9a9a9a"),
    _m("resin_std", "Standard photopolymer resin (SLA)", "polymer", 1180, 2.2, None, 55, 60.0,
       {"sla"}, "n/a", ("resin", "sla", "photopolymer"), None, "#8f9ba3"),
    # Composites, wood, elastomers
    _m("cfrp_plate", "Carbon fibre plate (quasi-isotropic CFRP)", "composite", 1550, 55, None, 600, 120.0,
       {"cnc", "laser"}, "fair", ("carbon fibre", "carbon fiber", "cfrp"), None, "#1f2124"),
    _m("g10", "Glass-epoxy laminate G10 / FR4", "composite", 1850, 18, None, 300, 25.0,
       {"cnc"}, "fair", ("g10", "fr4", "glass epoxy"), None, "#d8d39a"),
    _m("plywood_birch", "Birch plywood (EN 636)", "wood", 680, 9.0, None, 40, 2.5,
       {"cnc", "laser", "wood"}, "good", ("plywood", "birch ply"), None, "#d9b98c"),
    _m("mdf", "MDF", "wood", 750, 3.5, None, 18, 1.0,
       {"cnc", "laser", "wood"}, "good", ("mdf",), None, "#b99a73"),
    _m("pine", "Pine / spruce softwood (C24)", "wood", 500, 11.0, None, 24, 1.5,
       {"wood"}, "good", ("pine", "spruce", "softwood", "c24"), None, "#e3c48f"),
    _m("oak", "European oak (hardwood)", "wood", 750, 12.0, None, 50, 6.0,
       {"wood", "cnc"}, "good", ("oak", "hardwood"), None, "#b08a5a"),
    _m("nbr_70", "Nitrile rubber NBR 70 Shore A (O-rings)", "elastomer", 1000, 0.006, None, 15, 15.0,
       set(), "n/a", ("nbr", "nitrile", "buna"), None, "#202124"),
]

# fmt: on
MATERIALS: Dict[str, Material] = {m.key: m for m in _ALL}


def material(name: str) -> Material:
    """A material by key (``"6061_t6"``), name, or keyword (``"stainless steel A2"``,
    ``"Aluminium 6082"``). Longest matching keyword wins."""
    if isinstance(name, Material):
        return name
    text = str(name).strip()
    norm = text.lower().replace("-", "_").replace(" ", "_")
    if norm in MATERIALS:
        return MATERIALS[norm]
    padded = " " + re.sub(r"[^a-z0-9./]+", " ", text.lower()) + " "
    # A grade designator ("6082", "a2", "1.4301") beats a family word
    # ("aluminium", "stainless"); then the longer keyword wins.
    best = None
    for m in _ALL:
        for kw in m.keywords + (m.name.lower(),):
            if f" {kw} " in padded or (len(kw) > 4 and kw in padded):
                score = (any(ch.isdigit() for ch in kw), len(kw))
                if best is None or score > best[1]:
                    best = (m, score)
    if best is None:
        raise UnknownSize(
            f"Unknown material {name!r}. Known keys: {', '.join(MATERIALS)}"
        )
    return best[0]


def materials_for(process: str) -> List[Material]:
    """Materials usable with ``process`` (cnc / sheet / weld / cast / laser / fdm / sla / sls / wood)."""
    if process not in PROCESSES:
        raise UnknownSize(f"Unknown process {process!r}; one of {', '.join(PROCESSES)}")
    return [m for m in _ALL if process in m.processes]
