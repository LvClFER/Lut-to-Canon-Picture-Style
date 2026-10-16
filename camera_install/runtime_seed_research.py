"""Compare zero/FF in-memory derived-node initialization, not a camera installer."""
import argparse
import hashlib
import json
from pathlib import Path
from .compiler_regression import cipher_tables
from .pf3_field_experiments import compile_stock
from .virtual_compatibility import load_models


def compare_outputs(report, reference):
    if report.get('cameraAccess') is not False or report.get('compilerPatched') is not False:
        raise ValueError('Requires private offline unpatched compilation')
    baseline = reference['files'][0]
    if baseline.get('rcGet') != 0 or baseline.get('error') or baseline.get('sourceSha256') != report.get('sourceSha256'):
        raise ValueError('Reference must successfully compile the same source')
    rows = []
    groups = {}
    for item in report['rows']:
        succeeded = item.get('rcGet') == 0 and not item.get('error')
        if succeeded:
            payload = Path(item['privatePayload']).read_bytes()
            if hashlib.sha256(payload).hexdigest() != item.get('payloadSha256'):
                raise ValueError('Retained payload does not match trace')
        row = dict(model=item['model'],cameraId=item['cameraId'],seedByte=item['seedByte'],
                   compiled=succeeded,stockReferenceExact=succeeded and item.get('payloadSha256') == baseline.get('payloadSha256'),
                   rcGet=item.get('rcGet'),cameraCompatibility='not-tested')
        rows.append(row)
        groups.setdefault(item['cameraId'], {})[item['seedByte']] = item.get('payloadSha256') if succeeded else None
    independent = {hex(identifier):set(values) == {0,255} and bool(values[0]) and values[0] == values[255]
                   for identifier,values in groups.items()}
    return dict(cameraAccess=False,compilerPatched=False,rows=rows,seedIndependent=independent,
                lutApplicationValidated=False,
                scope='Equality to stock compiler output does not prove application of source LUT',
                successfulCases=sum(row['compiled'] for row in rows),
                exactStockReferenceCases=sum(row['stockReferenceExact'] for row in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll','source','descriptor','matrix'):
        parser.add_argument('--'+name,type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--compare-trace',type=Path)
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--seed-mode',choices=('derived','legacy-metadata'),default='derived')
    parser.add_argument('--explicit-dense-conversion',action='store_true',help='Private direct Canon converter invocation, not production or stock behavior')
    parser.add_argument('--observe-color',action='store_true',help='Read-only bounded converter source capture in the private host')
    args = parser.parse_args()
    if args.compare_trace:
        if not args.reference:
            parser.error('Comparison requires the stock reference trace')
        result = compare_outputs(json.loads(args.compare_trace.read_text(encoding='utf-8')),
                                 json.loads(args.reference.read_text(encoding='utf-8')))
        with args.output.open('x',encoding='utf-8') as output:
            json.dump(result,output,indent=2)
        print(result['successfulCases'],'compiled;',result['exactStockReferenceCases'],'exact stock reference')
        return
    if not all((args.dll,args.source,args.descriptor,args.matrix)):
        parser.error('Compilation requires DLL, source, descriptor and matrix')
    cipher_tables(args.dll)
    import frida
    device = frida.get_local_device()
    original = args.source.read_bytes()
    args.output.mkdir(parents=True,exist_ok=True)
    report = dict(cameraAccess=False,compilerPatched=False,experimentalRuntimePreconditioning=True,
                  seedMode=args.seed_mode,
                  diagnosticPayloadsNotInstallable=True,
                  explicitDenseConversion=args.explicit_dense_conversion,
                  dllSha256=hashlib.sha256(args.dll.read_bytes()).hexdigest(),
                  descriptorSha256=hashlib.sha256(args.descriptor.read_bytes()).hexdigest(),
                  researchAgentSha256=hashlib.sha256(Path(__file__).with_name('runtime_seed_probe.js').read_bytes()).hexdigest(),
                  cameraCompatibility='not-tested',sourceSha256=hashlib.sha256(original).hexdigest(),rows=[])
    for model in load_models(args.matrix):
        for seed in (0,255):
            try:
                result,payload = compile_stock(device,args.dll.resolve(),Path(__file__).with_name('runtime_seed_probe.js'),
                    args.source.resolve(),model['cameraId'],args.descriptor.read_bytes(),
                    observe=True,observe_dense=True,observe_color=args.observe_color,packing_only=not args.observe_color,runtime_seed=seed,runtime_seed_mode=args.seed_mode,
                    explicit_dense_conversion=args.explicit_dense_conversion)
                target = args.output/f'{model["cameraId"]:08x}_SEED_{seed:02X}.bin'
                with target.open('xb') as output: output.write(payload)
                result['privatePayload'] = str(target.resolve())
            except Exception as error:
                result = dict(getattr(error,'native_report',{}))
                result.update(error=str(error),classification='failed-not-validated')
            result.update(model=model['model'],cameraId=model['cameraId'],seedByte=seed)
            report['rows'].append(result)
            print(model['model'],seed,'FAILED' if result.get('error') else 'COMPILED',result.get('rcGet'),flush=True)
            (args.output/'RUNTIME_SEEDS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if args.source.read_bytes() != original:
        raise ValueError('Original fixture changed')


if __name__ == '__main__':
    main()
