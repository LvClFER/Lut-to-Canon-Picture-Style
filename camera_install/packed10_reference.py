"""Independent compact octant packing from observed stock Canon inputs."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from .cipher_stream_reference import decode


def packed_index(r,g,b):
    if not all(isinstance(v,int) and 0<=v<10 for v in (r,g,b)):
        raise ValueError('Require 10-node coordinates')
    return 5*((g%5)+5*(b%5))+(513 if b>4 else 0)+(257 if g>4 else 0)+r+(124 if r>4 else 0)


def pack10(values, coefficient_mode):
    if len(values)!=3000 or not all(math.isfinite(v) for v in values):
        raise ValueError('Require finite planar 10-node channels')
    if coefficient_mode:
        yr,yg,yb,br,bg,bb,rr,rg,rb=(.2979874,.5851238,.1168888,-.173047,-.339793,.5128404,.5009222,.417349,.0833729)
    else:
        yr,yg,yb,br,bg,bb,rr,rg,rb=(.29922207,.586998487,.113779442,-.168724339,-.330994742,.499719081,.499719081,.41858388,.081135201)
    result=[0]*1024
    def chroma(v):
        if v<0: v+=512
        q=math.floor(v*2+.5)
        return (q if q!=1024 else 0)&1023
    for r in range(10):
        for g in range(10):
            for b in range(10):
                i=(r*10+g)*10+b
                red,green,blue=values[i],values[1000+i],values[2000+i]
                y=math.floor(((red*yr+green*yg)+blue*yb)*2+.5)&1023
                cb=chroma((red*br+green*bg)+blue*bb)
                cr=chroma((red*rr-green*rg)-blue*rb)
                result[packed_index(r,g,b)]=(y<<20)|(cb<<10)|cr
    return struct.pack('<1024I',*result)


def unpack10_integer(data):
    """Static4a5e0 inverse layout: unsigned Y, signed 10-bit Cr/Cb.

    Unused packed slots and upper two bits are not color-table entries.
    This is a research decoder, not proof of native source/cache selection.
    """
    if not isinstance(data,bytes) or len(data)!=4096:
        raise ValueError('Require exact 4096-byte packed compact table')
    words=struct.unpack('<1024I',data)
    values=[0]*3000
    def signed(value):return value-1024 if value&512 else value
    for r in range(10):
        for g in range(10):
            for b in range(10):
                i=(r*10+g)*10+b
                word=words[packed_index(r,g,b)]
                values[i]=(word>>20)&1023
                values[1000+i]=signed(word&1023)
                values[2000+i]=signed((word>>10)&1023)
    return values


def pack10_integer(values):
    """Observed final planar integer order: Y, Cr, Cb; no color conversion."""
    if len(values)!=3000 or not all(isinstance(v,int) for v in values):
        raise ValueError('Require 3000 integer components')
    result=[0]*1024
    for r in range(10):
        for g in range(10):
            for b in range(10):
                i=(r*10+g)*10+b
                result[packed_index(r,g,b)]=((values[i]&1023)<<20)|((values[2000+i]&1023)<<10)|(values[1000+i]&1023)
    return struct.pack('<1024I',*result)


def pack10_for_style(values, style, mode):
    """Observed475c0 coefficient branch, before the49e00 integer packer.

    Known-revision static predicate4776e..4777f selects the first matrix
    only for Standard/Neutral in mode1. No device support is inferred.
    """
    if style not in (0x81, 0x82, 0x83, 0x84, 0x85, 0x88) or mode not in (1, 2):
        raise ValueError('Require an observed base style and color mode')
    return pack10(values, not (style in (0x81, 0x84) and mode == 1))


def decoded_payload_blocks(payload,keys):
    result=[]
    header={8528:336,16720:336,16744:360,16752:368}.get(len(payload))
    if header is not None:
        for offset in range(header,len(payload),4096):
            for seed in (0xb8ed,0x33137):
                result.append((offset,seed,decode(payload[offset:offset+4096],keys,seed)))
    elif len(payload)==83076:
        # Modern 17-node carrier can append one compact legacy representation.
        result.append((78980,0xb8ed,decode(payload[78980:],keys,0xb8ed)))
    return result


def main():
    from .compiler_regression import cipher_tables
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--dll',type=Path,help='Also verify packer output occurs in decoded native payload')
    args=parser.parse_args(); source=json.loads(args.trace.read_text(encoding='utf-8'))
    keys=cipher_tables(args.dll) if args.dll else None
    rows=[]; failures=[]
    for case in source['files']:
        if case.get('error'):
            failures.append(case['error']); continue
        payload=Path(case['privateResearchPayload']).read_bytes() if keys else None
        if payload is not None and hashlib.sha256(payload).hexdigest()!=case['payloadSha256']:
            raise ValueError('Private payload differs from recorded compiler output')
        decoded=decoded_payload_blocks(payload,keys) if payload is not None else []
        for capture in case.get('mlibCalls',{}).get('captures',[]):
            if capture['functionRva'] not in ('0x4b760','0x49e00'): continue
            if capture['functionRva']=='0x49e00':
                values=struct.unpack('<3000i',bytes.fromhex(capture['inputPlanarInt32Hex']))
                actual=pack10_integer(values)
            else:
                values=struct.unpack('<3000d',bytes.fromhex(capture['inputPlanarFloat64Hex']))
                actual=pack10(values,capture['coefficientMode'])
            expected=bytes.fromhex(capture['nativePackedHex'])
            locations=[{'blockOffset':offset,'seed':seed,'insideOffset':block.find(expected)}
                       for offset,seed,block in decoded if block.find(expected)>=0]
            rows.append({'model':case['model'],'source':case['source'],
                         'mode':capture.get('coefficientMode'),'functionRva':capture['functionRva'],'passed':actual==expected,
                         'callerRva':capture.get('callerRva'),
                         'nativePayloadLocations':locations,'payloadContainsPackedBytes':bool(locations) if keys else None,
                         'differentBytes':sum(a!=b for a,b in zip(actual,expected))})
    result={'cameraAccess':False,'rows':rows,'traceFailures':failures,'passed':sum(r['passed'] for r in rows)}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(rows),'passed':result['passed'],'payloadMatches':sum(r['payloadContainsPackedBytes'] is True for r in rows),'traceFailures':len(failures)}))


if __name__=='__main__': main()
