'use strict';

let seq = 0;
let readySent = false;
let edsHooked = false;
let armed = false;
let armedSlot = 0;
let armedPayload = null;
let armedName = 'PICTURE STYLE';

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
  const original = String(value || '');
  const hex = original.replace(/\s/g, '');
  if (!/^[0-9a-fA-F]*$/.test(hex) || (hex.length % 2) !== 0) {
    throw new Error('invalid hexadecimal payload');
  }
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.substr(i * 2, 2), 16);
  return out;
}

function fixedAscii32(s) {
  const out = new Uint8Array(32);
  const text = String(s || 'PICTURE STYLE').substring(0, 31);
  for (let i = 0; i < text.length; i++) {
    const code = text.charCodeAt(i);
    out[i] = (code >= 32 && code <= 126) ? code : 95;
  }
  return out;
}

function patchPayloadName(payload) {
  const name = fixedAscii32(armedName);
  for (const offset of [8, 44]) {
    for (let i = 0; i < 32; i++) payload[offset + i] = name[i];
  }
}

function compilePf3(path, cameraIdHex, descriptorHex) {
  const module = Process.getModuleByName('EdsCFParse.dll');
  const createExport = ex(module, 'EdsCfpCreateRef');
  const setExport = ex(module, 'EdsCfpSetPropertyData');
  const getExport = ex(module, 'EdsCfpGetPropertyData');
  const releaseExport = ex(module, 'EdsCfpRelease');
  if (!createExport || !setExport || !getExport || !releaseExport) {
    throw new Error('Required EdsCFParse exports not found');
  }

  const Create = new NativeFunction(createExport.address, 'uint32', ['pointer', 'uint32', 'uint32', 'pointer']);
  const Set = new NativeFunction(setExport.address, 'uint32', ['pointer', 'uint32', 'uint32', 'uint32', 'pointer']);
  const Get = new NativeFunction(getExport.address, 'uint32', ['pointer', 'uint32', 'uint32', 'uint32', 'pointer']);
  const Release = new NativeFunction(releaseExport.address, 'uint32', ['pointer']);

  const pathMemory = Memory.allocUtf8String(String(path));
  const outRef = Memory.alloc(Process.pointerSize);
  outRef.writePointer(ptr(0));
  const rcCreate = Create(pathMemory, 2, 0, outRef);
  const ref = outRef.readPointer();
  if (rcCreate !== 0 || ref.isNull()) return [{ ok: false, rcCreate: rcCreate }, new ArrayBuffer(0)];

  const cameraId = hexToBytes(cameraIdHex);
  const descriptor = hexToBytes(descriptorHex);
  const cameraIdMemory = Memory.alloc(cameraId.length); cameraIdMemory.writeByteArray(cameraId);
  const descriptorMemory = Memory.alloc(descriptor.length); descriptorMemory.writeByteArray(descriptor);

  const rcId = Set(ref, 0x01000001, 0, cameraId.length, cameraIdMemory);
  const rcDescriptor = Set(ref, 0x01000210, 0, descriptor.length, descriptorMemory);
  const output = Memory.alloc(16744);
  output.writeByteArray(new Uint8Array(16744));
  const rcGet = Get(ref, 0x01000203, 0, 16744, output);
  const data = (rcGet === 0) ? output.readByteArray(16744) : new ArrayBuffer(0);
  const rcRelease = Release(ref);

  return [{
    ok: rcCreate === 0 && rcId === 0 && rcDescriptor === 0 && rcGet === 0,
    rcCreate: rcCreate, rcId: rcId, rcDesc: rcDescriptor,
    rcGet: rcGet, rcRelease: rcRelease
  }, data];
}

function hookEdsdk() {
  let module;
  try { module = Process.getModuleByName('EDSDK.dll'); }
  catch (_) { return false; }
  const target = ex(module, 'EdsSetPropertyData');
  if (!target) return false;

  Interceptor.attach(target.address, {
    onEnter(args) {
      this.prop = args[1].toUInt32();
      this.param = args[2].toInt32();
      this.n = args[3].toUInt32();
      this.didPatchPayload = false;
      const selectedParam = 32 + armedSlot;

      if (this.prop === 0x01000203) {
        emit({
          type: 'registration_seen', slot: this.param - 32,
          inParam: this.param, size: this.n, armed: armed
        });
      }

      // 0x00000115 is binary state/control data. Observe only; do not modify.
      if (this.prop === 0x00000115 && this.param === selectedParam) {
        emit({
          type: 'control115_seen', slot: this.param - 32,
          size: this.n, untouched: true
        });
      }

      if (!armed || this.param !== selectedParam) return;
      if (this.prop !== 0x01000203) return;
      if (this.n !== 16752) {
        emit({
          type: 'install_error', reason: 'Native RP registration payload was not 16752 bytes',
          size: this.n, slot: this.param - 32
        });
        return;
      }
      if (!armedPayload) {
        emit({ type: 'install_error', reason: 'No RP payload armed' });
        return;
      }

      const outgoing = new Uint8Array(armedPayload);
      patchPayloadName(outgoing);
      this.payloadMemory = Memory.alloc(16752);
      this.payloadMemory.writeByteArray(outgoing);
      args[3] = ptr(16752);
      args[4] = this.payloadMemory;
      this.didPatchPayload = true;
      emit({
        type: 'payload_patched', slot: this.param - 32,
        size: 16752, styleName: armedName
      }, outgoing.buffer);
    },

    onLeave(returnValue) {
      if (this.prop !== 0x01000203) return;
      const rc = returnValue.toUInt32();
      emit({
        type: 'registration_return', slot: this.param - 32,
        rc: rc, patched: this.didPatchPayload, size: this.n
      });
      if (!this.didPatchPayload) return;
      if (rc === 0) {
        const completedSlot = armedSlot;
        armed = false;
        armedPayload = null;
        emit({
          type: 'install_success', slot: completedSlot,
          styleName: armedName, payloadWriteOK: true, control115Patched: false
        });
      } else {
        emit({
          type: 'install_error', reason: 'Patched 0x01000203 write failed',
          rc: rc, slot: this.param - 32
        });
      }
    }
  });
  edsHooked = true;
  return true;
}

function scan() {
  let compiler = null;
  try { compiler = Process.getModuleByName('EdsCFParse.dll'); } catch (_) {}
  if (!edsHooked) {
    try { hookEdsdk(); }
    catch (error) { emit({ type: 'hook_error', error: String(error) }); }
  }
  if (compiler && edsHooked && !readySent) {
    readySent = true;
    emit({ type: 'ready', cfpPath: compiler.path, cfpSize: compiler.size });
  }
}

scan();
setInterval(scan, 250);

rpc.exports = {
  compile: function(path, cameraIdHex, descriptorHex) {
    return compilePf3(path, cameraIdHex, descriptorHex);
  },
  arm: function(slot, payloadHex, styleName) {
    const payload = hexToBytes(payloadHex);
    if (payload.length !== 16752) throw new Error('payload must be 16752 bytes');
    const selectedSlot = parseInt(slot);
    if (selectedSlot < 1 || selectedSlot > 3) throw new Error('slot must be 1..3');
    armedPayload = payload.buffer;
    armedSlot = selectedSlot;
    armedName = String(styleName || 'PICTURE STYLE').substring(0, 31);
    armed = true;
    emit({ type: 'armed', slot: selectedSlot, styleName: armedName, payloadSize: payload.length });
    return true;
  },
  disarm: function() {
    armed = false;
    armedPayload = null;
    armedSlot = 0;
    armedName = 'PICTURE STYLE';
    return true;
  },
  status: function() {
    return { ready: readySent, armed: armed, slot: armedSlot, styleName: armedName };
  }
};
