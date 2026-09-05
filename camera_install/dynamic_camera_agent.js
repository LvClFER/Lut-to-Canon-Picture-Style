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
let armedLegacyBlock1 = null;
let capturedCameraId = null;
let capturedDescriptor = null;

// Canon's 83076-byte mirrorless carrier stores a 17^3 main transform in
// 0x1F00/0x1022 and a 1024-word auxiliary transform in 0x1F02.  These matrices
// were recovered from controlled Canon compiler vectors; the resulting primary
// regions were then physically exercised on an EOS R8 with an Aerochrome PF3.
const MODERN_1F00_ENCODER = [
  [0.500072257608, -0.167807965474, 0.299122622189],
  [-0.417721266293, -0.331721249182, 0.587079570317],
  [-0.076971231656, 0.501513430464, 0.111715634378],
  [-3.452540877943, -2.556957731189, 2.653572155506]
];
const MODERN_1022_ENCODER = [
  [0.500061911406, -0.168831708880, 0.299370135171],
  [-0.418839319307, -0.331206989894, 0.587406536823],
  [-0.081193543148, 0.500046922678, 0.113863797691],
  [-0.013230205577, -0.003799443653, 0.112558518217]
];
const MODERN_1F02_ENCODER = [
  [0.249944106404, -0.084132397621, 0.149734280432],
  [-0.209141021672, -0.165721441020, 0.293721499133],
  [-0.039232782149, 0.250159533133, 0.056424491597],
  [-1.101104246556, -0.694334966624, 0.737661553757]
];

const CAMERA_FAMILY_REGISTRY = [
  { id: 'legacy-single-compact-8164', sizes: [8164], installEnabled: false, status: 'recognized-research-required' },
  { id: 'legacy-single-compact-8168', sizes: [8168], installEnabled: false, status: 'recognized-research-required' },
  { id: 'legacy-compact-8528', sizes: [8528], installEnabled: false, status: 'recognized-research-required' },
  { id: 'legacy-transition-16720', sizes: [16720], installEnabled: false, status: 'recognized-research-required' },
  { id: 'legacy-dual-8192', sizes: [16744, 16752], installEnabled: true, status: 'physically-validated-eos-1300d-rp', builder: 'legacy-dual-8192' },
  { id: 'modern-17cube-paired', sizes: [78980], installEnabled: true, status: 'structurally-mapped-physical-validation-required', builder: 'modern-17cube' },
  { id: 'modern-17cube-paired-aux', sizes: [83076], installEnabled: true, status: 'physically-exercised-eos-r8-aerochrome', builder: 'modern-17cube-aux' },
  { id: 'modern-full33-paired', sizes: [431616], installEnabled: false, status: 'recognized-encoder-research-required', builder: 'modern-full33', regions: ['0x1F04', '0x1F03'] }
];

// Legacy carriers place both 32-byte names directly at 8 and 44. Modern
// mirrorless carriers keep a two-byte field header at 44/45, so their second
// name begins at 46. Overwriting that header makes the camera discard the
// first two visible characters of the replacement name.
const LEGACY_NAME_OFFSETS = [8, 44];
const MODERN_NAME_OFFSETS = [8, 46];

function detectCarrierFamily(bytes) {
  const size = bytes.length;
  for (const family of CAMERA_FAMILY_REGISTRY) {
    if (family.sizes.indexOf(size) >= 0) return family;
  }
  return { id: 'unknown-' + size, sizes: [size], installEnabled: false, status: 'unknown-capture-required' };
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

function sliceBytes(bytes, start, end) {
  const output = new Uint8Array(end - start);
  output.set(bytes.subarray(start, end));
  return output;
}

function xorCanon(bytes, seed) {
  const module = Process.getModuleByName('EdsCFParse.dll');
  if (module.size !== 901120) throw new Error('Unsupported EdsCFParse build for the modern carrier encoder: ' + module.size);
  const transform = new NativeFunction(module.base.add(0x2db0), 'void', ['pointer', 'uint32', 'uint32']);
  const memory = copyToMemory(bytes);
  transform(memory, bytes.length, Number(seed) >>> 0);
  return new Uint8Array(memory.readByteArray(bytes.length));
}

function readU16(bytes, offset) {
  return bytes[offset] | (bytes[offset + 1] << 8);
}

function writeU32(bytes, offset, value) {
  const word = Number(value) >>> 0;
  bytes[offset] = word & 255;
  bytes[offset + 1] = (word >>> 8) & 255;
  bytes[offset + 2] = (word >>> 16) & 255;
  bytes[offset + 3] = (word >>> 24) & 255;
}

function roundEven(value) {
  const floor = Math.floor(value);
  const fraction = value - floor;
  if (fraction < 0.5) return floor;
  if (fraction > 0.5) return floor + 1;
  return (floor % 2 === 0) ? floor : floor + 1;
}

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

function unpackCanonWord(bytes, offset) {
  const word = (bytes[offset] | (bytes[offset + 1] << 8) |
    (bytes[offset + 2] << 16) | (bytes[offset + 3] << 24)) >>> 0;
  let c0 = word & 0x3ff;
  let c1 = (word >>> 10) & 0x3ff;
  if (c0 >= 512) c0 -= 1024;
  if (c1 >= 512) c1 -= 1024;
  return [c0, c1, (word >>> 20) & 0x3ff];
}

function packEncodedRgb(rgb, encoder) {
  const encoded = [];
  for (let channel = 0; channel < 3; channel++) {
    encoded[channel] = roundEven(
      rgb[0] * encoder[0][channel] + rgb[1] * encoder[1][channel] +
      rgb[2] * encoder[2][channel] + encoder[3][channel]
    );
  }
  encoded[0] = clamp(encoded[0], -512, 511) & 0x3ff;
  encoded[1] = clamp(encoded[1], -512, 511) & 0x3ff;
  encoded[2] = clamp(encoded[2], 0, 1023) & 0x3ff;
  return (encoded[0] | (encoded[1] << 10) | (encoded[2] << 20)) >>> 0;
}

function inverse3(matrix) {
  const a = matrix[0][0], b = matrix[0][1], c = matrix[0][2];
  const d = matrix[1][0], e = matrix[1][1], f = matrix[1][2];
  const g = matrix[2][0], h = matrix[2][1], i = matrix[2][2];
  const det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
  if (Math.abs(det) < 1e-12) throw new Error('Modern carrier encoder matrix is singular');
  return [
    [(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
    [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
    [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]
  ];
}

function validatePf3Table(table) {
  if (table.length !== 215628 || readU16(table, 0) !== 12 ||
      readU16(table, 2) !== 3 || readU16(table, 4) !== 33) {
    throw new Error('PF3 does not contain a Canon 12-bit 33x33x33 table');
  }
}

function tableRgb(table, r, g, b) {
  const offset = 6 + (((r * 33 + g) * 33 + b) * 3 * 2);
  return [readU16(table, offset), readU16(table, offset + 2), readU16(table, offset + 4)];
}

function encodeMainTable(table, encoder) {
  validatePf3Table(table);
  const output = new Uint8Array(4913 * 4);
  let offset = 0;
  for (let b = 0; b <= 32; b += 2) {
    for (let g = 0; g <= 32; g += 2) {
      for (let r = 0; r <= 32; r += 2) {
        const source = tableRgb(table, r, g, b);
        const rgb = source.map(value => value * (1023.0 / 4095.0));
        writeU32(output, offset, packEncodedRgb(rgb, encoder));
        offset += 4;
      }
    }
  }
  return output;
}

function recoverAuxiliaryGrid(nativeDecodedAux) {
  if (nativeDecodedAux.length !== 4096) throw new Error('Native 0x1F02 region has an unexpected size');
  const matrix = MODERN_1F00_ENCODER.slice(0, 3);
  const inverse = inverse3(matrix);
  const bias = MODERN_1F00_ENCODER[3];
  const grid = [];
  for (let node = 0; node < 1024; node++) {
    const value = unpackCanonWord(nativeDecodedAux, node * 4);
    const centered = [value[0] * 2 - bias[0], value[1] * 2 - bias[1], value[2] * 2 - bias[2]];
    const rgb = [];
    for (let channel = 0; channel < 3; channel++) {
      rgb[channel] = centered[0] * inverse[0][channel] +
        centered[1] * inverse[1][channel] + centered[2] * inverse[2][channel];
    }
    grid.push(rgb.map(value => clamp(roundEven(value * (8.0 / 1023.0)), 0, 8)));
  }
  return grid;
}

function encodeAuxiliaryTable(table, grid) {
  validatePf3Table(table);
  if (!grid || grid.length !== 1024) throw new Error('Modern auxiliary grid is incomplete');
  const output = new Uint8Array(4096);
  for (let node = 0; node < 1024; node++) {
    const index = grid[node];
    const source = tableRgb(table, index[0] * 4, index[1] * 4, index[2] * 4);
    const rgb = source.map(value => value * (1023.0 / 4095.0));
    writeU32(output, node * 4, packEncodedRgb(rgb, MODERN_1F02_ENCODER));
  }
  return output;
}

function getPropertyBytes(api, ref, property) {
  const dataType = Memory.alloc(4); dataType.writeU32(0);
  const dataSize = Memory.alloc(4); dataSize.writeU32(0);
  const rcSize = api.GetSize(ref, property, 0, dataType, dataSize);
  const size = dataSize.readU32();
  if (rcSize !== 0 || size <= 0 || size > 1048576) throw new Error('Canon PF3 property size failed: 0x' + property.toString(16));
  const memory = Memory.alloc(size);
  memory.writeByteArray(new Uint8Array(size));
  const rcGet = api.Get(ref, property, 0, size, memory);
  if (rcGet !== 0) throw new Error('Canon PF3 property read failed: 0x' + property.toString(16));
  return new Uint8Array(memory.readByteArray(size));
}

function buildModern17Carrier(nativeCarrier, family) {
  const includeAuxiliary = family.builder === 'modern-17cube-aux';
  const expectedSize = includeAuxiliary ? 83076 : 78980;
  if (nativeCarrier.length !== expectedSize) throw new Error('Modern encoder carrier size does not match its registered family');
  const api = compilerApi();
  const rcInitialize = api.Initialize();
  // EOS Utility normally initialized the parser before the hook runs. Canon
  // returns 2 when Initialize is called again; both states are usable.
  if (rcInitialize !== 0 && rcInitialize !== 2) throw new Error('Canon PF3 parser initialization failed: rc=' + rcInitialize);
  const outRef = Memory.alloc(Process.pointerSize); outRef.writePointer(ptr(0));
  const rcCreate = api.Create(Memory.allocUtf8String(armedPf3Path), 2, 0, outRef);
  const ref = outRef.readPointer();
  if (rcCreate !== 0 || ref.isNull()) throw new Error('Canon could not open the PF3 for modern table encoding: rc=' + rcCreate);
  compilerBusy = true;
  try {
    const table70 = getPropertyBytes(api, ref, 0x40001070);
    const table71 = getPropertyBytes(api, ref, 0x40001071);
    const decoded1f00 = encodeMainTable(table70, MODERN_1F00_ENCODER);
    const decoded1022 = encodeMainTable(table71, MODERN_1022_ENCODER);
    const output = new Uint8Array(nativeCarrier);
    output.set(xorCanon(decoded1f00, 0xB8ED), 372);
    output.set(xorCanon(decoded1022, 0xB8ED), 39676);
    const patchedRegions = ['0x1F00', '0x1022'];
    if (includeAuxiliary) {
      const nativeAux = xorCanon(sliceBytes(nativeCarrier, 78980, 83076), 0xB8ED);
      const grid = recoverAuxiliaryGrid(nativeAux);
      const decoded1f02 = encodeAuxiliaryTable(table70, grid);
      output.set(xorCanon(decoded1f02, 0xB8ED), 78980);
      patchedRegions.push('0x1F02');
    }
    patchPayloadName(output, MODERN_NAME_OFFSETS);
    const validation = validateNativeRoundTrip(nativeCarrier, output);
    return { output: output, metadata: {
      strategy: includeAuxiliary ? 'modern-83076-pf3-table-encoder-v1' : 'modern-78980-pf3-table-encoder-v1',
      familyId: family.id, familyStatus: family.status, outputSize: output.length,
      tableProperties: ['0x40001070', '0x40001071'],
      patchedRegions: patchedRegions,
      preservedRegions: ['0x1F01', '0x102A'],
      physicallyExercisedLook: includeAuxiliary ? 'Aerochrome on EOS R8' : null,
      sentinelOffset: validation.sentinelOffset, meaningfulStart: validation.meaningfulStart,
      totalDifferences: validation.totalDifferences,
      meaningfulDifferences: validation.meaningfulDifferences,
      cameraIdHex: bytesToHex(capturedCameraId), descriptorSize: capturedDescriptor.length
    }};
  } finally {
    try { api.Release(ref); } catch (_) {}
    compilerBusy = false;
  }
}

function fixedAscii32(value) {
  const output = new Uint8Array(32);
  const text = String(value || 'PICTURE STYLE').substring(0, 31);
  for (let i = 0; i < text.length; i++) {
    const code = text.charCodeAt(i);
    output[i] = (code >= 32 && code <= 126) ? code : 95;
  }
  return output;
}

function patchPayloadName(payload, offsets) {
  const name = fixedAscii32(armedName);
  for (const offset of (offsets || LEGACY_NAME_OFFSETS)) {
    if (offset + 32 > payload.length) throw new Error('Canon carrier is too small for its duplicated style name');
    for (let i = 0; i < 32; i++) payload[offset + i] = name[i];
  }
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
  if (nativeMagic < 0 || outputMagic !== nativeMagic) throw new Error('Canon output carrier sentinel does not match the genuine transaction');
  const meaningfulStart = nativeMagic + 276;
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
  return { sentinelOffset: nativeMagic, meaningfulStart: meaningfulStart, totalDifferences: totalDifferences, meaningfulDifferences: meaningfulDifferences };
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
  const pathMemory = Memory.allocUtf8String(String(path));
  const outRef = Memory.alloc(Process.pointerSize);
  outRef.writePointer(ptr(0));
  const rcCreate = api.Create(pathMemory, 2, 0, outRef);
  const ref = outRef.readPointer();
  if (rcCreate !== 0 || ref.isNull()) return [{ ok: false, rcCreate: rcCreate }, new ArrayBuffer(0)];
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
      rcCreate: rcCreate, rcId: rcId, rcDesc: rcDescriptor, rcSize: rcSize,
      rcGet: rcGet, rcRelease: rcRelease, outputSize: outputSize, outputType: dataType.readU32()
    }, data];
  } finally {
    compilerBusy = false;
  }
}

function compileForNativeCarrier(nativeCarrier) {
  if (!capturedCameraId || capturedCameraId.length !== 4) throw new Error('Live Canon camera ID was not captured');
  if (!capturedDescriptor || capturedDescriptor.length === 0) throw new Error('Live Canon camera descriptor was not captured');
  if (!armedPf3Path) throw new Error('No PF3 is armed');
  const family = detectCarrierFamily(nativeCarrier);
  if (!family.installEnabled) {
    throw new Error('Canon carrier family ' + family.id + ' is recognized but not yet enabled: ' + family.status);
  }
  if (family.builder === 'modern-17cube' || family.builder === 'modern-17cube-aux') {
    return buildModern17Carrier(nativeCarrier, family);
  }
  const nativeSentinel = magicOffset(nativeCarrier);
  const legacyDataStart = nativeSentinel + 276;
  if (family.builder === 'legacy-dual-8192' && armedLegacyBlock1 &&
      armedLegacyBlock1.length === 8192 && nativeSentinel >= 0 &&
      nativeCarrier.length - legacyDataStart === 16384) {
    const output = new Uint8Array(nativeCarrier);
    output.set(armedLegacyBlock1, legacyDataStart);
    patchPayloadName(output, LEGACY_NAME_OFFSETS);
    const validation = validateNativeRoundTrip(nativeCarrier, output);
    return { output: output, metadata: {
      strategy: 'legacy-dual-8192-block-carrier', familyId: family.id,
      familyStatus: family.status, outputSize: output.length,
      sentinelOffset: validation.sentinelOffset, meaningfulStart: validation.meaningfulStart,
      totalDifferences: validation.totalDifferences,
      meaningfulDifferences: validation.meaningfulDifferences,
      cameraIdHex: bytesToHex(capturedCameraId), descriptorSize: capturedDescriptor.length,
      oracleBlockSize: armedLegacyBlock1.length
    }};
  }
  throw new Error('Canon carrier family ' + family.id + ' failed its structural validation');
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
          installEnabled: family.installEnabled, builder: family.builder || null, size: this.n
        });
        emit({ type: 'native_payload_observed', slot: observedSlot, inParam: this.param, size: this.n, readOnly: true, argumentsModified: false }, nativeCarrier.buffer);
        if (!family.installEnabled) {
          emit({
            type: 'native_payload_captured', slot: observedSlot, inParam: this.param, size: this.n,
            familyId: family.id, familyStatus: family.status, readOnly: true, argumentsModified: false
          }, nativeCarrier.buffer);
          emit({
            type: 'install_error', reason: 'Carrier family ' + family.id + ' was captured safely but is not enabled: ' + family.status,
            size: this.n, slot: observedSlot, cameraIdCaptured: capturedCameraId !== null,
            descriptorCaptured: capturedDescriptor !== null
          });
          return;
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
    if (family.builder !== 'modern-17cube-aux') throw new Error('testmodern83076 requires the registered 83076-byte family');
    const built = buildModern17Carrier(nativeCarrier, family);
    return [built.metadata, built.output.buffer];
  },
  testcarrierfamily: function(pf3Path, nativeHex, styleName, cameraIdHex, descriptorHex) {
    armedPf3Path = String(pf3Path || '');
    armedName = String(styleName || 'PICTURE STYLE').substring(0, 31);
    capturedCameraId = hexToBytes(cameraIdHex);
    capturedDescriptor = hexToBytes(descriptorHex);
    const nativeCarrier = hexToBytes(nativeHex);
    const family = detectCarrierFamily(nativeCarrier);
    if (!family.installEnabled) throw new Error('family not enabled: ' + family.id);
    const built = compileForNativeCarrier(nativeCarrier);
    return [built.metadata, built.output.buffer];
  },
  armdynamic: function(slot, pf3Path, styleName, legacyBlock1Hex) {
    const selectedSlot = parseInt(slot);
    if (selectedSlot < 0 || selectedSlot > 3) throw new Error('slot must be 0..3');
    const path = String(pf3Path || '');
    if (!path) throw new Error('PF3 path is required');
    armedSlot = selectedSlot;
    armedPf3Path = path;
    armedName = String(styleName || 'PICTURE STYLE').substring(0, 31);
    armedLegacyBlock1 = hexToBytes(legacyBlock1Hex);
    if (armedLegacyBlock1.length !== 8192) throw new Error('validated legacy Block1 must be exactly 8192 bytes');
    capturedCameraId = null;
    capturedDescriptor = null;
    armed = true;
    emit({ type: 'armed', slot: selectedSlot || null, slotPolicy: 'dynamic-user-def-1-to-3', styleName: armedName, payloadPolicy: 'validated-oracle-block-plus-live-camera-family' });
    return true;
  },
  disarm: function() {
    armed = false;
    armedSlot = 0;
    armedPf3Path = '';
    armedName = 'PICTURE STYLE';
    armedLegacyBlock1 = null;
    capturedCameraId = null;
    capturedDescriptor = null;
    return true;
  },
  status: function() {
    return { ready: readySent, armed: armed, slot: armedSlot, styleName: armedName, oracleBlockReady: armedLegacyBlock1 !== null, cameraIdCaptured: capturedCameraId !== null, descriptorCaptured: capturedDescriptor !== null };
  }
};
