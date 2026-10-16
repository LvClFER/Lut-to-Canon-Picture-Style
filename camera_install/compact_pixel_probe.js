'use strict';
// Private own-host direct ABI probe. Never loaded into EOS Utility.
rpc.exports.run=function(cases) {
  if(cases.length>96)throw new Error('Unbounded pixel case count');
  const compiler=Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'),'uint32',[])();
  const mlib=Process.getModuleByName('MLib.dll');
  const call=new NativeFunction(mlib.base.add(0x1cab0),'void',
    ['double','double','double','pointer','pointer','pointer','pointer','uint32','uint32','pointer','pointer','pointer','pointer','pointer'],'mscdecl');
  const rows=[];
  function buffer(hex,max) {
    if(hex===null)return ptr(0);
    if(typeof hex!=='string'||hex.length%2||hex.length>max*2||!/^[0-9a-f]+$/i.test(hex))throw new Error('Invalid bounded buffer');
    const p=Memory.alloc(hex.length/2);p.writeByteArray(hex.match(/../g).map(v=>parseInt(v,16)));return p;
  }
  for(const item of cases) {
    const a=item.arguments;
    const pointers=[buffer(a.preCurvesHex,300),buffer(a.postCurvesHex,300),buffer(a.thirdCurvesHex,300),buffer(a.matrix240Hex,240),
      buffer(a.axisBlock?a.axisBlock.initializedHex:null,512),buffer(a.selectorBlock?a.selectorBlock.initializedHex:null,1016)];
    const output=Memory.alloc(24);
    if(item.inputs.length>1000)throw new Error('Unbounded sample count');
    for(const input of item.inputs) {
      if(input.length!==3||input.some(v=>!Number.isFinite(v)||v<0||v>1))throw new Error('Invalid pixel domain');
      output.writeByteArray(new Uint8Array(24));
      call(...input,...pointers.slice(0,4),a.mode,a.splitCount,pointers[4],pointers[5],output,output.add(8),output.add(16));
      rows.push({name:item.name,input,output:[0,1,2].map(c=>output.add(c*8).readDouble())});
    }
  }
  return {cameraAccess:false,mlibPath:mlib.path,rows};
};
