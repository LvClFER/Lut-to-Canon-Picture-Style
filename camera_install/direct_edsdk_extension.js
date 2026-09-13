'use strict';

// Direct Canon EDSDK host extension. This source is appended to
// dynamic_camera_agent.js inside a private, hidden x86 host process. The
// existing target-scoped EdsCFParse acceptance hooks therefore remain the
// single compiler implementation for both direct and EOS Utility workflows.

let directSdk = null;
let directCamera = ptr(0);
let directSessionOpen = false;
let directInitialized = false;
let directDllFolder = '';

function directExport(module, name) {
  const item = ex(module, name);
  if (!item) throw new Error('Required Canon export not found: ' + name);
  return item.address;
}

function directLoadLibrary(path) {
  const kernel = Process.getModuleByName('kernel32.dll');
  const load = new NativeFunction(directExport(kernel, 'LoadLibraryW'), 'pointer', ['pointer']);
  const handle = load(Memory.allocUtf16String(path));
  if (handle.isNull()) throw new Error('Could not load Canon runtime: ' + path);
  return handle;
}

function directLoadRuntime(folder) {
  directDllFolder = String(folder || '').replace(/[\\\/]$/, '');
  if (!directDllFolder) throw new Error('Canon runtime folder is required');
  const kernel = Process.getModuleByName('kernel32.dll');
  const setDirectory = new NativeFunction(
    directExport(kernel, 'SetDllDirectoryW'), 'bool', ['pointer']
  );
  if (!setDirectory(Memory.allocUtf16String(directDllFolder))) {
    throw new Error('Could not configure the Canon DLL search folder');
  }
  directLoadLibrary(directDllFolder + '\\EDSDK.dll');
  directLoadLibrary(directDllFolder + '\\EdsCFParse.dll');
  scan();
  if (!compilerHooked || !edsHooked) {
    throw new Error('Canon compiler/EDSDK hooks did not initialize in the direct host');
  }
  return {
    ok: true,
    architecture: Process.arch,
    edsdkPath: Process.getModuleByName('EDSDK.dll').path,
    edsCFParsePath: Process.getModuleByName('EdsCFParse.dll').path,
    compilerResolver: 'semantic-signatures-v1'
  };
}

function directApi() {
  const module = Process.getModuleByName('EDSDK.dll');
  return {
    Initialize: new NativeFunction(directExport(module, 'EdsInitializeSDK'), 'uint32', []),
    Terminate: new NativeFunction(directExport(module, 'EdsTerminateSDK'), 'uint32', []),
    GetCameraList: new NativeFunction(directExport(module, 'EdsGetCameraList'), 'uint32', ['pointer']),
    GetChildCount: new NativeFunction(directExport(module, 'EdsGetChildCount'), 'uint32', ['pointer', 'pointer']),
    GetChildAtIndex: new NativeFunction(directExport(module, 'EdsGetChildAtIndex'), 'uint32', ['pointer', 'int32', 'pointer']),
    GetDeviceInfo: new NativeFunction(directExport(module, 'EdsGetDeviceInfo'), 'uint32', ['pointer', 'pointer']),
    OpenSession: new NativeFunction(directExport(module, 'EdsOpenSession'), 'uint32', ['pointer']),
    CloseSession: new NativeFunction(directExport(module, 'EdsCloseSession'), 'uint32', ['pointer']),
    GetPropertySize: new NativeFunction(
      directExport(module, 'EdsGetPropertySize'), 'uint32',
      ['pointer', 'uint32', 'int32', 'pointer', 'pointer']
    ),
    GetPropertyData: new NativeFunction(
      directExport(module, 'EdsGetPropertyData'), 'uint32',
      ['pointer', 'uint32', 'int32', 'uint32', 'pointer']
    ),
    SetPropertyData: new NativeFunction(
      directExport(module, 'EdsSetPropertyData'), 'uint32',
      ['pointer', 'uint32', 'int32', 'uint32', 'pointer']
    ),
    SendStatusCommand: new NativeFunction(
      directExport(module, 'EdsSendStatusCommand'), 'uint32', ['pointer', 'uint32', 'int32']
    ),
    GetEvent: new NativeFunction(directExport(module, 'EdsGetEvent'), 'uint32', []),
    Release: new NativeFunction(directExport(module, 'EdsRelease'), 'uint32', ['pointer'])
  };
}

function directReadProperty(property, param, maximumSize) {
  if (!directSessionOpen || directCamera.isNull()) throw new Error('Canon camera session is not open');
  const dataType = Memory.alloc(4);
  const dataSize = Memory.alloc(4);
  dataType.writeU32(0);
  dataSize.writeU32(0);
  const rcSize = directSdk.GetPropertySize(directCamera, property, param, dataType, dataSize);
  const size = dataSize.readU32();
  if (rcSize !== 0) {
    throw new Error('EdsGetPropertySize 0x' + property.toString(16) + ' failed: 0x' + rcSize.toString(16));
  }
  const cap = maximumSize || 1048576;
  if (size <= 0 || size > cap) {
    throw new Error('Canon property 0x' + property.toString(16) + ' returned invalid size ' + size);
  }
  const output = Memory.alloc(size);
  output.writeByteArray(new Uint8Array(size));
  const rcData = directSdk.GetPropertyData(directCamera, property, param, size, output);
  if (rcData !== 0) {
    throw new Error('EdsGetPropertyData 0x' + property.toString(16) + ' failed: 0x' + rcData.toString(16));
  }
  return { property: property, param: param, dataType: dataType.readU32(), size: size, bytes: readBytes(output, size) };
}

function directWriteProperty(property, param, bytes) {
  const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (data.length <= 0 || data.length > 1048576) throw new Error('Invalid Canon property write size');
  return directSdk.SetPropertyData(directCamera, property, param, data.length, copyToMemory(data));
}

function directDeviceInfo(camera) {
  // EdsDeviceInfo: char portName[256], char deviceDescription[256],
  // EdsUInt32 deviceSubType, EdsUInt32 reserved.
  const info = Memory.alloc(520);
  info.writeByteArray(new Uint8Array(520));
  const rc = directSdk.GetDeviceInfo(camera, info);
  if (rc !== 0) throw new Error('EdsGetDeviceInfo failed: 0x' + rc.toString(16));
  return {
    portName: info.readAnsiString(256) || '',
    description: info.add(256).readAnsiString(256) || '',
    deviceSubType: info.add(512).readU32()
  };
}

function directDisconnect() {
  const result = { closeSession: null, releaseCamera: null, terminate: null };
  if (directSdk && directSessionOpen && !directCamera.isNull()) {
    try { result.closeSession = directSdk.CloseSession(directCamera); } catch (_) {}
  }
  directSessionOpen = false;
  if (directSdk && !directCamera.isNull()) {
    try { result.releaseCamera = directSdk.Release(directCamera); } catch (_) {}
  }
  directCamera = ptr(0);
  if (directSdk && directInitialized) {
    try { result.terminate = directSdk.Terminate(); } catch (_) {}
  }
  directInitialized = false;
  return result;
}

function directConnect() {
  if (directSessionOpen && !directCamera.isNull()) throw new Error('A Canon camera session is already open');
  directSdk = directApi();
  const rcInitialize = directSdk.Initialize();
  if (rcInitialize !== 0) throw new Error('EdsInitializeSDK failed: 0x' + rcInitialize.toString(16));
  directInitialized = true;
  let list = ptr(0);
  try {
    const listOut = Memory.alloc(Process.pointerSize);
    listOut.writePointer(ptr(0));
    const rcList = directSdk.GetCameraList(listOut);
    list = listOut.readPointer();
    if (rcList !== 0 || list.isNull()) throw new Error('EdsGetCameraList failed: 0x' + rcList.toString(16));
    const countOut = Memory.alloc(4);
    countOut.writeS32(0);
    const rcCount = directSdk.GetChildCount(list, countOut);
    const count = countOut.readS32();
    if (rcCount !== 0) throw new Error('EdsGetChildCount failed: 0x' + rcCount.toString(16));
    if (count !== 1) {
      throw new Error(count === 0
        ? 'No Canon camera is connected or the camera is owned by another application'
        : 'More than one Canon camera is connected; leave only the intended camera connected');
    }
    const cameraOut = Memory.alloc(Process.pointerSize);
    cameraOut.writePointer(ptr(0));
    const rcChild = directSdk.GetChildAtIndex(list, 0, cameraOut);
    directCamera = cameraOut.readPointer();
    if (rcChild !== 0 || directCamera.isNull()) throw new Error('EdsGetChildAtIndex failed: 0x' + rcChild.toString(16));
  } finally {
    if (!list.isNull()) directSdk.Release(list);
  }
  try {
    const device = directDeviceInfo(directCamera);
    const rcOpen = directSdk.OpenSession(directCamera);
    if (rcOpen !== 0) throw new Error('EdsOpenSession failed: 0x' + rcOpen.toString(16));
    directSessionOpen = true;
    const cameraId = directReadProperty(0x01000001, 0, 64);
    const descriptor = directReadProperty(0x01000210, 0, 1048576);
    if (cameraId.size !== 4) throw new Error('Live Canon camera ID was not 4 bytes');
    emit({ type: 'direct_camera_connected', description: device.description, portName: device.portName });
    emit({ type: 'compiler_input_captured', input: 'cameraId', size: cameraId.size, cameraIdHex: bytesToHex(cameraId.bytes) });
    emit({ type: 'compiler_input_captured', input: 'descriptor', size: descriptor.size });
    return {
      ok: true,
      description: device.description,
      portName: device.portName,
      deviceSubType: device.deviceSubType,
      cameraIdHex: bytesToHex(cameraId.bytes),
      descriptorHex: bytesToHex(descriptor.bytes),
      descriptorSize: descriptor.size
    };
  } catch (error) {
    directDisconnect();
    throw error;
  }
}

function directCompileAndInstall(pf3Path, styleName, slot, cameraIdHex, descriptorHex) {
  if (!directSessionOpen || directCamera.isNull()) throw new Error('Canon camera session is not open');
  const selectedSlot = parseInt(slot);
  if (selectedSlot < 1 || selectedSlot > 3) throw new Error('Direct installation requires User Def. 1, 2 or 3');
  const inParam = 32 + selectedSlot;
  armCompilerForOfflineTest(String(pf3Path), String(styleName || 'PICTURE STYLE'));
  const compiled = compilePf3(String(pf3Path), String(cameraIdHex), String(descriptorHex));
  const metadata = compiled[0] || {};
  const payload = new Uint8Array(compiled[1] || new ArrayBuffer(0));
  const validation = metadata.acceptanceHook || null;
  if (!metadata.ok || !validation || !validation.ok || payload.length <= 0) {
    armed = false;
    throw new Error('Canon-native target PF3 compilation failed validation');
  }

  // Direct transport owns its own final validation. Disable the passive EDSDK
  // observer before making writes so success is reported only after 0x115 and
  // UI unlock complete, not immediately after the 0x01000203 call returns.
  armed = false;
  const rcLock = directSdk.SendStatusCommand(directCamera, 0, 0);
  if (rcLock !== 0) throw new Error('Canon UI lock failed: 0x' + rcLock.toString(16));
  let rcUnlock = 0xffffffff;
  try {
    // Read every camera-owned state object before the first mutation. 0x115 is
    // never manufactured, renamed, resized or patched; its exact live bytes are
    // replayed after the compiled style payload, matching Canon's transaction.
    const selector114 = directReadProperty(0x00000114, inParam, 4096);
    const control115 = directReadProperty(0x00000115, inParam, 4096);
    const native203 = directReadProperty(0x01000203, inParam, 1048576);
    if (selector114.size !== 4) throw new Error('Live Canon 0x00000114 selector was not 4 bytes');
    if (native203.size !== payload.length) {
      throw new Error('Canon compiler output size ' + payload.length +
        ' does not match live camera carrier size ' + native203.size);
    }
    emit({
      type: 'direct_state_captured', slot: selectedSlot,
      selector114Size: selector114.size, control115Size: control115.size,
      nativeCarrierSize: native203.size, control115Untouched: true
    });
    const rc114 = directWriteProperty(0x00000114, inParam, selector114.bytes);
    if (rc114 !== 0) throw new Error('Canon 0x00000114 write failed: 0x' + rc114.toString(16));
    directSdk.GetEvent();
    const rc203 = directWriteProperty(0x01000203, inParam, payload);
    if (rc203 !== 0) throw new Error('Canon 0x01000203 write failed: 0x' + rc203.toString(16));
    directSdk.GetEvent();
    const rc115 = directWriteProperty(0x00000115, inParam, control115.bytes);
    if (rc115 !== 0) throw new Error('Canon 0x00000115 replay failed: 0x' + rc115.toString(16));
    directSdk.GetEvent();
    rcUnlock = directSdk.SendStatusCommand(directCamera, 1, 0);
    if (rcUnlock !== 0) throw new Error('Canon UI unlock failed: 0x' + rcUnlock.toString(16));
    emit({
      type: 'direct_install_success', slot: selectedSlot, styleName: String(styleName),
      payloadSize: payload.length, compilerPath: validation.compilerPath,
      control115Size: control115.size, control115Untouched: true
    });
    return {
      ok: true, slot: selectedSlot, payloadSize: payload.length,
      compilerPath: validation.compilerPath, compilerValidation: validation,
      selector114ReadAndReplayed: true, control115ReadAndReplayedUnchanged: true,
      control115Size: control115.size, nativeCarrierSize: native203.size,
      rc114: rc114, rc203: rc203, rc115: rc115, rcUnlock: rcUnlock
    };
  } finally {
    if (rcUnlock === 0xffffffff) {
      try { directSdk.SendStatusCommand(directCamera, 1, 0); } catch (_) {}
    }
  }
}

rpc.exports.loaddirectruntime = function(folder) {
  return directLoadRuntime(folder);
};
rpc.exports.directconnect = function() {
  return directConnect();
};
rpc.exports.directcompileandinstall = function(pf3Path, styleName, slot, cameraIdHex, descriptorHex) {
  return directCompileAndInstall(pf3Path, styleName, slot, cameraIdHex, descriptorHex);
};
rpc.exports.directdisconnect = function() {
  return directDisconnect();
};
