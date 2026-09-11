'use strict';

let seq = 0;
let readySent = false;
let compilerHooked = false;
let edsHooked = false;
let compilerBusy = false;
let armed = false;
let armedSlot = 0;
let armedPf3Path = '';
let armedName = 'PICTURE STYLE';
let capturedCameraId = null;
let capturedDescriptor = null;

// Diagnostic labels only. Carrier size never selects a payload builder: every
// camera goes through the same live EdsCFParse compilation below.
const KNOWN_CARRIER_OBSERVATIONS = [
  { id: 'observed-8164', sizes: [8164], status: 'universal-canon-compiler' },
  { id: 'observed-8168', sizes: [8168], status: 'universal-canon-compiler' },
  { id: 'observed-8528', sizes: [8528], status: 'universal-canon-compiler' },
  { id: 'observed-16720', sizes: [16720], status: 'universal-canon-compiler' },
  { id: 'observed-16744-16752', sizes: [16744, 16752], status: 'universal-canon-compiler' },
  { id: 'observed-78980', sizes: [78980], status: 'universal-canon-compiler' },
  { id: 'observed-83076', sizes: [83076], status: 'universal-canon-compiler' },
  { id: 'observed-431616', sizes: [431616], status: 'universal-canon-compiler' }
];

function detectCarrierFamily(bytes) {
  const size = bytes.length;
  for (const family of KNOWN_CARRIER_OBSERVATIONS) {
    if (family.sizes.indexOf(size) >= 0) return family;
  }
  return { id: 'observed-new-' + size, sizes: [size], status: 'universal-canon-compiler-new-carrier' };
}

function emit(o, data) {
  o.seq = ++seq;
  o.ts = Date.now();
  send(o, data || null);
}

function ex(m, n) {
  try {
    return m.enumerateExports().find(e => e.type === 'function' && e.name === n) || null;
  } catch (_) { return null; }
}

function hexToBytes(value) {
  const hex = String(value || '').replace(/\s/g, '');
  if (!/^[0-9a-fA-F]*$/.test(hex) || (hex.length % 2) !== 0) throw new Error('invalid hexadecimal payload');
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.substr(i * 2, 2), 16);
  return out;
}

function bytesToHex(value) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  let out = '';
  for (let i = 0; i < bytes.length; i++) out += bytes[i].toString(16).padStart(2, '0');
  return out;
}

function readBytes(pointer, size) {
  if (pointer.isNull() || size <= 0 || size > 1048576) throw new Error('invalid native buffer');
  return new Uint8Array(pointer.readByteArray(size));
}

function copyToMemory(bytes) {
  const memory = Memory.alloc(bytes.length);
  memory.writeByteArray(bytes);
  return memory;
}

function buildCanonNativeCarrier(nativeCarrier, family) {
  const compiled = compilePf3WithAcceptedTables(
    armedPf3Path, bytesToHex(capturedCameraId), bytesToHex(capturedDescriptor)
  );
  const compiler = compiled[0];
  const output = new Uint8Array(compiled[1]);
  if (!compiler.ok) throw new Error('Canon-native PF3 acceptance compile failed: ' +
    (compiler.acceptanceError || 'compiler error') + ' · ' + JSON.stringify(compiler.acceptanceHook || {}));
  if (output.length !== nativeCarrier.length) {
    throw new Error('Canon selected a ' + output.length + '-byte carrier but EOS Utility supplied ' + nativeCarrier.length + ' bytes');
  }
  const validation = validateNativeRoundTrip(nativeCarrier, output);
  return { output: output, metadata: {
    strategy: 'canon-native-pf3-compiler-universal-v2',
    familyId: family.id, familyStatus: family.status, outputSize: output.length,
    tableProperties: ['0x40001070', '0x40001071'],
    nameSource: 'Canon PF3 metadata compiled by EdsCFParse',
    compilerSelectedCarrier: true,
    acceptanceHook: compiler.acceptanceHook,
    sentinelOffset: validation.sentinelOffset, meaningfulStart: validation.meaningfulStart,
    totalDifferences: validation.totalDifferences,
    meaningfulDifferences: validation.meaningfulDifferences,
    cameraIdHex: bytesToHex(capturedCameraId), descriptorSize: capturedDescriptor.length
  }};
}

function magicOffset(bytes) {
  for (let i = 0; i + 7 < bytes.length; i++) {
    if (bytes[i] === 0xef && bytes[i + 1] === 0xbe && bytes[i + 2] === 0xad && bytes[i + 3] === 0xde &&
        bytes[i + 4] === 0xef && bytes[i + 5] === 0xbe && bytes[i + 6] === 0xad && bytes[i + 7] === 0xde) return i;
  }
  return -1;
}

function validateNativeRoundTrip(nativeCarrier, output) {
  if (nativeCarrier.length !== output.length) throw new Error('Canon output size does not match the genuine camera carrier');
  if (nativeCarrier.length < 128 || nativeCarrier.length > 1048576) throw new Error('Genuine camera carrier size is outside the guarded range');
  for (let i = 0; i < 8; i++) {
    if (nativeCarrier[i] !== output[i]) throw new Error('Canon output header does not match the genuine carrier family');
  }
  const nativeMagic = magicOffset(nativeCarrier);
  const outputMagic = magicOffset(output);
  if ((nativeMagic >= 0 || outputMagic >= 0) && outputMagic !== nativeMagic) {
    throw new Error('Canon output carrier sentinel does not match the genuine transaction');
  }
  // Canon's known payload families use the DEADBEEF sentinel.  A future
  // carrier may not; in that case keep validation format-agnostic and exclude
  // the complete leading name/metadata area from the transform comparison.
  const meaningfulStart = nativeMagic >= 0 ? nativeMagic + 276 : 256;
  if (meaningfulStart >= nativeCarrier.length) throw new Error('Canon carrier has no validated PF3 data region');
  let totalDifferences = 0;
  let meaningfulDifferences = 0;
  for (let i = 0; i < nativeCarrier.length; i++) {
    if (nativeCarrier[i] !== output[i]) {
      totalDifferences++;
      if (i >= meaningfulStart) meaningfulDifferences++;
    }
  }
  if (totalDifferences === 0) throw new Error('Canon compiler output is identical to the genuine default carrier');
  if (meaningfulDifferences === 0) throw new Error('Canon compiler changed only carrier metadata; the PF3 transform was not incorporated');
  return { sentinelOffset: nativeMagic >= 0 ? nativeMagic : null, meaningfulStart: meaningfulStart, totalDifferences: totalDifferences, meaningfulDifferences: meaningfulDifferences };
}

function compilerApi() {
  const module = Process.getModuleByName('EdsCFParse.dll');
  const initializeExport = ex(module, 'EdsCfpInitialize');
  const createExport = ex(module, 'EdsCfpCreateRef');
  const setExport = ex(module, 'EdsCfpSetPropertyData');
  const sizeExport = ex(module, 'EdsCfpGetPropertySize');
  const getExport = ex(module, 'EdsCfpGetPropertyData');
  const releaseExport = ex(module, 'EdsCfpRelease');
  if (!initializeExport || !createExport || !setExport || !sizeExport || !getExport || !releaseExport) throw new Error('Required EdsCFParse exports not found');
  return {
    module: module,
    Initialize: new NativeFunction(initializeExport.address, 'uint32', []),
    Create: new NativeFunction(createExport.address, 'uint32', ['pointer', 'uint32', 'uint32', 'pointer']),
    Set: new NativeFunction(setExport.address, 'uint32', ['pointer', 'uint32', 'uint32', 'uint32', 'pointer']),
    GetSize: new NativeFunction(sizeExport.address, 'uint32', ['pointer', 'uint32', 'uint32', 'pointer', 'pointer']),
    Get: new NativeFunction(getExport.address, 'uint32', ['pointer', 'uint32', 'uint32', 'uint32', 'pointer']),
    Release: new NativeFunction(releaseExport.address, 'uint32', ['pointer'])
  };
}

function compilePf3(path, cameraIdHex, descriptorHex) {
  const api = compilerApi();
  const rcInitialize = api.Initialize();
  if (rcInitialize !== 0 && rcInitialize !== 2) {
    return [{ ok: false, rcInitialize: rcInitialize }, new ArrayBuffer(0)];
  }
  const pathMemory = Memory.allocUtf8String(String(path));
  const outRef = Memory.alloc(Process.pointerSize);
  outRef.writePointer(ptr(0));
  const rcCreate = api.Create(pathMemory, 2, 0, outRef);
  const ref = outRef.readPointer();
  if (rcCreate !== 0 || ref.isNull()) return [{ ok: false, rcInitialize: rcInitialize, rcCreate: rcCreate }, new ArrayBuffer(0)];
  compilerBusy = true;
  try {
    const cameraId = hexToBytes(cameraIdHex);
    const descriptor = hexToBytes(descriptorHex);
    const rcId = api.Set(ref, 0x01000001, 0, cameraId.length, copyToMemory(cameraId));
    const rcDescriptor = api.Set(ref, 0x01000210, 0, descriptor.length, copyToMemory(descriptor));
    const dataType = Memory.alloc(4); dataType.writeU32(0);
    const dataSize = Memory.alloc(4); dataSize.writeU32(0);
    const rcSize = api.GetSize(ref, 0x01000203, 0, dataType, dataSize);
    const outputSize = dataSize.readU32();
    let rcGet = 0xffffffff;
    let data = new ArrayBuffer(0);
    if (rcSize === 0 && outputSize > 0 && outputSize <= 1048576) {
      const output = Memory.alloc(outputSize);
      output.writeByteArray(new Uint8Array(outputSize));
      rcGet = api.Get(ref, 0x01000203, 0, outputSize, output);
      if (rcGet === 0) data = output.readByteArray(outputSize);
    }
    const rcRelease = api.Release(ref);
    return [{
      ok: rcCreate === 0 && rcId === 0 && rcDescriptor === 0 && rcSize === 0 && rcGet === 0,
      rcInitialize: rcInitialize, rcCreate: rcCreate, rcId: rcId, rcDesc: rcDescriptor, rcSize: rcSize,
      rcGet: rcGet, rcRelease: rcRelease, outputSize: outputSize, outputType: dataType.readU32()
    }, data];
  } finally {
    compilerBusy = false;
  }
}

function assertCodeSignature(module, rva, expected) {
  const actual = new Uint8Array(module.base.add(rva).readByteArray(expected.length));
  for (let index = 0; index < expected.length; index++) {
    if (actual[index] !== expected[index]) {
      throw new Error('Unsupported EdsCFParse code signature at 0x' + rva.toString(16));
    }
  }
}

function installPf3AcceptanceHooks() {
  const module = Process.getModuleByName('EdsCFParse.dll');
  if (module.size !== 901120) {
    throw new Error('Unsupported EdsCFParse build for the Canon-native PF3 acceptance hook: ' + module.size);
  }
  assertCodeSignature(module, 0x4d8d0, [0x55, 0x8b, 0xec, 0x81, 0xec, 0x84, 0x04, 0x00, 0x00]);
  assertCodeSignature(module, 0x48d10, [0x55, 0x8b, 0xec, 0xb8, 0x10, 0x58, 0x00, 0x00]);
  assertCodeSignature(module, 0x46fd0, [0x55, 0x8b, 0xec, 0x33, 0xc0, 0x83, 0x7d, 0x08, 0x01]);
  assertCodeSignature(module, 0x46a50, [0x55, 0x8b, 0xec, 0xa1]);
  assertCodeSignature(module, 0x49830, [0x55, 0x8b, 0xec, 0xb8, 0x14, 0x50, 0x00, 0x00]);
  assertCodeSignature(module, 0x4a2b0, [0x55, 0x8b, 0xec, 0x56, 0xff, 0x75, 0x08]);

  const ReadDenseGrid = new NativeFunction(
    module.base.add(0x46fd0), 'uint32', ['pointer', 'uint32', 'pointer'], 'thiscall'
  );
  const DenseGridToIntermediate = new NativeFunction(
    module.base.add(0x46a50), 'void', ['pointer', 'uint32', 'uint32', 'pointer']
  );
  const results = { dense17: [], dense10: [], auxiliary: [] };
  let overrideActive = false;
  const hooks = [];

  hooks.push(Interceptor.attach(module.base.add(0x4d8d0), {
    onEnter(args) {
      this.self = this.context.ecx;
      this.gridIndex = args[0].toUInt32();
      this.output = args[1];
    },
    onLeave(returnValue) {
      const item = { index: this.gridIndex, originalResult: returnValue.toUInt32(), applied: false };
      if (!overrideActive && (this.gridIndex === 1 || this.gridIndex === 2)) {
        overrideActive = true;
        try {
          const sourceOut = Memory.alloc(Process.pointerSize);
          sourceOut.writePointer(ptr(0));
          const rcRead = ReadDenseGrid(this.self, this.gridIndex, sourceOut);
          const source = sourceOut.readPointer();
          item.readDenseGrid = rcRead;
          if (rcRead !== 0 && !source.isNull()) {
            this.output.writeU32(3);
            this.output.add(4).writeU32(17);
            this.output.add(8).writeU32(0x1cc98);
            this.output.add(12).writeU32(2);
            DenseGridToIntermediate(source, 0, this.gridIndex, this.output);
            returnValue.replace(1);
            item.applied = true;
          }
        } catch (error) {
          item.error = String(error);
        } finally {
          overrideActive = false;
        }
      }
      results.dense17.push(item);
    }
  }));

  // When the live Canon descriptor selects a 10x10x10 intermediate grid, the
  // stock PF3 branch builds that grid from
  // Canon's base-profile records and can silently ignore arbitrary 33^3 PF3
  // tables.  Feed the same dense PF3 source through Canon's own generic grid
  // converter, with the exact 10-node structure selected by the live camera.
  hooks.push(Interceptor.attach(module.base.add(0x48d10), {
    onEnter(args) {
      this.self = this.context.ecx;
      this.gridIndex = args[0].toUInt32();
      this.output = args[1];
    },
    onLeave(returnValue) {
      const item = { index: this.gridIndex, originalResult: returnValue.toUInt32(), applied: false };
      if (results.dense17.length === 0 && !overrideActive && (this.gridIndex === 1 || this.gridIndex === 2)) {
        overrideActive = true;
        try {
          const sourceOut = Memory.alloc(Process.pointerSize);
          sourceOut.writePointer(ptr(0));
          const rcRead = ReadDenseGrid(this.self, this.gridIndex, sourceOut);
          const source = sourceOut.readPointer();
          item.readDenseGrid = rcRead;
          if (rcRead !== 0 && !source.isNull()) {
            this.output.writeU32(3);
            this.output.add(4).writeU32(10);
            this.output.add(8).writeU32(0x5dc0);
            this.output.add(12).writeU32(1);
            DenseGridToIntermediate(source, 0, this.gridIndex, this.output);
            returnValue.replace(1);
            item.applied = true;
          }
        } catch (error) {
          item.error = String(error);
        } finally {
          overrideActive = false;
        }
      }
      results.dense10.push(item);
    }
  }));

  {
    const ConvertGrid33ForCamera = new NativeFunction(
      module.base.add(0x4cd10), 'uint32', ['pointer'], 'thiscall'
    );
    const ReadCompactGrid = new NativeFunction(
      module.base.add(0x46f50), 'uint32', ['pointer', 'uint32', 'pointer'], 'thiscall'
    );
    const SetInternalProperty = new NativeFunction(
      module.base.add(0x4a2b0), 'uint32',
      ['pointer', 'uint32', 'uint32', 'pointer', 'uint32', 'uint32'], 'thiscall'
    );
    hooks.push(Interceptor.attach(module.base.add(0x49830), {
      onEnter(args) {
        this.self = this.context.ecx;
        this.compact = Memory.alloc(0x1000);
        this.compact.writeByteArray(new Uint8Array(0x1000));
        const item = { converted: false, applied: false };
        this.itemIndex = results.auxiliary.length;
        try {
          item.convertResult = ConvertGrid33ForCamera(this.context.ecx);
          item.readCompactGrid = ReadCompactGrid(this.context.ecx, 1, this.compact);
          item.converted = item.convertResult !== 0 && item.readCompactGrid !== 0;
        } catch (error) {
          item.error = String(error);
        }
        results.auxiliary.push(item);
      },
      onLeave(returnValue) {
        const item = results.auxiliary[this.itemIndex];
        if (item && item.converted && !item.error) {
          try {
            item.setResult = SetInternalProperty(this.self, 0x1f02, 0x1000, this.compact, 0, 1);
            item.applied = item.setResult === 0;
          } catch (error) {
            item.error = String(error);
          }
        }
      }
    }));
  }
  return {
    results: results,
    detach: function() {
      for (const hook of hooks) {
        try { hook.detach(); } catch (_) {}
      }
    }
  };
}

function compilePf3WithAcceptedTables(path, cameraIdHex, descriptorHex) {
  const acceptance = installPf3AcceptanceHooks();
  try {
    const compiled = compilePf3(path, cameraIdHex, descriptorHex);
    const metadata = compiled[0];
    const dense17Events = acceptance.results.dense17.filter(item => item.index === 1 || item.index === 2);
    const dense10Events = acceptance.results.dense10.filter(item => item.index === 1 || item.index === 2);
    const dense17Applied = dense17Events.filter(item => item.applied).map(item => item.index);
    const dense10Applied = dense10Events.filter(item => item.applied).map(item => item.index);
    const requiredDense17 = dense17Events.length === 0 || (dense17Applied.indexOf(1) >= 0 && dense17Applied.indexOf(2) >= 0);
    const dense10IsSelectedPath = dense17Events.length === 0 && dense10Events.length > 0;
    const requiredDense10 = !dense10IsSelectedPath || (dense10Applied.indexOf(1) >= 0 && dense10Applied.indexOf(2) >= 0);
    const compilerGridPathSeen = dense17Events.length > 0 || dense10Events.length > 0;
    const auxiliarySeen = acceptance.results.auxiliary.length > 0;
    const auxiliaryApplied = !auxiliarySeen || acceptance.results.auxiliary.some(item => item.applied);
    metadata.acceptanceHook = {
      version: 2,
      rcInitialize: metadata.rcInitialize,
      compilerGridPathSeen: compilerGridPathSeen,
      dense17BuilderSeen: dense17Events.length > 0,
      dense17IndicesApplied: dense17Applied,
      dense10BuilderSeen: dense10Events.length > 0,
      dense10IndicesApplied: dense10Applied,
      auxiliaryBuilderSeen: auxiliarySeen,
      auxiliaryApplied: auxiliaryApplied,
      errors: acceptance.results.dense17.concat(acceptance.results.dense10, acceptance.results.auxiliary)
        .filter(item => item && item.error).map(item => item.error)
    };
    if (!metadata.ok || !requiredDense17 || !requiredDense10 || !auxiliaryApplied || metadata.acceptanceHook.errors.length) {
      metadata.ok = false;
      metadata.acceptanceError = 'Canon-native PF3 table acceptance hook did not complete every required conversion';
    }
    return [metadata, compiled[1]];
  } finally {
    acceptance.detach();
  }
}

function compileForNativeCarrier(nativeCarrier) {
  if (!capturedCameraId || capturedCameraId.length !== 4) throw new Error('Live Canon camera ID was not captured');
  if (!capturedDescriptor || capturedDescriptor.length === 0) throw new Error('Live Canon camera descriptor was not captured');
  if (!armedPf3Path) throw new Error('No PF3 is armed');
  const family = detectCarrierFamily(nativeCarrier);
  return buildCanonNativeCarrier(nativeCarrier, family);
}

function hookCompilerInputs() {
  let module;
  try { module = Process.getModuleByName('EdsCFParse.dll'); } catch (_) { return false; }
  const target = ex(module, 'EdsCfpSetPropertyData');
  if (!target) return false;
  Interceptor.attach(target.address, { onEnter(args) {
    if (!armed || compilerBusy) return;
    const property = args[1].toUInt32();
    const size = args[3].toUInt32();
    try {
      if (property === 0x01000001 && size === 4) {
        capturedCameraId = readBytes(args[4], size);
        emit({ type: 'compiler_input_captured', input: 'cameraId', size: size, cameraIdHex: bytesToHex(capturedCameraId) });
      } else if (property === 0x01000210 && size > 0 && size <= 1048576) {
        capturedDescriptor = readBytes(args[4], size);
        emit({ type: 'compiler_input_captured', input: 'descriptor', size: size });
      }
    } catch (error) {
      emit({ type: 'compiler_input_error', property: property, size: size, error: String(error) });
    }
  }});
  compilerHooked = true;
  return true;
}

function hookEdsdk() {
  let module;
  try { module = Process.getModuleByName('EDSDK.dll'); } catch (_) { return false; }
  const target = ex(module, 'EdsSetPropertyData');
  if (!target) return false;
  Interceptor.attach(target.address, {
    onEnter(args) {
      this.prop = args[1].toUInt32();
      this.param = args[2].toInt32();
      this.n = args[3].toUInt32();
      this.didPatchPayload = false;
      const observedSlot = this.param - 32;
      const isUserDefSlot = observedSlot >= 1 && observedSlot <= 3;
      if (this.prop === 0x01000203) emit({ type: 'registration_seen', slot: observedSlot, inParam: this.param, size: this.n, armed: armed });

      // 0x00000115 is binary state/control data. Observe only; do not modify.
      if (this.prop === 0x00000115 && armed && isUserDefSlot) emit({ type: 'control115_seen', slot: observedSlot, size: this.n, untouched: true });
      if (!armed || this.prop !== 0x01000203 || !isUserDefSlot) return;
      if (this.n <= 0 || this.n > 1048576 || args[4].isNull()) {
        emit({ type: 'install_error', reason: 'Genuine Canon registration carrier is invalid', size: this.n, slot: observedSlot });
        return;
      }
      try {
        const nativeCarrier = readBytes(args[4], this.n);
        const family = detectCarrierFamily(nativeCarrier);
        emit({
          type: 'carrier_family_detected', familyId: family.id, familyStatus: family.status,
          installEnabled: true, compilerRoute: 'universal-live-eds-cfparse', size: this.n
        });
        emit({ type: 'native_payload_observed', slot: observedSlot, inParam: this.param, size: this.n, readOnly: true, argumentsModified: false }, nativeCarrier.buffer);
        if (family.id.indexOf('observed-new-') === 0) {
          emit({
            type: 'native_payload_captured', slot: observedSlot, inParam: this.param, size: this.n,
            familyId: family.id, familyStatus: family.status, readOnly: true, argumentsModified: false
          }, nativeCarrier.buffer);
        }
        const compiled = compileForNativeCarrier(nativeCarrier);
        const outgoing = compiled.output;
        this.payloadMemory = copyToMemory(outgoing);
        args[3] = ptr(outgoing.length);
        args[4] = this.payloadMemory;
        this.didPatchPayload = true;
        emit({
          type: 'payload_patched', slot: observedSlot, size: outgoing.length, nativeSize: this.n,
          styleName: armedName, compiler: compiled.metadata, dynamicCameraFamily: true
        }, outgoing.buffer);
      } catch (error) {
        emit({
          type: 'install_error', reason: 'Dynamic Canon payload validation failed: ' + String(error),
          size: this.n, slot: observedSlot, cameraIdCaptured: capturedCameraId !== null,
          descriptorCaptured: capturedDescriptor !== null
        });
      }
    },
    onLeave(returnValue) {
      if (this.prop !== 0x01000203) return;
      const rc = returnValue.toUInt32();
      emit({ type: 'registration_return', slot: this.param - 32, rc: rc, patched: this.didPatchPayload, size: this.n });
      if (!this.didPatchPayload) return;
      if (rc === 0) {
        const completedSlot = this.param - 32;
        armed = false;
        emit({ type: 'install_success', slot: completedSlot, styleName: armedName, payloadWriteOK: true, control115Patched: false, dynamicCameraFamily: true });
      } else {
        emit({ type: 'install_error', reason: 'Patched 0x01000203 write failed', rc: rc, slot: this.param - 32 });
      }
    }
  });
  edsHooked = true;
  return true;
}

function scan() {
  let compiler = null;
  try { compiler = Process.getModuleByName('EdsCFParse.dll'); } catch (_) {}
  if (!compilerHooked) { try { hookCompilerInputs(); } catch (error) { emit({ type: 'hook_error', component: 'EdsCFParse', error: String(error) }); } }
  if (!edsHooked) { try { hookEdsdk(); } catch (error) { emit({ type: 'hook_error', component: 'EDSDK', error: String(error) }); } }
  if (compiler && compilerHooked && edsHooked && !readySent) {
    readySent = true;
    emit({ type: 'ready', cfpPath: compiler.path, cfpSize: compiler.size, dynamicCameraFamily: true });
  }
}

scan();
setInterval(scan, 250);

rpc.exports = {
  compile: function(path, cameraIdHex, descriptorHex) { return compilePf3(path, cameraIdHex, descriptorHex); },
  detectfamilysize: function(size) { return detectCarrierFamily(new Uint8Array(Number(size))); },
  testmodern83076: function(pf3Path, nativeHex, styleName, cameraIdHex, descriptorHex) {
    armedPf3Path = String(pf3Path || '');
    armedName = String(styleName || 'PICTURE STYLE').substring(0, 31);
    capturedCameraId = hexToBytes(cameraIdHex);
    capturedDescriptor = hexToBytes(descriptorHex);
    const nativeCarrier = hexToBytes(nativeHex);
    const family = detectCarrierFamily(nativeCarrier);
    if (nativeCarrier.length !== 83076) throw new Error('testmodern83076 requires an 83076-byte carrier');
    const built = buildCanonNativeCarrier(nativeCarrier, family);
    return [built.metadata, built.output.buffer];
  },
  testcarrierfamily: function(pf3Path, nativeHex, styleName, cameraIdHex, descriptorHex) {
    armedPf3Path = String(pf3Path || '');
    armedName = String(styleName || 'PICTURE STYLE').substring(0, 31);
    capturedCameraId = hexToBytes(cameraIdHex);
    capturedDescriptor = hexToBytes(descriptorHex);
    const nativeCarrier = hexToBytes(nativeHex);
    const built = compileForNativeCarrier(nativeCarrier);
    return [built.metadata, built.output.buffer];
  },
  armdynamic: function(slot, pf3Path, styleName) {
    const selectedSlot = parseInt(slot);
    if (selectedSlot < 0 || selectedSlot > 3) throw new Error('slot must be 0..3');
    const path = String(pf3Path || '');
    if (!path) throw new Error('PF3 path is required');
    armedSlot = selectedSlot;
    armedPf3Path = path;
    armedName = String(styleName || 'PICTURE STYLE').substring(0, 31);
    capturedCameraId = null;
    capturedDescriptor = null;
    armed = true;
    emit({ type: 'armed', slot: selectedSlot || null, slotPolicy: 'dynamic-user-def-1-to-3', styleName: armedName, payloadPolicy: 'live-canon-pf3-native-compiler' });
    return true;
  },
  disarm: function() {
    armed = false;
    armedSlot = 0;
    armedPf3Path = '';
    armedName = 'PICTURE STYLE';
    capturedCameraId = null;
    capturedDescriptor = null;
    return true;
  },
  status: function() {
    return { ready: readySent, armed: armed, slot: armedSlot, styleName: armedName, cameraIdCaptured: capturedCameraId !== null, descriptorCaptured: capturedDescriptor !== null };
  }
};
