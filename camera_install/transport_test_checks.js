// Append after dynamic_camera_agent.js in the isolated offline test process.
const testSet = new NativeFunction(testSinkCode, 'uint32',
  ['pointer', 'uint32', 'int32', 'uint32', 'pointer'], 'stdcall');

function testRequire(value, message) {
  if (!value) throw new Error(message);
}

function testFastHex(value) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  const digits = Array.from({length: 256}, (_, index) => index.toString(16).padStart(2, '0'));
  const result = new Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) result[i] = digits[bytes[i]];
  return result.join('');
}

rpc.exports.createnamedfixture = function(sourcePath, outputPath, title, properties) {
  const api = compilerApi();
  api.Initialize();
  const sourceOut = Memory.alloc(Process.pointerSize);
  const outputOut = Memory.alloc(Process.pointerSize);
  sourceOut.writePointer(ptr(0)); outputOut.writePointer(ptr(0));
  testRequire(api.Create(Memory.allocUtf8String(sourcePath), 2, 0, sourceOut) === 0,
    'Could not read name fixture');
  const sourceRef = sourceOut.readPointer();
  let outputRef = ptr(0);
  try {
    testRequire(api.Create(Memory.allocUtf8String(outputPath), 1, 1, outputOut) === 0,
      'Could not create name fixture');
    outputRef = outputOut.readPointer();
    for (const item of properties) {
      const data = Memory.alloc(item[1]);
      testRequire(api.Get(sourceRef, item[0], 0, item[1], data) === 0, 'Fixture property read failed');
      if (item[0] === 0x40001002) {
        const bytes = new Uint8Array(32);
        for (let i = 0; i < Math.min(31, title.length); i++) bytes[i] = title.charCodeAt(i);
        data.writeByteArray(bytes);
      }
      // PF3 property 0x115 is copied in its file context, not camera control state.
      testRequire(api.Set(outputRef, item[0], 0, item[1], data) === 0, 'Fixture property write failed');
    }
    const reflect = ex(api.module, 'EdsCfpReflectProperty');
    testRequire(!!reflect, 'Canon serializer unavailable');
    testRequire(new NativeFunction(reflect.address, 'uint32', ['pointer'])(outputRef) === 0,
      'Canon fixture serialization failed');
    return {ok: true, title: title};
  } finally {
    if (!outputRef.isNull()) api.Release(outputRef);
    api.Release(sourceRef);
  }
};

rpc.exports.testtransport = function(pf3Path, cameraIdHex, descriptorHex, slot) {
  armCompilerForOfflineTest(pf3Path, 'TRANSPORT TEST');
  send({type: 'test_stage', stage: 'compile'});
  const compiled = compilePf3(pf3Path, cameraIdHex, descriptorHex);
  testRequire(compiled[0].ok && compiled[0].acceptanceHook.ok, 'Compiler validation failed');
  const bytes = new Uint8Array(compiled[1]);
  const buffer = copyToMemory(bytes);
  const camera = ptr(0x12345678); // Opaque value read only by the sink.
  const param = 32 + Number(slot);
  const before = testSinkState.readU32();
  buffer.writeU8(bytes[0] ^ 1);
  send({type: 'test_stage', stage: 'modified buffer'});
  testRequire(testSet(camera, 0x01000203, param, bytes.length, buffer) !== 0,
    'Modified carrier was accepted');
  testRequire(testSinkState.readU32() === before, 'Modified carrier reached sink');
  buffer.writeU8(bytes[0]);
  testRequire(testSet(camera, 0x01000203, param, bytes.length - 1, buffer) !== 0,
    'Truncated carrier was accepted');
  testRequire(testSinkState.readU32() === before, 'Truncated carrier reached sink');

  const control = Memory.alloc(32);
  send({type: 'test_stage', stage: 'control passthrough'});
  const controlBytes = Uint8Array.from({length: 32}, (_, i) => (i * 17) & 255);
  control.writeByteArray(controlBytes);
  testRequire(testSet(camera, 0x00000115, param, 32, control) === 0, 'Control call failed');
  testRequire(bytesEqual(new Uint8Array(control.readByteArray(32)), controlBytes),
    'Camera control was modified');
  testRequire(testSinkState.add(12).readU32() === 0x00000115 &&
    testSinkState.add(24).readPointer().equals(control), 'Control pointer/property changed');

  testSinkState.add(4).writeU32(0x2019);
  testRequire(testSet(camera, 0x01000203, param, bytes.length, buffer) === 0x2019,
    'Original Canon failure code was not preserved');
  testRequire(armed, 'Failed registration disarmed the target');
  testSinkState.add(4).writeU32(0);
  testRequire(testSet(camera, 0x01000203, param, bytes.length, buffer) === 0,
    'Validated carrier was rejected');
  testRequire(testSinkState.readU32() === before + 3, 'Unexpected sink call count');
  testRequire(testSinkState.add(8).readPointer().equals(camera) &&
    testSinkState.add(12).readU32() === 0x01000203 &&
    testSinkState.add(16).readS32() === param &&
    testSinkState.add(20).readU32() === bytes.length &&
    testSinkState.add(24).readPointer().equals(buffer), 'Original transport arguments changed');
  testRequire(bytesEqual(new Uint8Array(buffer.readByteArray(bytes.length)), bytes),
    'Original transport bytes changed');
  testRequire(!armed, 'Successful registration did not disarm');
  return [{compiler: compiled[0], slot: Number(slot), modifiedBlocked: true,
    truncatedBlocked: true, controlUntouched: true, failurePreserved: true,
    argumentsPreserved: true, successDisarmed: true, sinkCalls: 3}, compiled[1]];
};

rpc.exports.teststale = function(pf3Path, cameraIdHex, descriptorHex) {
  armCompilerForOfflineTest(pf3Path, 'STALE TEST');
  const good = compilePf3(pf3Path, cameraIdHex, descriptorHex);
  testRequire(good[0].ok, 'Initial compiler call failed');
  const buffer = copyToMemory(new Uint8Array(good[1]));
  const count = testSinkState.readU32();
  armCompilerForOfflineTest(pf3Path + '.missing', 'MISSING TEST');
  let failed;
  try { failed = compilePf3(pf3Path + '.missing', cameraIdHex, descriptorHex); }
  catch (_) { failed = [{ok: false}]; }
  testRequire(!failed[0].ok, 'Missing PF3 unexpectedly compiled');
  testRequire(testSet(ptr(1), 0x01000203, 33, good[1].byteLength, buffer) !== 0,
    'Old compiler output survived rearming');
  testRequire(testSinkState.readU32() === count, 'Stale output reached sink');
  return {staleBlocked: true};
};

rpc.exports.readtesttables = function(path, includeDense) {
  // Read the serialized PF3 inputs through the exported Canon API. The Python
  // checker separately reconstructs planar full33 values from these inputs.
  const api = compilerApi();
  api.Initialize();
  const out = Memory.alloc(Process.pointerSize);
  out.writePointer(ptr(0));
  testRequire(api.Create(Memory.allocUtf8String(path), 2, 0, out) === 0, 'PF3 open failed');
  const ref = out.readPointer();
  try {
    const name = Memory.alloc(32);
    testRequire(api.Get(ref, 0x40001002, 0, 32, name) === 0, 'PF3 name read failed');
    return {nameHex: testFastHex(name.readByteArray(32)),
      table70: includeDense ? testFastHex(readPf3DenseTable(api.Get, ref, 0x40001070)) : '',
      table71: includeDense ? testFastHex(readPf3DenseTable(api.Get, ref, 0x40001071)) : ''};
  } finally { api.Release(ref); }
};
