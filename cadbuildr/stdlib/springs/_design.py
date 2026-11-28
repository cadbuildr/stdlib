"""Spring design formulas (EN 13906-1 / -2 / -3) and wire materials.

Plain functions, mm / N / MPa everywhere, so a part, a check or an agent can
size a spring without building geometry:

* :func:`compression_rate` / :func:`extension_rate` — ``R = G d^4 / (8 D^3 n)``
  (EN 13906-1 eq. (11), EN 13906-2 eq. (9)).
* :func:`torsion_rate` — ``R_M = E d^4 / (3667 D n)`` in N·mm per degree
  (EN 13906-3 eq. (5); 3667 = 64 · 180 / pi).
* :func:`shear_stress` — ``tau = 8 D F / (pi d^3)`` and the Bergmann stress
  correction ``k = (w + 0.5) / (w - 0.75)`` (EN 13906-1 eq. (4), (6)).
* :func:`solid_length` — cold-coiled compression springs, ``nt = n + 2``
  (DIN 2095 / EN 13906-1 §9.2): ends closed and ground ``Ls <= nt d``,
  closed not ground ``Ls <= (nt + 1.5) d`` (EN 13906-1 eq. (24), (25)).
* :func:`min_sum_of_gaps` — DIN 2095 / EN 13906-1 eq. (21): the coils must
  keep ``Sa = (0.0015 D^2 / d + 0.1 d) n`` apart at the maximum load.

``SPRING_WIRES`` lists the moduli of EN 13906-1 Table 2 for the common wires
(EN 10270-1 patented spring steel, EN 10270-2 oil-hardened, EN 10270-3
stainless 1.4310) with the :mod:`cadbuildr.stdlib.standards.materials` key
used for density and colour.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

__all__ = [
    "SPRING_WIRES",
    "SpringError",
    "SpringWire",
    "compression_rate",
    "extension_rate",
    "helix_wire_length",
    "min_sum_of_gaps",
    "shear_stress",
    "solid_length",
    "stress_correction",
    "torsion_rate",
]


class SpringError(ValueError):
    """A spring cannot be built with these dimensions."""


@dataclass(frozen=True)
class SpringWire:
    """A spring wire: shear modulus ``G`` and Young's modulus ``E`` (MPa)."""

    key: str
    name: str
    G: float
    E: float
    material: str  # cadbuildr.stdlib.standards.materials key


# EN 13906-1:2013 Table 2 (moduli at 20 °C).
SPRING_WIRES: Dict[str, SpringWire] = {
    w.key: w
    for w in (
        SpringWire("EN 10270-1", "Patented cold-drawn spring steel (SH / DH)",
                   81500.0, 206000.0, "spring_steel"),
        SpringWire("EN 10270-2", "Oil-hardened and tempered spring steel (FD / VD)",
                   79500.0, 206000.0, "spring_steel"),
        SpringWire("EN 10270-3", "Stainless spring steel 1.4310",
                   70000.0, 185000.0, "stainless_301"),
    )
}  # fmt: skip


def compression_rate(G: float, d: float, D: float, n: float) -> float:
    """Spring rate ``R = G d^4 / (8 D^3 n)`` in N/mm (EN 13906-1 eq. (11))."""
    return G * d**4 / (8.0 * D**3 * n)


def extension_rate(G: float, d: float, D: float, n: float) -> float:
    """Extension springs use the same rate (EN 13906-2 eq. (9))."""
    return compression_rate(G, d, D, n)


def torsion_rate(E: float, d: float, D: float, n: float) -> float:
    """Torsion spring rate in N·mm per degree, ``E d^4 / (3667 D n)``
    (EN 13906-3 eq. (5))."""
    return E * d**4 / (3667.0 * D * n)


def stress_correction(index: float) -> float:
    """Bergmann factor ``k = (w + 0.5) / (w - 0.75)`` (EN 13906-1 eq. (6))."""
    return (index + 0.5) / (index - 0.75)


def shear_stress(F: float, d: float, D: float, *, corrected: bool = True) -> float:
    """Torsional stress in MPa under force ``F`` (EN 13906-1 eq. (4)); with
    ``corrected`` the Bergmann factor is applied (``tau_k``)."""
    tau = 8.0 * D * F / (math.pi * d**3)
    return tau * stress_correction(D / d) if corrected else tau


def solid_length(d: float, n_total: float, ends: str) -> float:
    """Maximum solid length of a cold-coiled compression spring
    (EN 13906-1 eq. (24) ground, (25) closed not ground)."""
    if ends == "ground":
        return n_total * d
    if ends == "closed":
        return (n_total + 1.5) * d
    raise SpringError(f"unknown ends {ends!r} (choose from ground, closed)")


def min_sum_of_gaps(d: float, D: float, n: float) -> float:
    """Minimum sum of the gaps between active coils at the maximum working
    load, ``Sa = (0.0015 D^2 / d + 0.1 d) n`` (EN 13906-1 eq. (21))."""
    return (0.0015 * D**2 / d + 0.1 * d) * n


def helix_wire_length(D: float, pitch: float, turns: float) -> float:
    """Wire centre-line length of ``turns`` coils of mean diameter ``D``."""
    return turns * math.hypot(math.pi * D, pitch)
