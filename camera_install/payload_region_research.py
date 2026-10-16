"""Compare observed raw compiler records with independently decoded output regions.

Research only: neither creates nor modifies a camera payload. Region geometry
is restricted to previously observed sizes; unknown sizes remain unmapped.
"""
import hashlib
from .compiler_regression import decode


def regions(size):
    if size in (8528, 16720, 16744, 16752):
        count = 2 if size == 8528 else 4
        start = size - count * 4096
        return [(start + i * 4096, 4096) for i in range(count)]
    if size in (78980, 83076):
        result = [(372 + i * 19652, 19652) for i in range(4)]
        if size == 83076:
            result.append((78980, 4096))
        return result
    if size == 431616:
        return [(372, 215622), (215994, 215622)]
    return []


def prove_regions(payload, observations, keys):
    decoded = []
    for offset, length in regions(len(payload)):
        if len(payload) == 431616:
            decoded.append((offset, None, payload[offset:offset + length]))
            continue
        for seed in (0xb8ed, 0x33137):
            block = decode(payload[offset:offset + length], keys, seed)
            decoded.append((offset, seed, block))
    records = []
    for item in observations:
        if item.get('stage') != 'compile' or item.get('rc') != 0 or not item.get('dataHex'):
            continue
        data = bytes.fromhex(item['dataHex'])
        matches = [dict(offset=offset, seed=hex(seed) if seed is not None else None) for offset, seed, block in decoded if block == data]
        records.append(dict(property=item['property'], callerRva=item['callerRva'],
                            length=len(data), sha256=hashlib.sha256(data).hexdigest(),
                            exactOutputRegions=matches))
    return dict(method='independent-output-versus-observed-record',
                geometryMapped=bool(decoded), payloadSize=len(payload), records=records,
                scope='Exact region equality only; no physical or numerical color validation')
