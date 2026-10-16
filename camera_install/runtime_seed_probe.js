'use strict';
// Private offline API-preconditioning experiment, never an EOS Utility hook.
let seedByte = 0;
let seedMode = 'derived';
let explicitDenseConversion = false;
rpc.exports.loadcompiler = function(path) { Module.load(path); return true; };
function hex(pointer, length) {
  return Array.from(new Uint8Array(pointer.readByteArray(length)),
    value => value.toString(16).padStart(2,'0')).join('');
}
function bytes(value) {
  const result = new Uint8Array(value.length/2);
  for (let i=0;i<result.length;i++) result[i] = parseInt(value.slice(i*2,i*2+2),16);
  return result;
}
rpc.exports.configure = function(value,mode,explicitConversion) {
  if (![0,255].includes(value)) throw new Error('Only bounded zero/FF seed experiment');
  if (!['derived','legacy-metadata'].includes(mode)) throw new Error('Unknown private seed mode');
  seedByte = value;
  seedMode = mode;
  explicitDenseConversion = explicitConversion === true;
};
rpc.exports.compile = function(source, idHex, descriptorHex) {
  const module = Process.getModuleByName('EdsCFParse.dll');
  function api(name,args) { return new NativeFunction(module.getExportByName(name),'uint32',args); }
  const initialize = api('EdsCfpInitialize',[]);
  const create = api('EdsCfpCreateRef',['pointer','uint32','uint32','pointer']);
  const set = api('EdsCfpSetPropertyData',['pointer','uint32','uint32','uint32','pointer']);
  const sizeOf = api('EdsCfpGetPropertySize',['pointer','uint32','uint32','pointer','pointer']);
  const get = api('EdsCfpGetPropertyData',['pointer','uint32','uint32','uint32','pointer']);
  const release = api('EdsCfpRelease',['pointer']);
  const report = {rcInitialize:initialize(),experimentalRuntimePreconditioning:true,seedByte:seedByte,seedMode:seedMode};
  const out = Memory.alloc(Process.pointerSize); out.writePointer(ptr(0));
  report.rcCreate = create(Memory.allocAnsiString(source),2,0,out);
  const ref = out.readPointer();
  if (report.rcCreate !== 0 || ref.isNull()) return report;
  try {
    const originalDense = new Map();
    function denseState(stage) {
      if (!explicitDenseConversion) return;
      const rows = [];
      for (const property of [0x40001070,0x40001071]) {
        const type = Memory.alloc(4), size = Memory.alloc(4); type.writeU32(0); size.writeU32(0);
        const item = {property:property,rcSize:sizeOf(ref,property,0,type,size),size:size.readU32()};
        if (item.rcSize === 0 && item.size > 0 && item.size <= 1048576) {
          const buffer = Memory.alloc(item.size);
          item.rcGet = get(ref,property,0,item.size,buffer);
          if (item.rcGet === 0) {
            const values = new Uint8Array(buffer.readByteArray(item.size));
            let digest = 2166136261;
            for (const value of values) digest = Math.imul(digest ^ value,16777619) >>> 0;
            item.fnv1a32 = digest;
            item.prefixHex = hex(buffer,Math.min(24,item.size));
            if (!originalDense.has(property)) originalDense.set(property,values);
            const original = originalDense.get(property);
            item.byteIdenticalToOpenedFileProperty = original.length === values.length &&
              values.every((value,index) => value === original[index]);
          }
        }
        rows.push(item);
      }
      if (!report.denseTableStages) report.denseTableStages = [];
      report.denseTableStages.push({stage:stage,properties:rows});
    }
    denseState('opened-file');
    const length = seedMode === 'derived' ? 4096 : 1460;
    const properties = seedMode === 'derived' ? [0x40001022,0x4000102a] : [0x40001007];
    const seed = Memory.alloc(length); seed.writeByteArray(new Uint8Array(length).fill(seedByte));
    report.runtimeSeedResults = properties.map(property =>
      ({property:property,rc:set(ref,property,0,length,seed)}));
    const id = bytes(idHex), descriptor = bytes(descriptorHex);
    const idMemory = Memory.alloc(id.length); idMemory.writeByteArray(id);
    const descriptorMemory = Memory.alloc(descriptor.length); descriptorMemory.writeByteArray(descriptor);
    report.rcId = set(ref,0x01000001,0,id.length,idMemory);
    report.rcDescriptor = set(ref,0x01000210,0,descriptor.length,descriptorMemory);
    denseState('after-descriptor');
    if (explicitDenseConversion) {
      // Hash-gated own-host experiment: call Canon's converter, no hooks/patches.
      const parser = ref.add(0x24).readPointer();
      if (parser.isNull()) throw new Error('Missing known parser');
      const content = parser.add(0x1c).readPointer();
      if (content.isNull()) throw new Error('Missing known content');
      const records = content.add(4).readPointer();
      if (records.isNull()) throw new Error('Missing known record collection');
      const construct = new NativeFunction(module.base.add(0x4c610),'pointer',['pointer','pointer'],'thiscall');
      const readId = new NativeFunction(module.base.add(0x470b0),'uint32',['pointer'],'thiscall');
      const convert = new NativeFunction(module.base.add(0x4cd10),'uint32',['pointer'],'thiscall');
      const context = Memory.alloc(0x38); context.writeByteArray(new Uint8Array(0x38));
      construct(context,records);
      report.explicitConversionContextId = readId(context);
      if (report.explicitConversionContextId !== idMemory.readU32()) {
        report.explicitConversionNotRun = 'Context camera ID does not match requested virtual ID';
      } else {
        report.rcExplicitDenseConversion = convert(context);
      }
      denseState('after-explicit-conversion');
    }
    const type = Memory.alloc(4), size = Memory.alloc(4); type.writeU32(0); size.writeU32(0);
    report.rcSize = sizeOf(ref,0x01000203,0,type,size);
    report.outputType = type.readU32(); report.outputSize = size.readU32();
    if (report.rcSize === 0 && report.outputSize > 0 && report.outputSize <= 1048576) {
      const output = Memory.alloc(report.outputSize); output.writeByteArray(new Uint8Array(report.outputSize));
      report.rcGet = get(ref,0x01000203,0,report.outputSize,output);
      if (report.rcGet === 0) report.outputHex = hex(output,report.outputSize);
    }
    denseState('after-native-get');
    return report;
  } finally { release(ref); }
};
