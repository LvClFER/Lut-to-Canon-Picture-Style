"""Offline extraction and native comparison of the known compiler's family gate.

These internal numeric classes are not assertions of camera compatibility.
No EDSDK, camera session, payload writes or function replacements are used.
"""
import argparse
import hashlib
import json
import os
import struct
from collections import Counter
from pathlib import Path

from .descriptor_policy_research import read_rva
from .pf3_schema_research import DLL_HASH


RETURNS = {0x4eb0e: 5, 0x4eb55: 7, 0x4eb70: 3, 0x4eb76: 1,
           0x4eb94: 2, 0x4ebb4: 4, 0x4ebe1: 6, 0x4ebe7: 8,
           0x4ec1c: 9, 0x4ec22: 10}
EXPLICIT = {0x03740000: 5, 0x03840000: 5, 0x40000218: 9,
            0x40000227: 10, 0x80000169: 3, 0x80000190: 3,
            0x80000215: 3, 0x80000176: 4, 0x80000218: 4,
            0x80000213: 1, 0x80000232: 1, 0x80000269: 5,
            0x80000329: 5, 0x80000432: 5, 0xc0000250: 5}
TABLES = ((0x80000234, 46, 0x4ec38, 0x4ec28, 4),
          (0x80000270, 184, 0x4ec78, 0x4ec68, 4),
          (0x80000331, 248, 0x4ed44, 0x4ed30, 5),
          (0x80000450, 201, 0x4ee48, 0x4ee3c, 3))


def classify(identifier, rules):
    if type(identifier) is not int or not 0 <= identifier <= 0xffffffff:
        raise ValueError('Expected uint32 model ID')
    if identifier in EXPLICIT:
        return EXPLICIT[identifier]
    for table in rules['tables']:
        offset = identifier - table['base']
        if 0 <= offset < len(table['classes']):
            return table['classes'][offset]
    return 7


def extract(dll):
    raw = dll.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DLL_HASH:
        raise ValueError('Unknown compiler revision')
    pe = struct.unpack_from('<I', raw, 0x3c)[0]
    image_base = struct.unpack_from('<I', raw, pe + 24 + 28)[0]
    tables = []
    for base, count, selector_rva, jump_rva, target_count in TABLES:
        selectors = read_rva(raw, selector_rva, count)
        targets = struct.unpack('<' + str(target_count) + 'I', read_rva(raw, jump_rva, target_count * 4))
        target_rvas = [address - image_base for address in targets]
        if any(target not in RETURNS for target in target_rvas) or any(index >= target_count for index in selectors):
            raise ValueError('Unexpected family-gate dispatch table')
        tables.append(dict(base=base, selectorRva=hex(selector_rva), jumpRva=hex(jump_rva),
                           classes=[RETURNS[target_rvas[index]] for index in selectors]))
    return dict(dllSha256=DLL_HASH, functionRva='0x4eaf0', tables=tables,
                densePreparationBypassClasses=[8, 9, 10], defaultClass=7)


def native_classes(dll, ids):
    # This leaf function reads only the model ID at context+8 and constant tables.
    # The context here is fresh scratch memory, not a camera/compiler reference.
    extract(dll)  # Hash and dispatch-table gate even when called outside main.
    if not 1 <= len(ids) <= 256 or any(type(value) is not int or not 0 <= value <= 0xffffffff for value in ids):
        raise ValueError('Expected a bounded batch of uint32 IDs')
    import frida
    device = frida.get_local_device()
    host = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
    pid = device.spawn([str(host), '-NoLogo', '-NoProfile', '-WindowStyle', 'Hidden',
                        '-Command', 'Start-Sleep -Seconds 3600'])
    session = None
    try:
        session = device.attach(pid)
        script = session.create_script('''rpc.exports = { classify(path, ids) {
          const dll = Module.load(path);
          const fn = new NativeFunction(dll.base.add(0x4eaf0), 'uint32', ['pointer'], 'thiscall');
          return ids.map(id => { const ctx = Memory.alloc(12); ctx.add(8).writeU32(id);
            return fn(ctx); });
        }};''')
        script.load()
        device.resume(pid)
        return script.exports_sync.classify(str(dll.resolve()), ids)
    finally:
        if session is not None:
            try:
                session.detach()
            except Exception:
                pass
        device.kill(pid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll', 'baseline', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Research output already exists; refusing overwrite')
    rules = extract(args.dll)
    baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
    rows = [dict(model, payloadSize=group['payloadSize'])
            for group in baseline['routes'] for model in group['models']]
    rows.extend(dict(model, payloadSize=None) for model in baseline['failures'])
    if len({row['cameraId'] for row in rows}) != len(rows):
        raise ValueError('Duplicate baseline model IDs')
    for row in rows:
        row['internalFamilyClass'] = classify(row['cameraId'], rules)
        row['densePreparationBypassed'] = row['internalFamilyClass'] in (8, 9, 10)
    if args.native:
        values = native_classes(args.dll, [row['cameraId'] for row in rows])
        if len(values) != len(rows):
            raise ValueError('Incomplete native classifier results')
        for row, value in zip(rows, values):
            row['nativeClass'] = value
            row['nativeAgrees'] = value == row['internalFamilyClass']
    if hashlib.sha256(args.dll.read_bytes()).hexdigest() != DLL_HASH:
        raise RuntimeError('DLL changed during read-only experiment')
    report = dict(cameraAccess=False, dllModified=False, compilerPatched=False,
                  scope='Internal preparation dispatch only; not physical compatibility',
                  rules=rules, rows=rows, counts=dict(Counter(row['internalFamilyClass'] for row in rows)))
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
    print(json.dumps(dict(cases=len(rows), classes=report['counts'],
                         nativeAgreement=sum(row.get('nativeAgrees', False) for row in rows))))
    if args.native and not all(row['nativeAgrees'] for row in rows):
        raise RuntimeError('Static classification disagrees with native function; inspect private report')


if __name__ == '__main__':
    main()
