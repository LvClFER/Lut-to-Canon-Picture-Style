'use strict';

// Test-only x86 EDSDK sink. No EDSDK DLL, USB handle or camera is opened.
// The production interceptor still receives a real native stdcall address.
if (Process.arch !== 'ia32') throw new Error('Transport test requires an x86 host');
const testSinkState = Memory.alloc(32);
testSinkState.writeByteArray(new Uint8Array(32));
const testSinkCode = Memory.alloc(Process.pageSize);
const testCode = [];
function testU32(value) {
  for (let shift = 0; shift < 32; shift += 8) testCode.push((value >>> shift) & 255);
}
testCode.push(0xa1); testU32(testSinkState.toUInt32()); // load call count
testCode.push(0x40, 0xa3); testU32(testSinkState.toUInt32());
for (let i = 0; i < 5; i++) {
  testCode.push(0x8b, 0x44, 0x24, 4 + i * 4, 0xa3);
  testU32(testSinkState.add(8 + i * 4).toUInt32());
}
testCode.push(0xa1); testU32(testSinkState.add(4).toUInt32()); // return code
testCode.push(0xc2, 0x14, 0x00); // ret 20 (stdcall)
testSinkCode.writeByteArray(testCode);
Memory.protect(testSinkCode, Process.pageSize, 'r-x');
const testModuleLookup = Process.getModuleByName.bind(Process);
function testGetModuleByName(name) {
  if (name.toLowerCase() === 'edsdk.dll') return {
    enumerateExports: function() {
      return [{name: 'EdsSetPropertyData', type: 'function', address: testSinkCode}];
    }
  };
  return testModuleLookup(name);
};
