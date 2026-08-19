
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

function hexToBytes(h) {
  h = String(h || '').replace(/[^0-9a-fA-F]/g, '');
  const a = new Uint8Array(h.length / 2);
  for (let i = 0; i < a.length; i++) a[i] = parseInt(h.substr(i * 2, 2), 16);
  return a;
}

function fixedAscii32(s) {
  const a = new Uint8Array(32);
  const t = String(s || 'PICTURE STYLE').substring(0, 31);
  for (let i = 0; i < t.length; i++) {
    const c = t.charCodeAt(i);
    a[i] = (c >= 32 && c <= 126) ? c : 95;
  }
  return a;
}

function patchPayloadName(a) {
  const n = fixedAscii32(armedName);
  for (const off of [8, 44]) {
    for (let i = 0; i < 32; i++) a[off + i] = n[i];
  }
}

function compilePf3(path, camidHex, descHex) {
  const m = Process.getModuleByName('EdsCFParse.dll');
  const createE = ex(m, 'EdsCfpCreateRef');
  const setE = ex(m, 'EdsCfpSetPropertyData');
  const getE = ex(m, 'EdsCfpGetPropertyData');
  const relE = ex(m, 'EdsCfpRelease');
  if (!createE || !setE || !getE || !relE) throw new Error('Required EdsCFParse exports not found');

  const Create = new NativeFunction(createE.address, 'uint32', ['pointer', 'uint32', 'uint32', 'pointer']);
  const Set = new NativeFunction(setE.address, 'uint32', ['pointer', 'uint32', 'uint32', 'uint32', 'pointer']);
  const Get = new NativeFunction(getE.address, 'uint32', ['pointer', 'uint32', 'uint32', 'uint32', 'pointer']);
  const Release = new NativeFunction(relE.address, 'uint32', ['pointer']);

  const pth = Memory.allocUtf8String(String(path));
  const outRef = Memory.alloc(Process.pointerSize);
  outRef.writePointer(ptr(0));
  const rcCreate = Create(pth, 2, 0, outRef);
  const ref = outRef.readPointer();
  if (rcCreate !== 0 || ref.isNull()) return [{ ok: false, rcCreate: rcCreate }, new ArrayBuffer(0)];

  const cid = hexToBytes(camidHex);
  const des = hexToBytes(descHex);
  const cidMem = Memory.alloc(cid.length); cidMem.writeByteArray(cid);
  const desMem = Memory.alloc(des.length); desMem.writeByteArray(des);

  const rcId = Set(ref, 0x01000001, 0, cid.length, cidMem);
  const rcDesc = Set(ref, 0x01000210, 0, des.length, desMem);

  const out = Memory.alloc(16744);
  out.writeByteArray(new Uint8Array(16744));
  const rcGet = Get(ref, 0x01000203, 0, 16744, out);
  const data = (rcGet === 0) ? out.readByteArray(16744) : new ArrayBuffer(0);
  const rcRelease = Release(ref);

  return [{
    ok: rcCreate === 0 && rcId === 0 && rcDesc === 0 && rcGet === 0,
    rcCreate: rcCreate, rcId: rcId, rcDesc: rcDesc, rcGet: rcGet, rcRelease: rcRelease
  }, data];
}

function hookEDS() {
  let m;
  try { m = Process.getModuleByName('EDSDK.dll'); }
  catch (_) { return false; }

  const f = ex(m, 'EdsSetPropertyData');
  if (!f) return false;

  Interceptor.attach(f.address, {
    onEnter(args) {
      this.prop = args[1].toUInt32();
      this.param = args[2].toInt32();
      this.n = args[3].toUInt32();
      this.didPatchPayload = false;

      const selectedParam = 32 + armedSlot;

      if (this.prop === 0x01000203) {
        emit({
          type: 'registration_seen',
          slot: this.param - 32,
          inParam: this.param,
          size: this.n,
          armed: armed
        });
      }

      // 0x00000115 is binary state/control data. Observe only; do not modify.
      if (this.prop === 0x00000115 && this.param === selectedParam) {
        let raw = null;
        try {
          if (this.n > 0 && this.n <= 256) raw = args[4].readByteArray(this.n);
        } catch (_) {}
        emit({
          type: 'control115_seen',
          slot: this.param - 32,
          size: this.n,
          untouched: true
        }, raw);
      }

      if (!armed || this.param !== selectedParam) return;

      if (this.prop === 0x01000203) {
        if (this.n !== 16752) {
          emit({
            type: 'install_error',
            reason: 'Native RP registration payload was not 16752 bytes',
            size: this.n,
            slot: this.param - 32
          });
          return;
        }
        if (!armedPayload) {
          emit({ type: 'install_error', reason: 'No RP payload armed' });
          return;
        }

        const out = new Uint8Array(armedPayload);
        patchPayloadName(out);

        this.mem = Memory.alloc(16752);
        this.mem.writeByteArray(out);
        args[3] = ptr(16752);
        args[4] = this.mem;
        this.didPatchPayload = true;

        emit({
          type: 'payload_patched',
          slot: this.param - 32,
          size: 16752,
          styleName: armedName
        }, out.buffer);
      }
    },

    onLeave(ret) {
      if (this.prop !== 0x01000203) return;

      const rc = ret.toUInt32();
      emit({
        type: 'registration_return',
        slot: this.param - 32,
        rc: rc,
        patched: this.didPatchPayload,
        size: this.n
      });

      if (this.didPatchPayload) {
        if (rc === 0) {
          const doneSlot = armedSlot;
          armed = false;
          emit({
            type: 'install_success',
            slot: doneSlot,
            styleName: armedName,
            payloadWriteOK: true,
            control115Patched: false
          });
        } else {
          emit({
            type: 'install_error',
            reason: 'Patched 0x01000203 write failed',
            rc: rc,
            slot: this.param - 32
          });
        }
      }
    }
  });

  edsHooked = true;
  return true;
}

function scan() {
  let c = null;
  try { c = Process.getModuleByName('EdsCFParse.dll'); } catch (_) {}
  if (!edsHooked) {
    try { hookEDS(); }
    catch (e) { emit({ type: 'hook_error', error: String(e) }); }
  }
  if (c && edsHooked && !readySent) {
    readySent = true;
    emit({ type: 'ready', cfpPath: c.path, cfpSize: c.size });
  }
}

scan();
setInterval(scan, 250);

rpc.exports = {
  compile: function(path, camidHex, descHex) {
    return compilePf3(path, camidHex, descHex);
  },
  arm: function(slot, payloadHex, styleName) {
    const p = hexToBytes(payloadHex);
    if (p.length !== 16752) throw new Error('payload must be 16752 bytes');
    const s = parseInt(slot);
    if (s < 1 || s > 3) throw new Error('slot must be 1..3');
    armedPayload = p.buffer;
    armedSlot = s;
    armedName = String(styleName || 'PICTURE STYLE').substring(0, 31);
    armed = true;
    emit({ type: 'armed', slot: s, styleName: armedName, payloadSize: p.length });
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
