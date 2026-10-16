'use strict';
// Read-only laboratory probe. No EDSDK, camera session, writes or compiler patch.
function hex(buffer) {
  const bytes = new Uint8Array(buffer);
  const digits = Array.from({length: 256}, (_, i) => i.toString(16).padStart(2, '0'));
  const out = new Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) out[i] = digits[bytes[i]];
  return out.join('');
}
rpc.exports.inspect = function(path, properties, cipherRva) {
  const module = Process.getModuleByName('EdsCFParse.dll');
  function api(name, args) {
    return new NativeFunction(module.getExportByName(name), 'uint32', args);
  }
  const initialize = api('EdsCfpInitialize', []);
  const create = api('EdsCfpCreateRef', ['pointer','uint32','uint32','pointer']);
  const sizeOf = api('EdsCfpGetPropertySize', ['pointer','uint32','uint32','pointer','pointer']);
  const get = api('EdsCfpGetPropertyData', ['pointer','uint32','uint32','uint32','pointer']);
  const release = api('EdsCfpRelease', ['pointer']);
  const captures = [];
  let capturedBytes = 0;
  const hook = Interceptor.attach(module.base.add(cipherRva), {
    onEnter(args) {
      this.length = args[1].toUInt32(); this.seed = args[2].toUInt32(); this.buffer = args[0];
      this.capture = this.length > 0 && this.length <= 1048576 && capturedBytes + this.length <= 2097152;
      if (this.capture) { this.before = this.buffer.readByteArray(this.length); capturedBytes += this.length; }
    },
    onLeave() {
      if (this.capture) captures.push({length: this.length, seed: this.seed,
        beforeHex: hex(this.before), afterHex: hex(this.buffer.readByteArray(this.length))});
    }
  });
  const out = Memory.alloc(Process.pointerSize); out.writePointer(ptr(0));
  let rcCreate;
  let rcInitialize;
  try {
    rcInitialize = initialize();
    rcCreate = create(Memory.allocUtf8String(path), 2, 0, out);
  } finally { hook.detach(); }
  const ref = out.readPointer();
  if (rcCreate !== 0 || ref.isNull()) throw new Error('PF3 open failed: ' + rcCreate);
  const results = {};
  const dispatchTargets = [];
  const referenceDispatchTargets = [];
  const vtable = ref.readPointer();
  for (let offset = 0; offset <= 0x30; offset += Process.pointerSize) {
    const address = vtable.add(offset).readPointer();
    const owner = address.isNull() ? null : Process.findModuleByAddress(address);
    referenceDispatchTargets.push({slotOffset:offset,ownerModule:owner ? owner.name : null,
      targetRva:owner ? address.sub(owner.base).toString() : null});
  }
  const parserDispatchTargets = [];
  const contentDispatchTargets = [];
  // Hash-checked x86 wrapper12840 delegates through ref+24, vtable slot14.
  const parser = ref.add(0x24).readPointer();
  if (!parser.isNull()) {
    const parserVtable = parser.readPointer();
    for (let offset = 0; offset <= 0x20; offset += Process.pointerSize) {
      const address = parserVtable.add(offset).readPointer();
      const owner = address.isNull() ? null : Process.findModuleByAddress(address);
      parserDispatchTargets.push({slotOffset:offset,ownerModule:owner ? owner.name : null,
        targetRva:owner ? address.sub(owner.base).toString() : null});
    }
    // ac70 delegates through parser+1c, content vtable slot4.
    const content = parser.add(0x1c).readPointer();
    if (!content.isNull()) {
      const contentVtable = content.readPointer();
      for (let offset = 0; offset <= 0x18; offset += Process.pointerSize) {
        const address = contentVtable.add(offset).readPointer();
        const owner = address.isNull() ? null : Process.findModuleByAddress(address);
        contentDispatchTargets.push({slotOffset:offset,ownerModule:owner ? owner.name : null,
          targetRva:owner ? address.sub(owner.base).toString() : null});
      }
    }
  }
  // Slots confirmed by the recorded x86 disassembly; caller validates DLL hash.
  for (const slot of [0xD11D4, 0xD11D8, 0xD11DC]) {
    const address = module.base.add(slot).readPointer();
    const owner = address.isNull() ? null : Process.findModuleByAddress(address);
    dispatchTargets.push({slotRva: '0x' + slot.toString(16), target: address.toString(),
      ownerModule: owner ? owner.name : null,
      targetRva: owner ? address.sub(owner.base).toString() : null});
  }
  try {
    for (const property of properties) {
      const type = Memory.alloc(4); type.writeU32(0);
      const size = Memory.alloc(4); size.writeU32(0);
      const rcSize = sizeOf(ref, property, 0, type, size);
      const length = size.readU32();
      const item = {rcSize: rcSize, type: type.readU32(), length: length};
      if (rcSize === 0 && length > 0 && length <= 1048576) {
        const buffer = Memory.alloc(length); buffer.writeByteArray(new Uint8Array(length));
        item.rcGet = get(ref, property, 0, length, buffer);
        if (item.rcGet === 0) item.dataHex = hex(buffer.readByteArray(length));
      }
      results['0x' + property.toString(16).padStart(8, '0')] = item;
    }
    return {rcInitialize: rcInitialize, rcCreate: rcCreate, properties: results,
      cipherCalls: captures, converterDispatchTargets: dispatchTargets,
      referenceDispatchTargets:referenceDispatchTargets,parserDispatchTargets:parserDispatchTargets,
      contentDispatchTargets:contentDispatchTargets};
  } finally { release(ref); }
};

rpc.exports.clone = function(sourcePath, outputPath, properties, mutationId, mutationHex, additionalMutations) {
  const module = Process.getModuleByName('EdsCFParse.dll');
  function api(name, args) { return new NativeFunction(module.getExportByName(name), 'uint32', args); }
  function check(rc, label) { if (rc !== 0) throw new Error(label + ': ' + rc); }
  const initialize = api('EdsCfpInitialize', []);
  const create = api('EdsCfpCreateRef', ['pointer','uint32','uint32','pointer']);
  const sizeOf = api('EdsCfpGetPropertySize', ['pointer','uint32','uint32','pointer','pointer']);
  const get = api('EdsCfpGetPropertyData', ['pointer','uint32','uint32','uint32','pointer']);
  const set = api('EdsCfpSetPropertyData', ['pointer','uint32','uint32','uint32','pointer']);
  const reflect = api('EdsCfpReflectProperty', ['pointer']);
  const release = api('EdsCfpRelease', ['pointer']);
  initialize();
  const sourceOut = Memory.alloc(Process.pointerSize); sourceOut.writePointer(ptr(0));
  const targetOut = Memory.alloc(Process.pointerSize); targetOut.writePointer(ptr(0));
  let source = ptr(0), target = ptr(0);
  try {
    check(create(Memory.allocUtf8String(sourcePath), 2, 0, sourceOut), 'Source open'); source = sourceOut.readPointer();
    check(create(Memory.allocUtf8String(outputPath), 1, 1, targetOut), 'Scratch output create'); target = targetOut.readPointer();
    for (const property of properties) {
      const type = Memory.alloc(4); type.writeU32(0);
      const size = Memory.alloc(4); size.writeU32(0);
      check(sizeOf(source, property, 0, type, size), 'Property size');
      const length = size.readU32();
      if (length === 0 || length > 1048576) throw new Error('Unexpected property size');
      const data = Memory.alloc(length);
      check(get(source, property, 0, length, data), 'Source property read');
      check(set(target, property, 0, length, data), 'Scratch property copy');
    }
    const mutation = new Uint8Array(mutationHex.length / 2);
    for (let i = 0; i < mutation.length; i++) mutation[i] = parseInt(mutationHex.slice(i * 2, i * 2 + 2), 16);
    const data = Memory.alloc(mutation.length); data.writeByteArray(mutation);
    // When used here, 0x115 is the PF3 file aggregate, never EDSDK registration state.
    check(set(target, mutationId, 0, mutation.length, data), 'Scratch-only controlled mutation');
    for (const extra of (additionalMutations || [])) {
      if (![0x40001022,0x4000102a].includes(extra.property) ||
          typeof extra.dataHex !== 'string' || !/^[0-9a-f]{8192}$/i.test(extra.dataHex)) {
        throw new Error('Only bounded private derived-record seed experiments are permitted');
      }
      const bytes = new Uint8Array(4096);
      for (let i=0;i<bytes.length;i++) bytes[i] = parseInt(extra.dataHex.slice(i*2,i*2+2),16);
      const buffer = Memory.alloc(bytes.length); buffer.writeByteArray(bytes);
      check(set(target,extra.property,0,bytes.length,buffer),'Scratch-only derived-record seed');
    }
    check(reflect(target), 'Canon serialize scratch file');
    return {ok: true};
  } finally {
    if (!target.isNull()) release(target);
    if (!source.isNull()) release(source);
  }
};
