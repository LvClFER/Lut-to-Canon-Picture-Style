'use strict';

// Canon-native PF3 compiler acceptance agent.
//
// The application never builds or replaces a camera-registration carrier.
// EOS Utility opens the selected PF3, EdsCFParse chooses the representation
// required by the connected camera, and EDSDK sends Canon's original buffer.
// The only mutation is inside EdsCFParse while it is compiling the exact PF3
// armed by Canon Style Studio: arbitrary 33^3 tables are fed through Canon's
// own grid conversion functions instead of being normalized to the base style.

let seq = 0;
let readySent = false;
let compilerHooked = false;
let compilerHookFailed = false;
let edsHooked = false;
let armed = false;
let armedSlot = 0;
let armedPf3Path = '';
let armedName = 'PICTURE STYLE';
let capturedCameraId = null;
let capturedDescriptor = null;
let validationSeq = 0;
let lastValidatedCompile = null;
let lastCompilerValidation = null;

const targetRefs = Object.create(null);
const activeCompilerCalls = Object.create(null);
const internalOverrideThreads = Object.create(null);

// Diagnostic labels only. Carrier size never selects a builder: the buffer is
// produced and sent unchanged by Canon's own EOS Utility/EdsCFParse/EDSDK path.
const KNOWN_CARRIER_OBSERVATIONS = [
  { id: 'observed-8164', sizes: [8164] },
  { id: 'observed-8168', sizes: [8168] },
  { id: 'observed-8528', sizes: [8528] },
  { id: 'observed-16720', sizes: [16720] },
  { id: 'observed-16744-16752', sizes: [16744, 16752] },
  { id: 'observed-78980', sizes: [78980] },
  { id: 'observed-83076', sizes: [83076] },
  { id: 'observed-431616', sizes: [431616] }
];

function emit(o, data) {
  o.seq = ++seq;
  o.ts = Date.now();
  send(o, data || null);
}

function ex(m, n) {
  try {
    return m.enumerateExports().find(e => e.type === 'function' && e.name === n) || null;
  } catch (_) {
    return null;
  }
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

function pointerKey(value) {
  return value.toString();
}

function normalizePath(value) {
  let text = String(value || '').trim().replace(/\//g, '\\');
  if (text.substring(0, 4) === '\\\\?\\') text = text.substring(4);
  return text.toLowerCase();
}

function readNativePath(value) {
  if (!value || value.isNull()) return '';
  try { return value.readUtf8String() || ''; } catch (_) {}
  try { return value.readAnsiString() || ''; } catch (_) {}
  return '';
}

function sameArmedPath(value) {
  return armed && normalizePath(value) === normalizePath(armedPf3Path);
}

function detectCarrierFamily(size) {
  for (const family of KNOWN_CARRIER_OBSERVATIONS) {
    if (family.sizes.indexOf(size) >= 0) return { id: family.id, known: true };
  }
  return { id: 'observed-new-' + size, known: false };
}

function compilerApi() {
  const module = Process.getModuleByName('EdsCFParse.dll');
  const initializeExport = ex(module, 'EdsCfpInitialize');
  const createExport = ex(module, 'EdsCfpCreateRef');
  const setExport = ex(module, 'EdsCfpSetPropertyData');
  const sizeExport = ex(module, 'EdsCfpGetPropertySize');
  const getExport = ex(module, 'EdsCfpGetPropertyData');
  const releaseExport = ex(module, 'EdsCfpRelease');
  if (!initializeExport || !createExport || !setExport || !sizeExport || !getExport || !releaseExport) {
    throw new Error('Required EdsCFParse exports not found');
  }
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
  lastCompilerValidation = null;
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
  if (rcCreate !== 0 || ref.isNull()) {
    return [{ ok: false, rcInitialize: rcInitialize, rcCreate: rcCreate }, new ArrayBuffer(0)];
  }
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
  const validation = lastCompilerValidation ? Object.assign({}, lastCompilerValidation) : null;
  return [{
    ok: rcCreate === 0 && rcId === 0 && rcDescriptor === 0 && rcSize === 0 && rcGet === 0,
    rcInitialize: rcInitialize, rcCreate: rcCreate, rcId: rcId, rcDesc: rcDescriptor,
    rcSize: rcSize, rcGet: rcGet, rcRelease: rcRelease,
    outputSize: outputSize, outputType: dataType.readU32(), acceptanceHook: validation
  }, data];
}

// Resolve internal compiler functions by semantic byte signatures. Fixed DLL
// size and fixed RVAs are intentionally not used: a Canon update may move the
// same implementation. Ambiguous or missing signatures fail closed.
function resolveCode(module, label, pattern, adjustment) {
  const hits = Memory.scanSync(module.base, module.size, pattern);
  if (hits.length !== 1) {
    throw new Error('Unsupported EdsCFParse semantic signature for ' + label + ': ' + hits.length + ' matches');
  }
  const address = hits[0].address.add(adjustment || 0);
  if (address.compare(module.base) < 0 || address.compare(module.base.add(module.size)) >= 0) {
    throw new Error('Resolved EdsCFParse address is outside the module for ' + label);
  }
  return address;
}

function resolveAcceptanceSymbols(module) {
  return {
    dense17Builder: resolveCode(module, '17-node grid builder',
      'c7 07 03 00 00 00 50 56 8b cb c7 47 04 11 00 00 00 c7 47 08 98 cc 01 00 c7 47 0c 02 00 00 00', -0xc2),
    dense10Builder: resolveCode(module, '10-node grid builder',
      '55 8b ec b8 10 58 00 00 e8 ?? ?? ?? ?? a1 ?? ?? ?? ?? 33 c5 89 45 fc 53 8b 5d 0c 56 57 8b f1', 0),
    readDenseGrid: resolveCode(module, 'dense PF3 grid reader',
      '55 8b ec 33 c0 83 7d 08 01 53 0f 95 c0 57 05 70 10 00 00 50 e8 ?? ?? ?? ?? 8b f8 85 ff 74 39', 0),
    denseGridToIntermediate: resolveCode(module, 'Canon generic grid converter',
      '55 8b ec a1 ?? ?? ?? ?? 85 c0 74 03 5d ff e0 5d c3 cc cc cc cc cc cc cc cc cc cc cc cc cc cc cc 55 8b ec a1 ?? ?? ?? ?? 85 c0 74 49 ff 75 48', 0),
    auxiliaryBuilder: resolveCode(module, 'auxiliary grid builder',
      '55 8b ec b8 14 50 00 00 e8 ?? ?? ?? ?? a1 ?? ?? ?? ?? 33 c5 89 45 fc 53 56 57 68 d4 5d 00 00 8b f1', 0),
    convertGrid33ForCamera: resolveCode(module, '33-grid camera converter',
      '55 8b ec b8 d0 4c 00 00 e8 ?? ?? ?? ?? a1 ?? ?? ?? ?? 33 c5 89 45 fc 53 56 57 8b f1 c7 85 30 b3 ff ff 00 00 00 00', 0),
    readCompactGrid: resolveCode(module, 'compact grid reader',
      '55 8b ec 33 c0 83 7d 08 01 0f 95 c0 8d 04 c5 22 10 00 00 50 e8 ?? ?? ?? ?? 85 c0 74 1a 6a 00 68 00 10 00 00', 0),
    setInternalProperty: resolveCode(module, 'internal property writer',
      '55 8b ec 56 ff 75 08 be 50 00 00 00 e8 ?? ?? ?? ?? 85 c0 74 16 ff 75 14 8b c8 ff 75 0c ff 75 10 e8 ?? ?? ?? ?? 84 c0 74 09', 0)
  };
}

function newValidation(refKey) {
  return {
    id: ++validationSeq,
    refKey: refKey,
    dense17: [], dense10: [], auxiliary: [], errors: [],
    outputSize: 0, startedAt: Date.now(), completed: false
  };
}

function currentValidation() {
  return activeCompilerCalls[String(Process.getCurrentThreadId())] || null;
}

function startCompilerCall(ref, operation, requestedSize) {
  const key = pointerKey(ref);
  const state = targetRefs[key];
  if (!state) return null;
  if (operation === 'size' || !state.validation || state.validation.completed) {
    state.validation = newValidation(key);
  }
  state.validation.operation = operation;
  if (requestedSize) state.validation.outputSize = requestedSize;
  activeCompilerCalls[String(Process.getCurrentThreadId())] = state.validation;
  return state.validation;
}

function endCompilerCall(context) {
  if (!context) return;
  const thread = String(Process.getCurrentThreadId());
  if (activeCompilerCalls[thread] === context) delete activeCompilerCalls[thread];
}

function summarizeValidation(context) {
  const dense17Indices = context.dense17.filter(item => item.applied).map(item => item.index);
  const dense10Indices = context.dense10.filter(item => item.applied).map(item => item.index);
  const dense17Seen = context.dense17.length > 0;
  const dense10Seen = context.dense10.length > 0;
  const stockCanonDirectPath = !dense17Seen && !dense10Seen;
  const selectedDenseValid = stockCanonDirectPath ? true : dense17Seen
    ? dense17Indices.indexOf(1) >= 0 && dense17Indices.indexOf(2) >= 0
    : dense10Seen && dense10Indices.indexOf(1) >= 0 && dense10Indices.indexOf(2) >= 0;
  const auxiliarySeen = context.auxiliary.length > 0;
  const auxiliaryApplied = !auxiliarySeen || context.auxiliary.some(item => item.applied);
  const errors = context.errors.concat(
    context.dense17.concat(context.dense10, context.auxiliary)
      .filter(item => item.error).map(item => item.error)
  );
  return {
    version: 3,
    mode: 'in-place-canon-compiler-acceptance',
    targetRef: context.refKey,
    outputSize: context.outputSize,
    compilerPath: stockCanonDirectPath ? 'stock-canon-direct' : (dense17Seen ? 'canon-17-node' : 'canon-10-node'),
    acceptanceMutationRequired: !stockCanonDirectPath,
    compilerGridPathSeen: dense17Seen || dense10Seen,
    dense17BuilderSeen: dense17Seen,
    dense17IndicesApplied: dense17Indices,
    dense10BuilderSeen: dense10Seen,
    dense10IndicesApplied: dense10Indices,
    auxiliaryBuilderSeen: auxiliarySeen,
    auxiliaryApplied: auxiliaryApplied,
    errors: errors,
    ok: selectedDenseValid && auxiliaryApplied && errors.length === 0
  };
}

function installAcceptanceHooks(module, symbols) {
  const ReadDenseGrid = new NativeFunction(
    symbols.readDenseGrid, 'uint32', ['pointer', 'uint32', 'pointer'], 'thiscall'
  );
  const DenseGridToIntermediate = new NativeFunction(
    symbols.denseGridToIntermediate, 'void', ['pointer', 'uint32', 'uint32', 'pointer']
  );
  const ConvertGrid33ForCamera = new NativeFunction(
    symbols.convertGrid33ForCamera, 'uint32', ['pointer'], 'thiscall'
  );
  const ReadCompactGrid = new NativeFunction(
    symbols.readCompactGrid, 'uint32', ['pointer', 'uint32', 'pointer'], 'thiscall'
  );
  const SetInternalProperty = new NativeFunction(
    symbols.setInternalProperty, 'uint32',
    ['pointer', 'uint32', 'uint32', 'pointer', 'uint32', 'uint32'], 'thiscall'
  );

  Interceptor.attach(symbols.dense17Builder, {
    onEnter(args) {
      this.validation = currentValidation();
      if (!this.validation) return;
      this.self = this.context.ecx;
      this.gridIndex = args[0].toUInt32();
      this.output = args[1];
    },
    onLeave(returnValue) {
      if (!this.validation) return;
      const item = { index: this.gridIndex, originalResult: returnValue.toUInt32(), applied: false };
      const thread = String(Process.getCurrentThreadId());
      if (!internalOverrideThreads[thread] && (this.gridIndex === 1 || this.gridIndex === 2)) {
        internalOverrideThreads[thread] = true;
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
          delete internalOverrideThreads[thread];
        }
      }
      this.validation.dense17.push(item);
    }
  });

  Interceptor.attach(symbols.dense10Builder, {
    onEnter(args) {
      this.validation = currentValidation();
      if (!this.validation) return;
      this.self = this.context.ecx;
      this.gridIndex = args[0].toUInt32();
      this.output = args[1];
    },
    onLeave(returnValue) {
      if (!this.validation) return;
      const item = { index: this.gridIndex, originalResult: returnValue.toUInt32(), applied: false };
      const thread = String(Process.getCurrentThreadId());
      if (this.validation.dense17.length === 0 && !internalOverrideThreads[thread] &&
          (this.gridIndex === 1 || this.gridIndex === 2)) {
        internalOverrideThreads[thread] = true;
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
          delete internalOverrideThreads[thread];
        }
      }
      this.validation.dense10.push(item);
    }
  });

  Interceptor.attach(symbols.auxiliaryBuilder, {
    onEnter() {
      this.validation = currentValidation();
      if (!this.validation) return;
      this.self = this.context.ecx;
      this.compact = Memory.alloc(0x1000);
      this.compact.writeByteArray(new Uint8Array(0x1000));
      this.item = { converted: false, applied: false };
      try {
        this.item.convertResult = ConvertGrid33ForCamera(this.self);
        this.item.readCompactGrid = ReadCompactGrid(this.self, 1, this.compact);
        this.item.converted = this.item.convertResult !== 0 && this.item.readCompactGrid !== 0;
      } catch (error) {
        this.item.error = String(error);
      }
      this.validation.auxiliary.push(this.item);
    },
    onLeave() {
      if (!this.validation || !this.item || !this.item.converted || this.item.error) return;
      try {
        this.item.setResult = SetInternalProperty(this.self, 0x1f02, 0x1000, this.compact, 0, 1);
        this.item.applied = this.item.setResult === 0;
      } catch (error) {
        this.item.error = String(error);
      }
    }
  });
}

function hookCompiler() {
  let module;
  try { module = Process.getModuleByName('EdsCFParse.dll'); } catch (_) { return false; }
  const createExport = ex(module, 'EdsCfpCreateRef');
  const setExport = ex(module, 'EdsCfpSetPropertyData');
  const sizeExport = ex(module, 'EdsCfpGetPropertySize');
  const getExport = ex(module, 'EdsCfpGetPropertyData');
  const releaseExport = ex(module, 'EdsCfpRelease');
  if (!createExport || !setExport || !sizeExport || !getExport || !releaseExport) return false;

  const symbols = resolveAcceptanceSymbols(module);
  installAcceptanceHooks(module, symbols);

  Interceptor.attach(createExport.address, {
    onEnter(args) {
      this.path = readNativePath(args[0]);
      this.outRef = args[3];
      this.isTarget = sameArmedPath(this.path);
    },
    onLeave(returnValue) {
      if (!this.isTarget || returnValue.toUInt32() !== 0 || !this.outRef || this.outRef.isNull()) return;
      try {
        const ref = this.outRef.readPointer();
        if (ref.isNull()) throw new Error('EdsCfpCreateRef returned a null reference');
        const key = pointerKey(ref);
        targetRefs[key] = { refKey: key, path: this.path, validation: null };
        lastValidatedCompile = null;
        emit({ type: 'target_pf3_opened', path: this.path, ref: key });
      } catch (error) {
        emit({ type: 'compiler_target_error', reason: String(error) });
      }
    }
  });

  Interceptor.attach(setExport.address, {
    onEnter(args) {
      const state = targetRefs[pointerKey(args[0])];
      if (!state) return;
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
    }
  });

  Interceptor.attach(sizeExport.address, {
    onEnter(args) {
      this.ref = args[0];
      this.property = args[1].toUInt32();
      this.sizeOut = args[4];
      this.validation = this.property === 0x01000203 ? startCompilerCall(this.ref, 'size', 0) : null;
    },
    onLeave(returnValue) {
      if (!this.validation) return;
      try {
        if (returnValue.toUInt32() === 0 && this.sizeOut && !this.sizeOut.isNull()) {
          this.validation.outputSize = this.sizeOut.readU32();
        }
      } catch (error) {
        this.validation.errors.push(String(error));
      }
      endCompilerCall(this.validation);
    }
  });

  Interceptor.attach(getExport.address, {
    onEnter(args) {
      this.ref = args[0];
      this.property = args[1].toUInt32();
      this.requestedSize = args[3].toUInt32();
      this.validation = this.property === 0x01000203
        ? startCompilerCall(this.ref, 'data', this.requestedSize) : null;
      if (this.validation) emit({ type: 'target_pf3_compile_started', size: this.requestedSize });
    },
    onLeave(returnValue) {
      if (!this.validation) return;
      const originalRc = returnValue.toUInt32();
      const summary = summarizeValidation(this.validation);
      summary.originalRc = originalRc;
      lastCompilerValidation = summary;
      this.validation.completed = true;
      endCompilerCall(this.validation);
      if (originalRc === 0 && summary.ok) {
        lastValidatedCompile = summary;
        emit({ type: 'compiler_validation_pass', validation: summary });
      } else {
        lastValidatedCompile = null;
        summary.ok = false;
        if (originalRc === 0) returnValue.replace(1);
        emit({
          type: 'compiler_validation_failed',
          reason: originalRc === 0
            ? 'Canon-native PF3 acceptance did not complete every required table conversion'
            : 'Canon PF3 compiler returned error ' + originalRc,
          validation: summary
        });
      }
    }
  });

  Interceptor.attach(releaseExport.address, {
    onEnter(args) { this.key = pointerKey(args[0]); },
    onLeave() { if (targetRefs[this.key]) delete targetRefs[this.key]; }
  });

  compilerHooked = true;
  compilerHookFailed = false;
  emit({
    type: 'compiler_hooks_resolved',
    resolver: 'semantic-signatures-v1',
    moduleSize: module.size,
    addresses: Object.fromEntries(Object.entries(symbols).map(([name, address]) => [name, address.sub(module.base).toString()]))
  });
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
      this.isTargetRegistration = false;
      this.compilerValidated = false;
      const observedSlot = this.param - 32;
      const isUserDefSlot = observedSlot >= 1 && observedSlot <= 3;

      // 0x00000115 is binary state/control data. Observe only; do not modify.
      if (this.prop === 0x00000115 && armed && isUserDefSlot) {
        emit({ type: 'control115_seen', slot: observedSlot, size: this.n, untouched: true });
      }
      if (!armed || this.prop !== 0x01000203 || !isUserDefSlot) return;
      this.isTargetRegistration = true;
      this.compilerValidated = !!lastValidatedCompile && lastValidatedCompile.outputSize === this.n;
      emit({
        type: 'registration_seen', slot: observedSlot, inParam: this.param, size: this.n,
        armed: true, compilerValidated: this.compilerValidated,
        argumentsModified: false, payloadReplaced: false
      });
      if (this.n <= 0 || this.n > 1048576 || args[4].isNull()) {
        emit({ type: 'install_error', reason: 'Canon registration buffer is invalid', size: this.n, slot: observedSlot });
        return;
      }
      try {
        const nativeCarrier = readBytes(args[4], this.n);
        const family = detectCarrierFamily(this.n);
        emit({
          type: 'carrier_family_detected', familyId: family.id,
          familyStatus: family.known ? 'known-observation' : 'new-observation',
          compilerRoute: 'original-eos-utility-native-compiler', size: this.n,
          modelSpecificBuilder: false
        });
        emit({
          type: 'native_payload_observed', slot: observedSlot, inParam: this.param,
          size: this.n, readOnly: true, argumentsModified: false, payloadReplaced: false
        }, nativeCarrier.buffer);
        if (!this.compilerValidated) {
          emit({
            type: 'install_error',
            reason: 'EOS Utility reached camera transport without a matching validated target-PF3 compilation',
            size: this.n, slot: observedSlot
          });
        }
      } catch (error) {
        emit({ type: 'install_error', reason: 'Could not validate Canon original registration buffer: ' + String(error), size: this.n, slot: observedSlot });
      }
    },
    onLeave(returnValue) {
      if (!this.isTargetRegistration) return;
      const rc = returnValue.toUInt32();
      const slot = this.param - 32;
      emit({
        type: 'registration_return', slot: slot, rc: rc, size: this.n,
        patched: false, argumentsModified: false, payloadReplaced: false,
        compilerValidated: this.compilerValidated
      });
      if (!this.compilerValidated) return;
      if (rc === 0) {
        armed = false;
        emit({
          type: 'install_success', slot: slot, styleName: armedName,
          payloadWriteOK: true, control115Patched: false,
          payloadReplaced: false, originalCanonTransaction: true
        });
      } else {
        emit({ type: 'install_error', reason: 'Canon original registration write failed', rc: rc, slot: slot });
      }
    }
  });
  edsHooked = true;
  return true;
}

function clearTargetState() {
  for (const key of Object.keys(targetRefs)) delete targetRefs[key];
  for (const key of Object.keys(activeCompilerCalls)) delete activeCompilerCalls[key];
  for (const key of Object.keys(internalOverrideThreads)) delete internalOverrideThreads[key];
  capturedCameraId = null;
  capturedDescriptor = null;
  lastValidatedCompile = null;
  lastCompilerValidation = null;
}

function armDynamic(slot, pf3Path, styleName) {
  const selectedSlot = parseInt(slot);
  if (selectedSlot < 0 || selectedSlot > 3) throw new Error('slot must be 0..3');
  const path = String(pf3Path || '');
  if (!path) throw new Error('PF3 path is required');
  if (!compilerHooked || !edsHooked) throw new Error('Canon compiler/transport hooks are not ready');
  clearTargetState();
  armedSlot = selectedSlot;
  armedPf3Path = path;
  armedName = String(styleName || 'PICTURE STYLE').substring(0, 31);
  armed = true;
  emit({
    type: 'armed', slot: selectedSlot || null,
    slotPolicy: 'dynamic-user-def-1-to-3', styleName: armedName,
    compilerPolicy: 'patch-only-the-selected-pf3-inside-edscfparse',
    transportPolicy: 'original-canon-buffer-observation-only'
  });
  return true;
}

function armCompilerForOfflineTest(pf3Path, styleName) {
  const path = String(pf3Path || '');
  if (!path) throw new Error('PF3 path is required');
  if (!compilerHooked) throw new Error('Canon compiler hooks are not ready');
  clearTargetState();
  armedSlot = 0;
  armedPf3Path = path;
  armedName = String(styleName || 'PICTURE STYLE').substring(0, 31);
  armed = true;
}

function scan() {
  let compiler = null;
  try { compiler = Process.getModuleByName('EdsCFParse.dll'); } catch (_) {}
  if (!compilerHooked && !compilerHookFailed) {
    try { hookCompiler(); }
    catch (error) {
      compilerHookFailed = true;
      emit({ type: 'hook_error', component: 'EdsCFParse', error: String(error) });
    }
  }
  if (!edsHooked) {
    try { hookEdsdk(); }
    catch (error) { emit({ type: 'hook_error', component: 'EDSDK', error: String(error) }); }
  }
  if (compiler && compilerHooked && edsHooked && !readySent) {
    readySent = true;
    emit({
      type: 'ready', cfpPath: compiler.path, cfpSize: compiler.size,
      compilerRoute: 'in-place-canon-native-pf3-acceptance',
      transportMutation: false, modelSpecificBuilder: false
    });
  }
}

scan();
setInterval(scan, 250);

rpc.exports = {
  compile: function(path, cameraIdHex, descriptorHex) {
    return compilePf3(path, cameraIdHex, descriptorHex);
  },
  detectfamilysize: function(size) {
    return detectCarrierFamily(Number(size));
  },
  testnativecompile: function(pf3Path, styleName, cameraIdHex, descriptorHex) {
    armCompilerForOfflineTest(pf3Path, styleName);
    return compilePf3(pf3Path, cameraIdHex, descriptorHex);
  },
  // Backwards-compatible offline research entry points. They exercise the
  // in-place Canon compiler path; nativeHex is used only for a size assertion.
  testcarrierfamily: function(pf3Path, nativeHex, styleName, cameraIdHex, descriptorHex) {
    const nativeCarrier = hexToBytes(nativeHex);
    armCompilerForOfflineTest(pf3Path, styleName);
    const compiled = compilePf3(pf3Path, cameraIdHex, descriptorHex);
    compiled[0].observedCarrierSize = nativeCarrier.length;
    compiled[0].carrierSizeMatches = compiled[1].byteLength === nativeCarrier.length;
    return compiled;
  },
  testmodern83076: function(pf3Path, nativeHex, styleName, cameraIdHex, descriptorHex) {
    const nativeCarrier = hexToBytes(nativeHex);
    if (nativeCarrier.length !== 83076) throw new Error('testmodern83076 requires an 83076-byte carrier');
    armCompilerForOfflineTest(pf3Path, styleName);
    return compilePf3(pf3Path, cameraIdHex, descriptorHex);
  },
  armdynamic: function(slot, pf3Path, styleName) {
    return armDynamic(slot, pf3Path, styleName);
  },
  disarm: function() {
    armed = false;
    armedSlot = 0;
    armedPf3Path = '';
    armedName = 'PICTURE STYLE';
    clearTargetState();
    return true;
  },
  status: function() {
    return {
      ready: readySent, armed: armed, slot: armedSlot, styleName: armedName,
      targetRefs: Object.keys(targetRefs).length,
      cameraIdCaptured: capturedCameraId !== null,
      descriptorCaptured: capturedDescriptor !== null,
      compilerValidated: lastValidatedCompile !== null,
      transportMutation: false
    };
  }
};
