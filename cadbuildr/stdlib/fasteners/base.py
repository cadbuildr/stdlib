"""The shared fastener contract every screw and bolt honours.

A *fastener* is anything :func:`connect_with_screw` /
:func:`connect_with_bolt_and_nut` can drive:

* ``body_radius`` — nominal shank radius (sizes the clearance hole);
* ``body_height`` — shank length below the seat (sizes the drill depth);
* anchor ``head_seat`` — the plane that lands on the hole face. For a
  protruding head (cap, hex, cheese, button) it is the under-head face; for
  a countersunk head it is the head top, flush with the face it is driven
  into. +Z points down the shank (screw-local -Z).
* anchor ``tip`` — the shank end at z=0, +Z pointing out of the tip
  (screw-local -Z).

Screws are built tip-at-origin, head toward +Z.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol

from cadbuildr.foundation import Part, make_anchor
from cadbuildr.foundation.interfaces import ScrewHead, ScrewTip


class ScrewLike(Protocol):
    """Structural type of a fastener: what the connection helpers rely on.

    Static-typing only — parts keep these attributes as pydantic extras, which
    ``isinstance`` on a runtime protocol cannot see. Use :func:`is_fastener`.
    """

    body_radius: float
    body_height: float

    def anchor(self, name: str) -> Any: ...


class Fastener(Part):
    """Base class for stdlib screws and bolts (see module docstring)."""

    def _set_fastener_contract(
        self,
        *,
        body_radius: float,
        body_height: float,
        seat_z: Optional[float] = None,
        size: Optional[str] = None,
    ) -> None:
        """Record the shank size and add the ``head_seat`` + ``tip`` anchors.

        ``seat_z`` defaults to ``body_height`` (shank ends at the seat).
        ``size`` is the designation the ``ScrewHead`` / ``ScrewTip``
        interfaces carry (default ``M<diameter>``; wood screws pass ``#8``).
        """
        self.body_radius = float(body_radius)
        self.body_height = float(body_height)
        seat = self.body_height if seat_z is None else float(seat_z)
        head = self.add_anchor(make_anchor("head_seat", (0.0, 0.0, seat), z_down=True))
        tip = self.add_anchor(make_anchor("tip", (0.0, 0.0, 0.0), z_down=True))
        # Interfaces: the head lands on a ScrewHole, a nut runs on from the tip.
        size = size or f"M{2.0 * self.body_radius:g}"
        self.fastener_size = size
        self.add_interface(ScrewHead(size=size, length=self.body_height), head)
        self.add_interface(ScrewTip(size=size), tip)


def _missing_contract(screw: Any) -> list[str]:
    missing = [a for a in ("body_radius", "body_height") if not hasattr(screw, a)]
    names = {a.name.value for a in getattr(screw, "anchors", [])}
    missing += [f"anchor '{a}'" for a in ("head_seat", "tip") if a not in names]
    return missing


def is_fastener(screw: Any) -> bool:
    """True when ``screw`` honours the fastener contract (duck-typed)."""
    return not _missing_contract(screw)


def require_fastener(screw: Any) -> None:
    """Raise a clear error when ``screw`` does not honour the contract."""
    missing = _missing_contract(screw)
    if missing:
        raise TypeError(
            f"{type(screw).__name__} is not a fastener (missing {', '.join(missing)}). "
            "Subclass cadbuildr.stdlib.fasteners.Fastener and call "
            "_set_fastener_contract(...)."
        )
