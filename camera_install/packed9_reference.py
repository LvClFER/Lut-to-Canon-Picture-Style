"""Independent nine-node packing and bounded own-host native comparison.

No camera API, references, payload construction or installed DLL modification.
"""
import argparse
import hashlib
import json
import math
import os
import random
import struct
from pathlib import Path


def quantize(red, green, blue):
    # 4bea0 truncates each float to int before calling 4abb0. The latter
    # applies a CRT scalar helper before the final 10-bit quantization.
    red, green, blue = [math.trunc(value) for value in (red, green, blue)]
    cb = math.floor((red * -.173047 - green * .339793) + blue * .5128404)
    cr = math.floor((red * .5009222 - green * .417349) - blue * .0833729)
    y = math.floor((red * .2979874 + green * .5851238) + blue * .1168888)
    def chroma(value):
        if value < 0:
            value += 512
        return math.trunc(value * 2 + .5) & 1023
    return ((math.trunc(y * 2 + .5) & 1023) << 20) | (chroma(cb) << 10) | chroma(cr)


def pack9(values):
    return _pack9_bounded(values, 255.75)


def pack9_observed_overshoot(values):
    """Research-only range observed during old-family MLib development.

    Allows finite 0..286 intermediates without silently clipping them. This
    does not extend the default caller contract or authorize camera output.
    """
    return _pack9_bounded(values, 286)


def pack9_dense9(values):
    """Explicit research domain from the dense9 flag0 output clamp, 0..320.

    Unlike the default helper, this preserves extrapolated values above255.
    No native device transport or model capability is implied.
    """
    return _pack9_bounded(values, 320)


def _pack9_bounded(values, maximum):
    count = 9 ** 3
    if len(values) != count * 3 or any(not math.isfinite(value) or not 0 <= value <= maximum for value in values):
        raise ValueError('Require bounded finite planar 9-node channels')
    words = []
    # Source coordinates: r-major, b-minor. Native output traverses b,g,r.
    for b in range(9):
        for g in range(9):
            for r in range(9):
                i = (r * 9 + g) * 9 + b
                words.append(quantize(values[i], values[count + i], values[2 * count + i]))
    return struct.pack('<729I', *words)


def native_pack(dll, vectors, integer_input=False):
    from .compiler_regression import cipher_tables
    cipher_tables(dll)
    if not 1 <= len(vectors) <= 8:
        raise ValueError('Bounded batch required')
    for vector in vectors:
        pack9(vector)
    import frida
    device = frida.get_local_device()
    host = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
    pid = device.spawn([str(host), '-NoLogo', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', 'Start-Sleep -Seconds 3600'])
    session = None
    try:
        session = device.attach(pid)
        script = session.create_script('''rpc.exports={pack(path,vectors,integerInput){
          const dll=Module.load(path);
          const fn=new NativeFunction(dll.base.add(integerInput?0x4c1d0:0x4bea0),'void',['pointer','pointer','pointer'],'thiscall');
          const context=Memory.alloc(0x38);context.writeByteArray(new Uint8Array(0x38));
          return vectors.map(values=>{
            const width=integerInput?4:8;
            const input=Memory.alloc(2187*width),output=Memory.alloc(2916);
            values.forEach((value,index)=>{
              if(integerInput)input.add(index*width).writeS32(Math.trunc(value));
              else input.add(index*width).writeDouble(value);
            });
            fn(context,input,output);
            return Array.from(new Uint8Array(output.readByteArray(2916)),v=>v.toString(16).padStart(2,'0')).join('');
          });
        }};''')
        script.load()
        device.resume(pid)
        return [bytes.fromhex(value) for value in script.exports_sync.pack(str(dll.resolve()), vectors, integer_input)]
    finally:
        if session:
            session.detach()
        device.kill(pid)


def main():
    from .compiler_regression import cipher_tables
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--integer-input', action='store_true', help='Compare integer planar packer4c1d0 instead of double packer4bea0')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Refusing to overwrite research output')
    n = 729
    rng = random.Random(20261005)
    vectors = [([0.] * (3*n)), ([255.] * (3*n)),
               [float((i // 81, (i // 9) % 9, i % 9)[c]) * 255 / 8 for c in range(3) for i in range(n)],
               [rng.random() * 255.75 for _ in range(3*n)]]
    expected = [pack9(values) for values in vectors]
    actual = native_pack(args.dll, vectors, args.integer_input)
    cipher_tables(args.dll)  # Recheck the original revision after native calls.
    rows = [dict(vector=name, exact=a == b,
                 changedBytes=sum(x != y for x,y in zip(a,b)),
                 independentSha256=hashlib.sha256(a).hexdigest(), nativeSha256=hashlib.sha256(b).hexdigest(),
                 firstIndependentWords=list(struct.unpack('<8I', a[:32])), firstNativeWords=list(struct.unpack('<8I', b[:32])))
            for name, a, b in zip(('black', 'white', 'coordinate-ramp', 'seeded-random'), expected, actual)]
    report = dict(cameraAccess=False, compilerPatched=False, dllSha256=hashlib.sha256(args.dll.read_bytes()).hexdigest(),
                  functionRva='0x4c1d0' if args.integer_input else '0x4bea0',
                  inputRepresentation='planar-truncated-int32' if args.integer_input else 'planar-double',
                  scope='Nine-node packing only; no legacy metadata or camera validation', rows=rows)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
    print(json.dumps(rows))
    if len(actual) != len(vectors) or not all(row['exact'] for row in rows):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
