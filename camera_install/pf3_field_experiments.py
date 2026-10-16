"""Single-field scratch experiments with Canon serialization and stock compilation."""
import argparse
import hashlib
import json
import os
import struct
from pathlib import Path

from .compiler_regression import cipher_tables, decode
from .pf3_research import parse_records, probe


class StockCompilerError(RuntimeError):
    def __init__(self, report):
        self.native_report = report
        status = {key:report.get(key) for key in ('rcInitialize','rcCreate','rcId','rcDescriptor','rcSize','outputType','outputSize','rcGet')}
        super().__init__(f'Stock compiler failed: {status}')


def mutations(records):
    data = {r["id"]: r["data"] for r in records}
    nested = bytearray(data["0x1008"])
    # Nested opaque property retains BE bytes through the API. First sector's
    # candidate centre is word 5 (header 2 + group offset 3).
    struct.pack_into(">i", nested, 8 + 5 * 4, 10 * 65536)
    yield "SECTOR_CENTRE_PLUS10", 0x40001008, bytes(nested)
    for name in ("0x1019", "0x1018", "0x1065"):
        values = list(struct.unpack(f">{len(data[name]) // 4}I", data[name]))
        if values[:5] != [2, 0, 0, 255, 255]:
            raise ValueError("Unexpected curve layout; refusing mutation")
        values[4] = 230
        yield "CURVE_" + name[2:] + "_END230", 0x40000000 | int(name, 16), struct.pack(f"<{len(values)}I", *values)


def nonlinear_mutations(records):
    original = next(record["data"] for record in records if record["id"] == "0x1018")
    for name, points in [("MID96", [0, 0, 128, 96, 255, 255]),
                         ("MID160", [0, 0, 128, 160, 255, 255]),
                         ("NONMONOTONIC", [0, 0, 85, 220, 170, 40, 255, 255]),
                         ("UNEVEN5", [0, 0, 30, 60, 110, 90, 200, 240, 255, 255]),
                         ("ZIGZAG6", [0, 0, 40, 90, 80, 30, 140, 180, 220, 120, 255, 255])]:
        values = [len(points) // 2] + points
        values.extend([0] * (len(original) // 4 - len(values)))
        yield "NONLINEAR_1018_" + name, 0x40001018, struct.pack(f"<{len(values)}I", *values)


def third_curve_channel_mutations(records):
    """Historical1065 diagnostic label;1065 is native post-RGB, not Lab."""
    for name,prop,data in curve_channel_mutations(records,0x1065):
        yield name.replace('CURVE_1065_','THIRD_CURVE_'),prop,data


def curve_channel_mutations(records,identifier):
    if identifier not in (0x1018,0x1019,0x1065):raise ValueError('Unsupported curve record')
    original=next(record['data'] for record in records if record['id']==f'0x{identifier:04x}')
    if len(original)!=300:raise ValueError('Require three fixed 100-byte curve records')
    words=list(struct.unpack('>75I',original))
    for channel in range(3):
        if words[channel*25:channel*25+5]!=[2,0,0,255,255]:
            raise ValueError('Require observed two-point identity curves')
    for channel in range(3):
        values=words.copy();values[channel*25+4]=230
        yield f'CURVE_{identifier:04X}_CHANNEL{channel}_END230',0x40000000|identifier,struct.pack('<75I',*values)


def contrast_mutations(records):
    original = next(record['data'] for record in records if record['id'] == '0x1030')
    if original != bytes(4):
        raise ValueError('Contrast sweep requires the zero baseline fixture')
    for value in range(-4, 5):
        if value:
            label = ('MINUS' if value < 0 else 'PLUS') + str(abs(value))
            yield 'CONTRAST_' + label, 0x40001030, struct.pack('<i', value)


def basic_scalar_mutations(records, identifier):
    if identifier not in (0x1030, 0x1031):
        raise ValueError('Only the two candidate contrast/strength records are in scope')
    original = next(record['data'] for record in records if record['id'] == f'0x{identifier:04x}')
    if original != bytes(4):
        raise ValueError('Scalar sweep requires a zero baseline')
    for value in range(-4, 5):
        if value:
            label = ('MINUS' if value < 0 else 'PLUS') + str(abs(value))
            yield f'SCALAR_{identifier:04X}_' + label, 0x40000000 | identifier, struct.pack('<i', value)


def auxiliary_flag_mutations(records):
    data = {record['id']:record['data'] for record in records}
    for identifier in (0x100c,0x1011,0x1012,0x1080):
        original = data[f'0x{identifier:04x}']
        width = 2 if identifier == 0x100c else 4
        if len(original) != width or int.from_bytes(original,'big') not in (0,1):
            raise ValueError('Auxiliary flag experiment requires observed bounded zero/one fields')
        value = 1-int.from_bytes(original,'big')
        yield f'AUX_FLAG_{identifier:04X}_VALUE{value}', 0x40000000 | identifier, value.to_bytes(width,'little')


def sharpness_scalar_mutations(records, identifier):
    """Bounded private transport diagnostics, not camera-install candidates."""
    if identifier not in (0x1034, 0x1035):
        raise ValueError('Only fineness/threshold records are in scope')
    original = next(record['data'] for record in records if record['id'] == f'0x{identifier:04x}')
    if len(original) != 4:
        raise ValueError('Expected a four-byte sharpness scalar')
    baseline = struct.unpack('>I', original)[0]
    if not 0 <= baseline <= 5:
        raise ValueError('Require a bounded sharpness baseline (including the observed zero sentinel)')
    for value in range(0, 8):
        if value != baseline:
            yield f'SHARPNESS_{identifier:04X}_VALUE{value}', 0x40000000 | identifier, struct.pack('<I', value)


def matrix_mutations(records, out_of_gamut=False):
    data = {record['id']: record['data'] for record in records}
    for identifier in ('0x1021', '0x1029'):
        values = list(struct.unpack('>60i', data[identifier]))
        values[0] = values[0]*2 if out_of_gamut else values[0]//2
        suffix = '_FIRST_DOUBLE' if out_of_gamut else '_FIRST_HALF'
        yield 'MATRIX_' + identifier[2:] + suffix, 0x40000000 | int(identifier,16), struct.pack('<60i', *values)


def policy_mutations(records):
    data = {record['id']:record['data'] for record in records}
    for identifier in ('0x1023','0x102b'):
        for word in (0,1):
            values = list(struct.unpack('>2I',data[identifier]))
            values[word] = 2
            yield f'POLICY_{identifier[2:]}_WORD{word}_2', 0x40000000 | int(identifier,16), struct.pack('<2I',*values)


def old_selector_mutations(records,extended=False):
    """Test the structured-block hypothesis, never an incomplete count edit."""
    data={record['id']:record['data'] for record in records}
    for identifier in ('0x1023','0x102b'):
        if data[identifier]!=struct.pack('>2I',1,0):
            raise ValueError('Require the observed empty eight-byte old record')
        variants=[('H0',(0,0,0),None),('H5',(5,0,0),None)]
        if extended:variants.extend([('S5',(0,5,0),None),('L5',(0,0,5),None),
                                    ('H5S5L5',(5,5,5),None),('TARGET',(0,0,0),(193,43,47))])
        for label,deltas,target in variants:
            words=[1,1,5 if target else 4,0,180,50,50,1,0,0,0,2,360,100,100,3,*deltas]
            if target:words.extend([4,*target])
            yield f'OLD_SELECTOR_{identifier[2:]}_{label}',0x40000000|int(identifier,16),struct.pack('<'+str(len(words))+'i',*words)


def axis_parameter_mutations(records):
    data = {record['id']:record['data'] for record in records}
    for identifier in ('0x1061','0x1062'):
        for word in (16,17,18):
            values = list(struct.unpack('>128i',data[identifier]))
            if values[:2] != [2,6] or values[word] != 0:
                raise ValueError('Unexpected six-group parameter fixture')
            values[word] = 10
            yield f'AXIS_{identifier[2:]}_WORD{word}_PLUS10', 0x40000000 | int(identifier,16), struct.pack('<128i',*values)


def validate_icc_curve_control(agent_path, control):
    if control is None:
        return
    expected = Path(__file__).resolve().parents[2] / 'tmp/PF3_FIELD_EXPERIMENTS_20261004/ALTERNATE_FF0001_20261007/private_icc_curve_agent.js'
    if Path(agent_path).resolve() != expected:
        raise ValueError('ICC curve control requires dedicated private agent')
    if not isinstance(control, dict) or set(control) not in ({'property', 'channel'}, {'property', 'channel', 'shape'}):
        raise ValueError('Invalid ICC curve control fields')
    if type(control['property']) is not int or control['property'] not in (0x1018,0x1019,0x1065):
        raise ValueError('Invalid private curve property')
    if type(control['channel']) is not int or control['channel'] not in (0,1,2):
        raise ValueError('Invalid private curve channel')
    if control.get('shape','linear') not in ('linear','mid96'):
        raise ValueError('Invalid private curve shape')


def compile_stock(device, dll, agent_path, source, camera_id, descriptor, observe=False, observe_color=False, observe_dense=False, packing_only=False, runtime_seed=None, runtime_seed_mode='derived', explicit_dense_conversion=False, icc_curve_control=None):
    validate_icc_curve_control(agent_path,icc_curve_control)
    if icc_curve_control is not None and not observe:
        raise ValueError('ICC curve control requires known-hash observer gate')
    if runtime_seed_mode not in ('derived','legacy-metadata'):
        raise ValueError('Unknown private seed mode')
    if runtime_seed is not None and (runtime_seed not in (0,255) or agent_path.resolve() != Path(__file__).with_name('runtime_seed_probe.js').resolve()):
        raise ValueError('Runtime seed requires the dedicated private experimental agent')
    if explicit_dense_conversion and runtime_seed is None:
        raise ValueError('Explicit conversion requires the dedicated private experimental agent')
    if observe or runtime_seed is not None:
        cipher_tables(dll)  # Verify compiler revision before any fixed-RVA hooks.
    host = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "SysWOW64/WindowsPowerShell/v1.0/powershell.exe"
    pid = device.spawn([str(host), "-NoLogo", "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Start-Sleep -Seconds 3600"])
    session = None
    script = None
    observer = None
    try:
        session = device.attach(pid)
        script = session.create_script(agent_path.read_text(encoding="utf-8")); script.load()
        device.resume(pid)
        script.exports_sync.loadcompiler(str(dll))
        if icc_curve_control is not None:
            script.exports_sync.configureicc(icc_curve_control['property'],icc_curve_control['channel'],icc_curve_control.get('shape','linear'))
        if runtime_seed is not None:
            script.exports_sync.configure(runtime_seed,runtime_seed_mode,explicit_dense_conversion)
        if observe:
            mlib = dll.parent / "MLib.dll"
            if hashlib.sha256(mlib.read_bytes()).hexdigest() != "a36f3cea5ea5776cb542282ccf832abf9a0952eeb4d284db329a1463cd4a922a":
                raise ValueError("Unknown MLib revision; refusing fixed-RVA observation")
            observer_source = Path(__file__).with_name("mlib_observer.js").read_text(encoding="utf-8")
            observer = session.create_script(observer_source)
            observer.load()
            observer_info = observer.exports_sync.start(observe_color, observe_dense, packing_only)
            if Path(observer_info["mlibPath"]).resolve() != mlib.resolve():
                raise ValueError("Loaded MLib path differs from verified DLL")
        result = script.exports_sync.compile(str(source), struct.pack("<I", camera_id).hex(), descriptor.hex())
        payload = bytes.fromhex(result.pop("outputHex", ""))
        if observer is not None:
            result["mlibObservation"] = observer_info
            result["observerSha256"] = hashlib.sha256(observer_source.encode("utf-8")).hexdigest()
            result["mlibCalls"] = observer.exports_sync.finish()
        if not payload or any(result.get(key) != 0 for key in
                              ("rcCreate", "rcId", "rcDescriptor", "rcSize", "rcGet")):
            raise StockCompilerError(result)
        result.update(payloadSha256=hashlib.sha256(payload).hexdigest(), payloadSize=len(payload))
        return result, payload
    finally:
        if observer is not None:
            try: observer.unload()
            except Exception: pass
        if script is not None:
            try: script.unload()
            except Exception: pass
        if session is not None:
            try: session.detach()
            except Exception: pass
        try: device.kill(pid)
        except Exception: pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--descriptor", type=Path, required=True)
    parser.add_argument("--camera-id", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nonlinear-curves", action="store_true")
    parser.add_argument('--third-curve-channels',action='store_true',help='Private independent single-channel1065 curve diagnostics')
    parser.add_argument('--curve-channel-property',type=lambda value:int(value,0),choices=(0x1018,0x1019,0x1065),help='Identify native stage by independently changing three channels of one curve record')
    parser.add_argument('--contrast-values', action='store_true', help='Sweep the documented -4..+4 scalar contrast range in scratch files')
    parser.add_argument('--signed-control-property', type=lambda value:int(value,0), choices=(0x1030,0x1031), help='Research-only signed sweep of a candidate Basic record; labels do not assert its meaning')
    parser.add_argument('--auxiliary-flags', action='store_true', help='Toggle only observed zero/one auxiliary records in scratch files')
    parser.add_argument('--sharpness-property', type=lambda value:int(value,0), choices=(0x1034,0x1035), help='Private bounded 0..7 fineness/threshold transport diagnostics; not installable candidates')
    parser.add_argument("--observe", action="store_true")
    parser.add_argument("--observe-dense", action="store_true")
    parser.add_argument("--matrix-coefficients", action="store_true")
    parser.add_argument("--matrix-out-of-gamut", action="store_true", help="Double a coefficient in private scratch PF3s to exercise boundary handling")
    parser.add_argument("--policies", action="store_true", help="Probe the two small policy records, private scratch files only")
    parser.add_argument("--axis-parameters", action="store_true", help="Probe three candidate adjustment words in each six-group parameter record")
    parser.add_argument('--old-selectors',action='store_true',help='Test complete bounded variable-length0x1023/102b selective blocks')
    parser.add_argument('--retain-payloads',action='store_true',help='Retain private native outputs for final byte comparisons; never release fixtures')
    parser.add_argument('--old-selector-extended',action='store_true',help='Include saturation/lightness and five-point target selector hypotheses')
    parser.add_argument('--case-name',help='Run one exact private mutation name rather than the entire group')
    args = parser.parse_args()
    if args.old_selector_extended and not args.old_selectors:parser.error('Extended old selectors require --old-selectors')
    keys = cipher_tables(args.dll)
    raw = args.source.read_bytes()
    records, tail = parse_records(decode(raw[12:], keys, 12))
    if tail:
        raise ValueError("Unexpected decoded tail")
    properties = [0x40000000 | int(r["id"], 16) for r in records if int(r["id"], 16) < 0xfffe]
    args.output.mkdir(parents=True, exist_ok=True)
    import frida
    device = frida.get_local_device()
    descriptor = args.descriptor.read_bytes()
    baseline, payload = compile_stock(device, args.dll.resolve(), args.agent, args.source.resolve(), args.camera_id, descriptor,
                                      args.observe or args.observe_dense, observe_dense=args.observe_dense)
    report = {"cameraAccess": False, "compilerPatched": False, "writesOriginals": False,
              "dllSha256": hashlib.sha256(args.dll.read_bytes()).hexdigest(),
              "sourceSha256": hashlib.sha256(raw).hexdigest(),
              "descriptorSha256": hashlib.sha256(descriptor).hexdigest(),
              "cameraId": args.camera_id, "baseline": baseline, "experiments": []}
    selected_mutations = policy_mutations(records) if args.policies else (matrix_mutations(records, args.matrix_out_of_gamut) if args.matrix_coefficients or args.matrix_out_of_gamut else (nonlinear_mutations(records) if args.nonlinear_curves else mutations(records)))
    if args.axis_parameters: selected_mutations = axis_parameter_mutations(records)
    if args.third_curve_channels:selected_mutations=third_curve_channel_mutations(records)
    if args.curve_channel_property is not None:selected_mutations=curve_channel_mutations(records,args.curve_channel_property)
    if args.old_selectors:selected_mutations=old_selector_mutations(records,args.old_selector_extended)
    if args.contrast_values:selected_mutations=contrast_mutations(records)
    if args.signed_control_property is not None:selected_mutations=basic_scalar_mutations(records,args.signed_control_property)
    if args.auxiliary_flags:selected_mutations=auxiliary_flag_mutations(records)
    if args.sharpness_property is not None:selected_mutations=sharpness_scalar_mutations(records,args.sharpness_property)
    if args.case_name:
        selected_mutations=[row for row in selected_mutations if row[0]==args.case_name]
        if not selected_mutations:raise ValueError('Unknown private mutation name')
    for name, prop, data in selected_mutations:
        scratch = (args.output / (name + ".pf3")).resolve()
        if scratch == args.source.resolve() or scratch.exists():
            raise ValueError(f"Refusing to overwrite existing research file: {scratch}")
        inspected = probe(device, args.dll.resolve(), args.source.resolve(), [prop],
                          {"path": scratch, "properties": properties, "property": prop, "data": data})
        actual = inspected["properties"][f"0x{prop:08x}"].get("dataHex")
        if actual != data.hex():
            raise ValueError("Canon did not preserve the requested mutation")
        scratch_records, scratch_tail = parse_records(decode(scratch.read_bytes()[12:], keys, 12))
        original_fields = {r["id"]: r["data"] for r in records if int(r["id"], 16) < 0xfffe}
        scratch_fields = {r["id"]: r["data"] for r in scratch_records if int(r["id"], 16) < 0xfffe}
        changed_fields = [key for key in original_fields if original_fields[key] != scratch_fields.get(key)]
        expected_field = f"0x{prop & 0xffff:04x}"
        if scratch_tail or set(original_fields) != set(scratch_fields) or changed_fields != [expected_field]:
            raise ValueError(f"Scratch serialization changed unrelated fields: {changed_fields}")
        try:
            result, output = compile_stock(device, args.dll.resolve(), args.agent, scratch, args.camera_id, descriptor,
                                          args.observe or args.observe_dense, observe_dense=args.observe_dense)
        except Exception as error:
            # Unsupported scratch values can crash the isolated Canon host.
            # Preserve the failed experiment and continue in a fresh host;
            # never classify a crash as a valid compiler result.
            report['experiments'].append({'name':name,'mutationProperty':hex(prop),
                'serializedMutationExact':True,'changedSerializedFields':changed_fields,
                'classification':'failed-not-validated','error':str(error)})
            (args.output / 'FIELD_EXPERIMENTS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(name,'FAILED-NOT-VALIDATED',str(error),flush=True)
            continue
        result.update(name=name, mutationProperty=hex(prop), serializedMutationExact=True,
                      changedSerializedFields=changed_fields,
                      sameSizeAsBaseline=len(output) == len(payload),
                      changedByteCount=sum(a != b for a, b in zip(payload, output)),
                      changedOffsets=[i for i, (a, b) in enumerate(zip(payload, output)) if a != b][:64])
        if args.retain_payloads:
            native_path=(args.output/(name+'_PRIVATE_NATIVE_PAYLOAD.bin')).resolve()
            if native_path.exists():raise ValueError('Refusing to overwrite private native payload')
            native_path.write_bytes(output)
            result['privateResearchPayload']=str(native_path)
        report["experiments"].append(result)
        (args.output / "FIELD_EXPERIMENTS.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(name, result["payloadSize"], result["changedByteCount"], flush=True)


if __name__ == "__main__":
    main()
