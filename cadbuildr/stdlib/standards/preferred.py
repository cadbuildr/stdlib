"""Preferred numbers and stock sizes: Renard series, E-series, sheet gauges, stock.

::

    preferred(37, "R20")            # 35.5
    preferred(37, "R10", "up")      # 40.0
    preferred(4700, "E12")          # 4700.0
    sheet_gauge(16, "steel")        # 1.519 mm (Manufacturers' Standard Gauge)
    stock_size(13, "sheet")         # 15 mm metric sheet / plate

Sources: ISO 3 / ISO 17 (Renard R5..R40, rounded basic values), IEC 60063
(E6 / E12 / E24 resistor & capacitor series), US gauge tables via
``cadbuildr.foundation.sheet_metal_materials`` (Manufacturers' Standard Gauge
for steel, Brown & Sharpe for aluminium / copper alloys), common metric stock
(EN 10051 / EN 485 sheet thicknesses, EN 10278 bright bar diameters, EN 636
plywood) as stocked by general suppliers.
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from ._common import OutOfRange, StandardsError, lookup

__all__ = [
    "E_SERIES",
    "RENARD",
    "STOCK",
    "preferred",
    "sheet_gauge",
    "stock_size",
]

# fmt: off
RENARD: Dict[str, Tuple[float, ...]] = {
    "R5": (1.00, 1.60, 2.50, 4.00, 6.30),
    "R10": (1.00, 1.25, 1.60, 2.00, 2.50, 3.15, 4.00, 5.00, 6.30, 8.00),
    "R20": (
        1.00, 1.12, 1.25, 1.40, 1.60, 1.80, 2.00, 2.24, 2.50, 2.80,
        3.15, 3.55, 4.00, 4.50, 5.00, 5.60, 6.30, 7.10, 8.00, 9.00,
    ),
    "R40": (
        1.00, 1.06, 1.12, 1.18, 1.25, 1.32, 1.40, 1.50, 1.60, 1.70,
        1.80, 1.90, 2.00, 2.12, 2.24, 2.36, 2.50, 2.65, 2.80, 3.00,
        3.15, 3.35, 3.55, 3.75, 4.00, 4.25, 4.50, 4.75, 5.00, 5.30,
        5.60, 6.00, 6.30, 6.70, 7.10, 7.50, 8.00, 8.50, 9.00, 9.50,
    ),
}

E_SERIES: Dict[str, Tuple[float, ...]] = {
    "E6": (1.0, 1.5, 2.2, 3.3, 4.7, 6.8),
    "E12": (1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2),
    "E24": (
        1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
        3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1,
    ),
}

# Common metric stock sizes (mm).
STOCK: Dict[str, Tuple[float, ...]] = {
    "sheet": (0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0, 25.0),
    "round_bar": (3, 4, 5, 6, 8, 10, 12, 14, 15, 16, 18, 20, 22, 25, 28, 30, 32, 35, 40, 45, 50, 60),
    "plywood": (3, 4, 6, 9, 12, 15, 18, 21, 24),
    "acrylic": (2, 3, 4, 5, 6, 8, 10),
}

# fmt: on


def preferred(value: float, series: str = "R20", direction: str = "nearest") -> float:
    """The member of ``series`` (R5..R40, E6..E24) nearest to ``value`` (or the next
    one ``"up"`` / ``"down"``), any decade."""
    base = RENARD.get(series) or lookup(E_SERIES, series, "preferred-number series")
    v = float(value)
    if v <= 0:
        raise OutOfRange(f"preferred(): value must be positive, got {value!r}")
    decade = 10.0 ** math.floor(math.log10(v))
    candidates = sorted(
        {round(b * decade * scale, 6) for b in base for scale in (0.1, 1.0, 10.0)}
    )
    if direction == "up":
        return next(c for c in candidates if c >= v - 1e-9)
    if direction == "down":
        return max(c for c in candidates if c <= v + 1e-9)
    if direction != "nearest":
        raise StandardsError(
            f"direction must be nearest / up / down, got {direction!r}"
        )
    # Nearest on a log scale (the series are geometric).
    return min(candidates, key=lambda c: abs(math.log(c / v)))


def sheet_gauge(gauge: int, family: str = "steel") -> float:
    """US gauge thickness (mm) for ``family`` steel / galvanized / stainless /
    aluminium / copper / brass (delegates to foundation's sheet-metal tables)."""
    from cadbuildr.foundation.sheet_metal_materials import MATERIALS

    keys = {
        "steel": "cold_rolled_steel",
        "galvanized": "galvanized_steel",
        "stainless": "stainless_304",
        "aluminium": "aluminum_5052",
        "aluminum": "aluminum_5052",
        "copper": "copper",
        "brass": "brass",
    }
    key = lookup(keys, family, "sheet gauge family")
    try:
        return MATERIALS[key].thickness_for_gauge(int(gauge))
    except ValueError as exc:
        raise OutOfRange(str(exc)) from None


def stock_size(value: float, kind: str = "sheet", direction: str = "up") -> float:
    """Common metric stock ``kind`` (sheet / round_bar / plywood / acrylic) at or
    above ``value`` (``direction="down"``: at or below)."""
    sizes = lookup(STOCK, kind, "stock kind")
    v = float(value)
    if direction == "up":
        for s in sizes:
            if s >= v - 1e-9:
                return float(s)
        raise OutOfRange(
            f"{kind}: {v:g} mm is thicker than the stock list ({sizes[-1]:g} mm)"
        )
    below = [s for s in sizes if s <= v + 1e-9]
    if not below:
        raise OutOfRange(
            f"{kind}: {v:g} mm is thinner than the stock list ({sizes[0]:g} mm)"
        )
    return float(below[-1])
