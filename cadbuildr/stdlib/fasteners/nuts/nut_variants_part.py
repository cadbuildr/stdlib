"""Nut variants beyond the plain hex nut: thin, nylon-insert lock, square and wing."""

from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Circle, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import (
    rectangle_shape,
    add_internal_thread,
)
from cadbuildr.stdlib.fasteners.nuts.hex_din934_part import HexNut


@catalog_part(
    id="din439-thin-hex-nut",
    category="Fasteners",
    subcategory="Nuts",
    name="Thin Hex Nut",
    standard="DIN 439 / ISO 4035",
    description="Reduced-height (jam) hex nut, used as a locknut or where clearance is tight.",
    params=[
        ParamSpec.enum("size", choices=["M3", "M4", "M5", "M6", "M8", "M10", "M12"], default="M6"),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=False,
    example_config={"size": "M8"},
)
class ThinNut(HexNut):
    dimension_table: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"width_across_flats": 5.5, "thickness": 1.8, "nominal_diameter": 3, "thread_pitch": 0.5},
        "M4": {"width_across_flats": 7.0, "thickness": 2.2, "nominal_diameter": 4, "thread_pitch": 0.7},
        "M5": {"width_across_flats": 8.0, "thickness": 2.7, "nominal_diameter": 5, "thread_pitch": 0.8},
        "M6": {"width_across_flats": 10.0, "thickness": 3.2, "nominal_diameter": 6, "thread_pitch": 1.0},
        "M8": {"width_across_flats": 13.0, "thickness": 4.0, "nominal_diameter": 8, "thread_pitch": 1.25},
        "M10": {"width_across_flats": 17.0, "thickness": 5.0, "nominal_diameter": 10, "thread_pitch": 1.5},
        "M12": {"width_across_flats": 19.0, "thickness": 6.0, "nominal_diameter": 12, "thread_pitch": 1.75},
    }


@catalog_part(
    id="din985-nylon-lock-nut",
    category="Fasteners",
    subcategory="Nuts",
    name="Nylon Insert Lock Nut",
    standard="DIN 985 / ISO 10511",
    description="Hex nut with a taller body carrying a nylon insert that resists loosening under vibration.",
    params=[
        ParamSpec.enum("size", choices=["M3", "M4", "M5", "M6", "M8", "M10", "M12"], default="M6"),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=False,
    example_config={"size": "M8"},
)
class NylonLockNut(HexNut):
    dimension_table: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"width_across_flats": 5.5, "thickness": 4.0, "nominal_diameter": 3, "thread_pitch": 0.5},
        "M4": {"width_across_flats": 7.0, "thickness": 5.0, "nominal_diameter": 4, "thread_pitch": 0.7},
        "M5": {"width_across_flats": 8.0, "thickness": 5.0, "nominal_diameter": 5, "thread_pitch": 0.8},
        "M6": {"width_across_flats": 10.0, "thickness": 6.0, "nominal_diameter": 6, "thread_pitch": 1.0},
        "M8": {"width_across_flats": 13.0, "thickness": 8.0, "nominal_diameter": 8, "thread_pitch": 1.25},
        "M10": {"width_across_flats": 17.0, "thickness": 10.0, "nominal_diameter": 10, "thread_pitch": 1.5},
        "M12": {"width_across_flats": 19.0, "thickness": 12.0, "nominal_diameter": 12, "thread_pitch": 1.75},
    }


class _BoredNut(Part):
    """Helper base: a prism body with a central threaded bore."""

    def _build(self, shape, thickness, nominal_diameter, thread_pitch, with_thread):
        self.add_operation(Extrusion(shape, thickness))
        bore = Circle(Sketch(self.xy()).origin, nominal_diameter / 2)
        self.add_operation(Extrusion(bore, thickness, cut=True))
        if with_thread and thickness > thread_pitch:
            add_internal_thread(
                self, nominal_radius=nominal_diameter / 2, length=thickness, pitch=thread_pitch
            )
        self.paint("grey")


@catalog_part(
    id="din557-square-nut",
    category="Fasteners",
    subcategory="Nuts",
    name="Square Nut",
    standard="DIN 557",
    description="Four-flat square nut, often dropped into channels or held against a flat to stop it turning.",
    params=[
        ParamSpec.enum("size", choices=["M4", "M5", "M6", "M8", "M10", "M12"], default="M6"),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=False,
    example_config={"size": "M6"},
)
class SquareNut(_BoredNut):
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M4": {"w": 7.0, "m": 3.2, "p": 0.7},
        "M5": {"w": 8.0, "m": 4.0, "p": 0.8},
        "M6": {"w": 10.0, "m": 5.0, "p": 1.0},
        "M8": {"w": 13.0, "m": 6.5, "p": 1.25},
        "M10": {"w": 17.0, "m": 8.0, "p": 1.5},
        "M12": {"w": 19.0, "m": 10.0, "p": 1.75},
    }

    def __init__(self, size, with_thread=True):
        d = self.TABLE[size]
        nominal = float(size[1:])
        shape = rectangle_shape(Sketch(self.xy()), d["w"], d["w"])
        self._build(shape, d["m"], nominal, d["p"], with_thread)
        self.size = size


@catalog_part(
    id="din315-wing-nut",
    category="Fasteners",
    subcategory="Nuts",
    name="Wing Nut",
    standard="DIN 315",
    description="Round-body nut with two upright wings for hand tightening without a tool.",
    params=[
        ParamSpec.enum("size", choices=["M4", "M5", "M6", "M8"], default="M6"),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=False,
    example_config={"size": "M6"},
)
class WingNut(_BoredNut):
    # body_d = round body diameter, m = body thickness, wing_l/h/t = wing length/height/thickness
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M4": {"body_d": 9.0, "m": 4.0, "wing_l": 9.0, "wing_h": 9.0, "wing_t": 1.6, "p": 0.7},
        "M5": {"body_d": 11.0, "m": 5.0, "wing_l": 11.0, "wing_h": 11.0, "wing_t": 2.0, "p": 0.8},
        "M6": {"body_d": 13.0, "m": 6.0, "wing_l": 13.0, "wing_h": 13.0, "wing_t": 2.5, "p": 1.0},
        "M8": {"body_d": 16.0, "m": 7.0, "wing_l": 16.0, "wing_h": 15.0, "wing_t": 3.0, "p": 1.25},
    }

    def __init__(self, size, with_thread=True):
        d = self.TABLE[size]
        nominal = float(size[1:])
        body = Circle(Sketch(self.xy()).origin, d["body_d"] / 2)
        self._build(body, d["m"], nominal, d["p"], with_thread)
        self._add_wings(d)
        self.size = size

    def _add_wings(self, d):
        """Two flat upright fins on +X and -X, standing above the body."""
        body_r = d["body_d"] / 2
        x_out = body_r + d["wing_l"]
        z_top = d["m"] + d["wing_h"]
        t = d["wing_t"]
        for sx in (1, -1):
            s = Sketch(self.xz())
            x0, x1 = sorted((sx * (body_r - 0.5), sx * x_out))
            s.pencil.move_to(x0, d["m"] * 0.4)
            s.pencil.line_to(x1, d["m"] * 0.4)
            s.pencil.line_to(x1, z_top)
            s.pencil.line_to(x0, z_top)
            shape = s.pencil.close()
            # Extrude along the sketch normal (Y) to give the fin its thickness.
            self.add_operation(Extrusion(shape, -t / 2, t / 2))
