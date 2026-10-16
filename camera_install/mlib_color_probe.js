'use strict';
// Internal math only, own laboratory process. Caller verifies both DLL hashes.
rpc.exports.run = function(vectors, modes, floatLab) {
  const compiler = Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'), 'uint32', [])();
  const mlib = Process.getModuleByName('MLib.dll');
  const signature = ['pointer', 'pointer', 'pointer', 'uint32', 'double', 'double', 'double'];
  const forward = new NativeFunction(mlib.base.add(floatLab ? 0x1470 : 0x1000), 'uint32', signature, 'fastcall');
  const inverse = new NativeFunction(mlib.base.add(floatLab ? 0x1600 : 0x1790), 'uint32', signature, 'fastcall');
  const rows = [];
  for (const mode of modes) {
    for (const vector of vectors) {
      const x = Memory.alloc(8), y = Memory.alloc(8), z = Memory.alloc(8);
      const r = Memory.alloc(8), g = Memory.alloc(8), b = Memory.alloc(8);
      x.writeDouble(0); y.writeDouble(0); z.writeDouble(0);
      r.writeDouble(0); g.writeDouble(0); b.writeDouble(0);
      const rcForward = forward(x, y, z, mode, ...vector);
      const xyz = [x.readDouble(), y.readDouble(), z.readDouble()];
      const rcInverse = inverse(r, g, b, mode, ...xyz);
      rows.push({mode, input: vector, forward: xyz, inverse: [r.readDouble(), g.readDouble(), b.readDouble()],
                 rcForward, rcInverse});
    }
  }
  return {mlibPath: mlib.path, floatLab:Boolean(floatLab), rows};
};
