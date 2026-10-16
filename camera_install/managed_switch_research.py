"""Independent, bounded extraction of simple subtract-and-switch IL dispatch."""
import argparse
import json
from pathlib import Path


def constant(instruction):
    opcode = instruction['opcode']
    if opcode in ('ldc.i4', 'ldc.i4.s'):
        return instruction['operand']
    if opcode == 'ldc.i4.m1':
        return -1
    if opcode.startswith('ldc.i4.') and opcode[-1] in '012345678':
        return int(opcode[-1])
    return None


def switches(method):
    instructions = method['instructions']
    offsets = {item['offset'] for item in instructions}
    rows = []
    for index, instruction in enumerate(instructions):
        if instruction['opcode'] != 'switch' or index < 3:
            continue
        load, base_instruction, subtract = instructions[index-3:index]
        base = constant(base_instruction)
        if not load['opcode'].startswith(('ldarg', 'ldloc')) or subtract['opcode'] != 'sub' or base is None:
            continue
        targets = instruction['branchTargets']
        if len(targets) != len(instruction['operand']) or any(target not in offsets for target in targets):
            raise ValueError('Incomplete switch or invalid instruction boundary')
        rows.append(dict(offset=instruction['offset'], input=load['opcode'], base=base,
                         entries=[dict(value=base+i, target=target) for i,target in enumerate(targets)]))
    return rows


def summarize(report):
    if any(report.get(key) is not False for key in ('cameraAccess', 'applicationExecuted', 'dllModified')) or report.get('complete') is not True:
        raise ValueError('Require complete reflection-only evidence')
    return dict(cameraAccess=False, applicationExecuted=False, binarySha256=report['binarySha256'],
                scope='Simple IL switch selection only; no runtime or physical validation',
                methods=[dict(method=method['method'], switches=switches(method))
                         for method in report['selectedMethods']])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = summarize(json.loads(args.source.read_text(encoding='utf-8')))
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2)
    print('Methods:', len(result['methods']), 'switches:', sum(len(row['switches']) for row in result['methods']))


if __name__ == '__main__':
    main()
