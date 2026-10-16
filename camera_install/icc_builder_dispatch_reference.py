"""Research-only translation of known MLib ICC dispatch header instructions.

This predicts dispatch, not successful compilation or a safe native-call layout.
Never use it to prepare a camera payload.
"""
import struct
import math


def mode_two_consumer_plan(selector, first_kind=None, companion_kind=None, second_kind=None):
    """Known-revision local gates only, never a native buffer validator.

    None denotes a null pointer; a kind value describes only its first word.
    Nonempty record structure and fa40 contents require separate evidence.
    """
    for value in (selector, first_kind, companion_kind, second_kind):
        if value is not None and (type(value) is not int or not 0<=value<=0xffffffff):
            raise ValueError('Require unsigned words or explicit null pointers')
    if selector is None:raise ValueError('Selector word required')
    operations=[]
    if first_kind==1:operations.append('first-selective')
    operations.append('second-curve-group')
    if selector!=2:operations.append('fixed-roundtrip-10-to-11')
    if companion_kind==2:operations.append('companion-axis')
    if selector!=2:operations.append('fixed-roundtrip-11-to-10')
    if second_kind==1:operations.append('second-selective')
    operations.extend(('rgb-clamp','floating-color'))
    return {'numericMode':11 if selector==2 else 10,'operations':tuple(operations),
            'scope':'Static call order and kind gates only; no record-content or camera validation'}


def inspect_dispatch(data):
    if not isinstance(data, bytes) or len(data) < 4:
        raise ValueError('Require immutable header bytes')
    mode = struct.unpack_from('<I', data)[0]
    if mode == 0:
        return {'mode': 0, 'entry': '0x4720', 'scope': 'dispatch only'}
    if mode == 1:
        if len(data) < 20:
            raise ValueError('Mode1 header truncated')
        field4, channels, nodes, field16 = struct.unpack_from('<4I', data, 4)
        entry = '0x5930' if nodes <= 10 else '0x6260'
        accepted_entry_header = channels == 3 and (nodes in (9, 10) if nodes <= 10 else True)
        return {'mode': 1, 'entry': entry, 'channels': channels, 'nodes': nodes,
                'field4': field4, 'field16': field16, 'payloadOffset': 20,
                'entryHeaderAccepted': accepted_entry_header,
                'localStep': (40 if nodes == 9 else 32) if nodes in (9, 10)
                             else (1024 // (nodes - 1) if nodes > 10 else None),
                'scope': 'header checks only; payload and successful output unproved'}
    if mode == 2:
        if len(data) < 0xf14:
            raise ValueError('Mode2 header truncated')
        prefix = struct.unpack_from('<i', data, 0x47c)[0]
        total = struct.unpack_from('<i', data, 0xf0c)[0]
        width = struct.unpack_from('<I', data, 0xf10)[0]
        route = ('null' if prefix > total else 'unsplit' if prefix == 0 or total == 0 or prefix == total else 'split')
        return {'mode': 2, 'entry': None if route == 'null' else '0x7810',
                'prefixCount': prefix, 'totalCount': total, 'recordWidth': width,
                'route': route, 'firstCurveGroupOffset': 4,
                'secondCurveGroupOffset': 0x130, 'thirdCurveGroupOffset': 0x25c,
                'matrixOffset': 0x388,
                'scope': 'signed count branches only; allocation safety and full layout unproved'}
    return {'mode': mode, 'entry': None, 'scope': 'unknown mode returns null'}


def split_mode_two_records(data):
    """Research-only bounded reproduction of full-capacity record copying.

    Inactive native record storage is unspecified, so partial records are refused.
    This validates copying only, not native builder acceptance.
    """
    header=inspect_dispatch(data)
    if header['mode']!=2:raise ValueError('Require mode2')
    prefix,total,width=header['prefixCount'],header['totalCount'],header['recordWidth']
    if not 0<=prefix<=total<=16 or not 1<=width<=12:
        raise ValueError('Require bounded nonnegative counts and capacities')
    stride=4+16*width
    if total==0 or len(data)!=0xf10+total*stride:
        raise ValueError('Require exact nonempty record payload')
    kind=struct.unpack_from('<I',data,0xf08)[0]
    records=[]
    for index in range(total):
        record=data[0xf10+index*stride:0xf10+(index+1)*stride]
        if struct.unpack_from('<I',record)[0]!=width:
            raise ValueError('Partial-capacity record copying not byte-defined')
        records.append(record)
    if header['route']=='unsplit':
        return (struct.pack('<2I',kind,total)+b''.join(records),)
    return tuple(struct.pack('<2I',kind,len(part))+b''.join(part)
                 for part in (records[:prefix],records[prefix:]))


def decode_mode_one_grid(data):
    """Bounded research decoder of static planar uint32 reads, not a compiler."""
    header = inspect_dispatch(data)
    if header['mode'] != 1 or not header['entryHeaderAccepted']:
        raise ValueError('Require locally accepted mode1 header')
    nodes = header['nodes']
    if not 9 <= nodes <= 33:
        raise ValueError('Research decoder limited to9..33 nodes')
    count = nodes ** 3
    if len(data) != 20 + 3 * count * 4:
        raise ValueError('Require exact three-plane payload length')
    values = struct.unpack_from(f'<{3*count}I', data, 20)
    return tuple(tuple(values[channel*count+node] for channel in range(3))
                 for node in range(count))


def sample_mode_one_grid(data, coordinates, *, allow_endpoints=False):
    """Observed bounded7020 math; native calls still require endpoint padding."""
    grid=decode_mode_one_grid(data)
    nodes=inspect_dispatch(data)['nodes']
    return _sample_decoded_grid(grid,nodes,coordinates,allow_endpoints=allow_endpoints)


def _sample_decoded_grid(grid,nodes,coordinates,*,allow_endpoints=False):
    """Internal research replay helper; grid must come from strict decoder."""
    if type(allow_endpoints) is not bool:raise ValueError('Explicit boolean endpoint policy required')
    if len(coordinates)!=3 or any(type(v) not in (int,float) or not math.isfinite(v)
                                 or v<0 or v>nodes-1 or (not allow_endpoints and v==nodes-1)
                                 for v in coordinates):
        raise ValueError('Require finite interior grid coordinates')
    cells=[int(v) for v in coordinates]
    fractions=[v-cell for v,cell in zip(coordinates,cells)]
    order=sorted(range(3),key=lambda axis:fractions[axis],reverse=True)
    vertices=[cells.copy()]
    for axis in order:
        point=vertices[-1].copy();point[axis]+=1;vertices.append(point)
    a,b,c=[fractions[axis] for axis in order]
    weights=(a-b,b-c,c)
    values=[]
    for point,weight in zip(vertices,(1.,*weights)):
        if weight==0:values.append(None);continue
        if any(v>=nodes for v in point):raise ValueError('Nonzero out-of-grid vertex')
        values.append(grid[(point[0]*nodes+point[1])*nodes+point[2]])
    result=[]
    for channel in range(3):
        base=float(values[0][channel])
        terms=[0. if weights[i]==0 else (float(values[i+1][channel])-base)*weights[i] for i in range(3)]
        result.append(((terms[0]+terms[1])+terms[2])+base)
    return tuple(result)
