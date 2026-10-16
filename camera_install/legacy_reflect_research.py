"""Test exported Canon reflection on private source copies before legacy compilation."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from .compiler_regression import cipher_tables
from .pf3_field_experiments import compile_stock


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--descriptor',type=Path,required=True)
    parser.add_argument('--source',type=Path,action='append',required=True)
    parser.add_argument('--observe-records',action='store_true')
    parser.add_argument('--camera-id',type=lambda v:int(v,0),action='append')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    cipher_tables(args.dll)
    import frida
    device=frida.get_local_device()
    args.output.mkdir(exist_ok=False,parents=True)
    report=dict(cameraAccess=False,installedDllModified=False,sourceFilesModified=False,
                descriptorSha256=hashlib.sha256(args.descriptor.read_bytes()).hexdigest(),rows=[])
    models=[('5D',0x80000213),('1D II N',0x80000232),('30D',0x80000234),
            ('400D',0x80000236),('10D',0x80000168),('M50',1042)]
    if args.camera_id:
        if set(args.camera_id)-{identifier for _,identifier in models}:
            raise ValueError('Requested ID is outside this bounded experiment')
        models=[row for row in models if row[1] in args.camera_id]
    for source in args.source:
        original=source.read_bytes()
        for model,identifier in models:
            clone=args.output/f'{source.stem}_{identifier:08x}{source.suffix}'
            shutil.copyfile(source,clone)
            try:
                result,payload=compile_stock(device,args.dll.resolve(),Path(__file__).with_name('legacy_reflect_probe.js'),
                                             clone.resolve(),identifier,args.descriptor.read_bytes(),observe=True,
                                             observe_dense=args.observe_records,packing_only=True)
                result.update(compiled=True,payloadSha256=hashlib.sha256(payload).hexdigest())
            except Exception as error:
                result=dict(getattr(error,'native_report',{}))
                result.update(compiled=False,error=str(error))
            result.update(model=model,cameraId=identifier,sourceSha256=hashlib.sha256(original).hexdigest(),
                          sourceName=source.name,scratchSourceChanged=clone.read_bytes()!=original)
            report['rows'].append(result)
            print(source.name,model,'reflect',result.get('rcReflect'),'get',result.get('rcGet'),
                  'compiled',result['compiled'],flush=True)
            with (args.output/'REFLECT_RESULTS.json').open('w',encoding='utf-8') as output:
                json.dump(report,output,indent=2)
        if source.read_bytes()!=original:
            raise ValueError('Source fixture changed')


if __name__=='__main__':
    main()
