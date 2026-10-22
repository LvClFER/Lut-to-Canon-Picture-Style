"""Integrated offline PF3 -> explicit compiler route -> transport plan.

No session or transport is opened. Route selection must already be established;
this is not model detection, fresh-state acquisition or permission to register.
Keys are caller supplied, never discovered from an installed Canon runtime.
"""
from dataclasses import dataclass, field
import hashlib
from .pf3_source_reference import read_source_fields
from .compact_carrier_reference import build_observed_compact16752,build_accepted_compact16752
from .accepted_modern_reference import build_accepted_modern17
from .style_send_plan_reference import plan_style_send, StyleSendPlan
from .style_confirmation_reference import verify_readback_content


@dataclass(frozen=True)
class OfflineRegistration:
    source_sha256: str
    route: str
    carrier: bytes = field(repr=False)
    send: StyleSendPlan
    control_words: tuple = field(default=(),repr=False)

    def verify_content(self, completed_readback):
        """Content equality only; caller must establish slot/freshness separately."""
        return verify_readback_content(self.carrier, completed_readback)


def prepare(raw, keys, *, route, handler_selector, supported_operations,
            internal_selector=None, normalized_descriptor=None):
    """Explicit compact or observed dense17 route; no model/carrier-size guessing.

    The two compact routes are never silently substituted for one another.
    Normal full33 reconstructs parameter-based tables
    and is deliberately excluded: it does not preserve arbitrary dense LUTs.
    """
    if route not in ('compact16752-cache','compact16752-dense-pixel','modern83076-dense'):
        raise ValueError('Require explicitly established compiler route')
    if route!='compact16752-cache' and (type(normalized_descriptor) is not bytes or len(normalized_descriptor)!=14796):
        raise ValueError('Require explicit normalized modern descriptor for dense-pixel route')
    fields = read_source_fields(raw, keys)
    if route=='modern83076-dense':
        # Twelve archived accepted carriers establish Neutral/extended only.
        if fields.get(0x1009)!=(3,b'\x84\x00') or internal_selector is not None:
            raise ValueError('Observed dense17 route requires Neutral and no inferred camera selector')
        carrier = build_accepted_modern17(fields,normalized_descriptor,keys,extended=True)
    elif route=='compact16752-dense-pixel':
        carrier = build_accepted_compact16752(fields,normalized_descriptor,keys,
            internal_selector=internal_selector)
    else:
        carrier = build_observed_compact16752(fields, None, keys,
            block_paths=('cache',)*4, pixel_scale=256,
            internal_selector=internal_selector)
    send = plan_style_send(carrier, handler_selector, supported_operations)
    return OfflineRegistration(hashlib.sha256(raw).hexdigest(), route, carrier, send)
