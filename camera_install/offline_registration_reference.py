"""Integrated offline PF3 -> explicit compiler route -> transport plan.

No session or transport is opened. Route selection must already be established;
this is not model detection, fresh-state acquisition or permission to register.
Keys are caller supplied, never discovered from an installed Canon runtime.
"""
from dataclasses import dataclass, field
import hashlib
from .pf3_source_reference import read_source_fields
from .compact_carrier_reference import build_observed_compact16752
from .style_send_plan_reference import plan_style_send, StyleSendPlan
from .style_confirmation_reference import verify_readback_content


@dataclass(frozen=True)
class OfflineRegistration:
    source_sha256: str
    route: str
    carrier: bytes = field(repr=False)
    send: StyleSendPlan

    def verify_content(self, completed_readback):
        """Content equality only; caller must establish slot/freshness separately."""
        return verify_readback_content(self.carrier, completed_readback)


def prepare(raw, keys, *, route, handler_selector, supported_operations,
            internal_selector=None):
    """Explicit dense-table cache route, no guessing by model/carrier size.

    The compact route is cache-only; pixel/integer/descriptor routes are not
    silently substituted. Normal full33 reconstructs parameter-based tables
    and is deliberately excluded: it does not preserve arbitrary dense LUTs.
    """
    if route != 'compact16752-cache':
        raise ValueError('Require explicitly established compiler route')
    fields = read_source_fields(raw, keys)
    carrier = build_observed_compact16752(fields, None, keys,
        block_paths=('cache',)*4, pixel_scale=256,
        internal_selector=internal_selector)
    send = plan_style_send(carrier, handler_selector, supported_operations)
    return OfflineRegistration(hashlib.sha256(raw).hexdigest(), route, carrier, send)
