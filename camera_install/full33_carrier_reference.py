"""Experimental normal full33 compiler replay from complete PF3 records.

No Canon execution/discovery or camera access. Cipher tables are explicit
inputs for control serialization. Normal-route equivalence does not imply
that arbitrary dense LUTs are accepted or installed correctly on a camera.
"""
from .cipher_stream_reference import decode
from .control_section_reference import build_control_plain
from .modern_header_reference import build_full33_prefix
from .full33_packing_reference import source_full33_table


def build_observed_full33(fields, keys):
    control = build_control_plain({i: fields[i] for i in (0x100a, 0x100d) if i in fields})
    encoded = control[:8] + decode(control[8:], keys, 0x22e1)
    prefix = build_full33_prefix(fields, encoded)
    data = {identifier: value for identifier, (_, value) in fields.items()}
    return prefix + source_full33_table(data, 1) + source_full33_table(data, 2)
