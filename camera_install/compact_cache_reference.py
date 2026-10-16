"""Research-only dense PF3 record to compact cache, with explicit policies.

No Canon discovery/execution, cipher keys, camera IDs or transport. Flag and
coefficient selection are caller obligations, not guessed from a model name.
Only the observed null-curve 10-node flag0/flag1 paths are represented.
"""
from .accepted_modern_reference import dense_source
from .compact_grid_reference import compact_flag0,compact_flag1
from .packed10_reference import pack10


def build_compact_cache(record,*,grid_flag,coefficient_mode):
    if type(grid_flag) is not int or grid_flag not in (0,1):
        raise ValueError('Require explicit observed compact grid flag0/1')
    if type(coefficient_mode) is not bool:
        raise ValueError('Require explicit coefficient policy')
    source=dense_source(record)
    values=(compact_flag0 if grid_flag==0 else compact_flag1)(source)
    return pack10(values.reshape(-1).tolist(),coefficient_mode)
