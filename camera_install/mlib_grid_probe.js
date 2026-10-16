'use strict';
rpc.exports.dispatch = function() {
  const compiler=Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'),'uint32',[])();
  const rows=[];
  for(const [name,slot] of [['grid_wrapper',0xd11d0],['per_pixel_old_selector',0xd11fc]]) {
    const target=compiler.base.add(slot).readPointer();
    const owner=target.isNull() ? null : Process.findModuleByAddress(target);
    rows.push({name,compilerSlotRva:'0x'+slot.toString(16),
               ownerModule:owner ? owner.name : null,
               functionRva:owner ? target.sub(owner.base).toString() : null});
  }
  return {cameraAccess:false,mlibPath:Process.getModuleByName('MLib.dll').path,rows};
};
rpc.exports.legacySectors = function(cases,dense) {
  const compiler=Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'),'uint32',[])();
  const mlib=Process.getModuleByName('MLib.dll'),adapter=Memory.alloc(Process.pageSize);
  const address=mlib.base.add(0xfa40).toUInt32();
  adapter.writeByteArray([0x55,0x8b,0xec,0x8b,0x4d,0x08,0x8b,0x55,0x0c,
    0xff,0x75,0x18,0xff,0x75,0x14,0xff,0x75,0x10,0xb8,
    address&255,(address>>>8)&255,(address>>>16)&255,(address>>>24)&255,
    0xff,0xd0,0x83,0xc4,0x0c,0x5d,0xc3]);
  Memory.protect(adapter,Process.pageSize,'r-x');
  const call=new NativeFunction(adapter,'uint32',['pointer','uint32','pointer','uint32','pointer'],'mscdecl');
  const input=Memory.alloc(24),output=Memory.alloc(24),rows=[],compositionCalls=[],legacyAxisCalls=[];
  const colors=[];
  for(let r=0;r<=8;r++)for(let g=0;g<=8;g++)for(let b=0;b<=8;b++)colors.push([r/8,g/8,b/8]);
  if(dense){
    let seed=0x13579bdf;
    for(let i=0;i<512;i++){
      const rgb=[];for(let c=0;c<3;c++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;rgb.push(seed/4294967295);}
      colors.push(rgb);
    }
    for(let centre=0;centre<6;centre++)for(const local of [-.5,-1/6,0,1/6,.5])
      for(const epsilon of [-1e-10,-1e-14,0,1e-14,1e-10])for(const [hi,lo] of [[.75,0],[.875,.125],[1,.25]]){
        const h=((centre+local+epsilon)%6+6)%6,sector=Math.floor(h),f=h-sector;
        const up=lo+(hi-lo)*f,down=hi-(hi-lo)*f;
        colors.push([[hi,up,lo],[down,hi,lo],[lo,hi,up],[lo,down,hi],[up,lo,hi],[hi,lo,down]][sector]);
      }
  }
  let active=null;
  const axisHook=Interceptor.attach(mlib.base.add(0x10a00),{
    onEnter(args) {
      if (!active) return;
      const group=p=>{
        const count=p.readU32();
        if (count>12) throw new Error('Unbounded axis group');
        return Array.from(new Uint8Array(p.readByteArray(4+16*count)),v=>v.toString(16).padStart(2,'0')).join('');
      };
      this.outputs=[args[3],args[4],args[5],args[6]];
      this.item={name:active.name,rgb:active.rgb,
        inputRGB:[0,1,2].map(c=>this.context.ecx.add(c*8).readDouble()),
        centre:args[0].add(8).readS32(),
        currentGroupHex:group(args[0]),previousGroupHex:group(args[1]),nextGroupHex:group(args[2])};
      legacyAxisCalls.push(this.item);
    },
    onLeave() {if(this.item){this.item.output=this.outputs.map(p=>p.readDouble());this.item.adjustments=this.item.output;}}
  });
  const compositionHook=Interceptor.attach(mlib.base.add(0x1e90),{
    onEnter(args) {
      if (!active) return;
      const stack=this.context.esp;
      this.pointers=[this.context.ecx,this.context.edx,args[0]];
      this.item={name:active.name,rgb:active.rgb,
        inputHSL:this.pointers.map(p=>p.readDouble()),
        saturationDelta:stack.add(8).readDouble(),lightnessDelta:stack.add(16).readDouble(),
        weights:[24,32,40].map(o=>stack.add(o).readDouble()),power:stack.add(48).readDouble()};
      compositionCalls.push(this.item);
    },
    onLeave() {if (this.item) this.item.outputHSL=this.pointers.map(p=>p.readDouble());}
  });
  for (const item of cases) {
    if (item.parametersHex.length<16 || item.parametersHex.length>1024) throw new Error('Require bounded parameter block');
    const parameters=Memory.alloc(item.parametersHex.length/2);parameters.writeByteArray(item.parametersHex.match(/../g).map(v=>parseInt(v,16)));
    const kind=parameters.readU32(),count=parameters.add(4).readU32(),points=parameters.add(8).readU32();
    if (![1,2].includes(kind)||count<1||count>6||![4,5].includes(points)||
        item.parametersHex.length/2!==8+count*(4+16*points))
      throw new Error('Invalid legacy group layout');
    for (const rgb of colors) {
      rgb.forEach((v,c)=>input.add(c*8).writeDouble(v));
      active={name:item.name,rgb};
      const nodes=item.nodes || 33;
      call(input,2,parameters,nodes,output);
      rows.push({name:item.name,nodes,rgb,output:[0,1,2].map(c=>output.add(c*8).readDouble())});
    }
  }
  compositionHook.detach();
  axisHook.detach();
  return {mlibPath:mlib.path,cameraAccess:false,cases,rows,compositionCalls,legacyAxisCalls,helperCalls:legacyAxisCalls};
};
rpc.exports.modernReplay = function(cases,legacy,observeNegative) {
  const compiler=Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'),'uint32',[])();
  const mlib=Process.getModuleByName('MLib.dll'),adapter=Memory.alloc(Process.pageSize),address=mlib.base.add(legacy ? 0x14bd0 : 0x11220).toUInt32();
  const code=[0x55,0x8b,0xec,0x8b,0x4d,0x08,0x8b,0x55,0x0c];
  for (let i=9;i>=2;i--) code.push(0xff,0x75,8+i*4);
  code.push(0xb8,address&255,(address>>>8)&255,(address>>>16)&255,(address>>>24)&255,
    0xff,0xd0,0x83,0xc4,0x20,0x5d,0xc3);
  adapter.writeByteArray(code); Memory.protect(adapter,Process.pageSize,'r-x');
  const call=new NativeFunction(adapter,'uint32',['pointer','pointer','pointer','pointer','uint32','pointer','pointer','pointer','uint32','pointer'],'mscdecl');
  const rows=[],negativeCurveCalls=[];
  let activeCase=null,activeOld=ptr(0);
  const negativeHook=observeNegative ? Interceptor.attach(mlib.base.add(0xfa40),{
    onEnter(args) {
      if(activeCase && args[0].equals(activeOld))this.output=args[2];
    },
    onLeave() {
      if(!this.output)return;
      const rgb=[0,1,2].map(c=>this.output.add(c*8).readDouble());
      if(rgb.some(v=>v<0) && negativeCurveCalls.length<2000){
        const observation={name:activeCase,preCurveRGB:rgb};
        negativeCurveCalls.push(observation);
        if(negativeCurveCalls.length<=64)send({kind:'negativePreCurveRGB',...observation});
      }
    }
  }) : null;
  for (const item of cases) {
    const keep=[];
    const allocate=(hex,size)=>{
      if (hex===null) return ptr(0);
      if (typeof hex!=='string'||hex.length!==size*2) throw new Error('Invalid initialized replay buffer');
      const p=Memory.alloc(size); p.writeByteArray(hex.match(/../g).map(v=>parseInt(v,16))); keep.push(p); return p;
    };
      const a=item.arguments;
      if (!legacy && a.additionalParametersHeader8Hex !== undefined && a.additionalParametersHeader8Hex !== null &&
          a.additionalParametersHeader8Hex !== '0100000000000000') throw new Error('Nonempty legacy header not replayed');
    let empty=a.additionalEmptyParametersHex;
    if (empty===undefined && a.additionalParameters512Hex) empty=a.additionalParameters512Hex.slice(0,16);
    if (!legacy && empty!==null && empty!=='0100000000000000') throw new Error('Nonempty legacy parameters not replayed');
    const block=name=>{
      const b=a[name];
      if (b===null) return ptr(0);
      if (!b || ![1,2].includes(b.kind) || b.count>12 || b.bytes<8 || b.bytes>2400)
        throw new Error('Unverified parameter block');
      const expected=b.count ? 8+b.count*(4+16*b.points) : 8;
      if (b.bytes!==expected) throw new Error('Parameter block size differs from native stride');
      return allocate(b.initializedHex,b.bytes);
    };
    const grid=Memory.alloc(16+item.nodes**3*24);
    grid.writeByteArray(item.headerHex.match(/../g).map(v=>parseInt(v,16)));
    grid.add(16).writeByteArray(new Uint8Array(item.nodes**3*24));
    activeCase=item.name || 'captured-baseline';
    activeOld=legacy ? block('oldParameterBlock') : allocate(a.oldParameters512Hex,512);
    const rc=call(allocate(a.preCurvesHex,300),allocate(a.postCurvesHex,300),
      allocate(a.thirdCurvesHex,300),allocate(a.matrix240Hex,240),a.numericArguments[0],
      activeOld,
      legacy ? block('axisParameterBlock') : allocate(a.sixAxes512Hex,512),
      legacy ? block('additionalParameterBlock') : allocate(empty,8),a.numericArguments[1],grid)&255;
    const outputHex=Array.from(new Uint8Array(grid.add(16).readByteArray(item.nodes**3*24)),v=>v.toString(16).padStart(2,'0')).join('');
    rows.push({name:item.name || null,model:item.model || null,source:item.source || null,nodes:item.nodes,rc,
      stockExact:item.expectedHex===null ? null : outputHex===item.expectedHex,
      outputDenseFloat64Hex:outputHex});
  }
  if(negativeHook)negativeHook.detach();
  return {mlibPath:mlib.path,cameraAccess:false,rows,negativeCurveCalls};
};
rpc.exports.integerTetrahedral = function() {
  const compiler = Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'),'uint32',[])();
  const call = new NativeFunction(compiler.base.add(0x47af0),'void',
    ['int','int','int','pointer','pointer','pointer','pointer'],'mscdecl');
  // Endpoint probes may load zero-weight neighbor cells beyond the final
  // plane. Keep those reads inside an owned padded allocation.
  const rows=[],table=Memory.alloc(16000),outputs=[Memory.alloc(4),Memory.alloc(4),Memory.alloc(4)];
  for (const pattern of ['identity','modular','signed','impulse','overflow']) {
    const values=[];
    for (let c=0;c<3;c++) for (let r=0;r<10;r++) for (let g=0;g<10;g++) for (let b=0;b<10;b++) {
      let v=([r,g,b][c])*64;
      if (pattern==='modular') v=(r*19+g*37+b*13+c*23)%1024;
      if (pattern==='signed') v=((r*17+g*71+b*53+c*19)%1024)-512;
      if (pattern==='impulse') v=(r===4&&g===5&&b===6)?(c+1)*100:0;
      if (pattern==='overflow') v=(r*19+g*37+b*13+c*23)*1000000;
      values.push(v); table.add((values.length-1)*4).writeS32(v);
    }
    for (const base of [0,4,8]) for (const fractions of [[3,19,51],[3,51,19],[19,3,51],
      [19,51,3],[51,3,19],[51,19,3],[0,0,0],[32,32,32],[63,63,63],[0,31,63]]) {
      const coordinates=fractions.map((v,i)=>(base*64+v)*16+i);
      call(...coordinates,...outputs,table);
      rows.push({pattern,coordinates,output:outputs.map(p=>p.readS32())});
    }
    let seed=0x12345678;
    for (let i=0;i<1024;i++) {
      const coordinates=[];
      for (let c=0;c<3;c++) { seed=(Math.imul(seed,1664525)+1013904223)>>>0; coordinates.push(seed%9216); }
      call(...coordinates,...outputs,table);
      rows.push({pattern,coordinates,output:outputs.map(p=>p.readS32())});
    }
    for (const coordinates of [[3*1024+512,4*1024+512,5*1024+512],[4*1024,5*1024,6*1024]]) {
      call(...coordinates,...outputs,table);
      rows.push({pattern,coordinates,output:outputs.map(p=>p.readS32())});
    }
    for (const guard of [0,123456789]) {
      for(let i=3000;i<4000;i++)table.add(i*4).writeS32(guard);
      for(const coordinates of [[9216,0,0],[0,9216,0],[0,0,9216],
        [9216,9216,9216],[9216,8191,4095],[4095,9216,8191],[8191,4095,9216]]) {
        call(...coordinates,...outputs,table);
        rows.push({pattern,coordinates,guard,output:outputs.map(p=>p.readS32())});
      }
    }
  }
  return {mlibPath:Process.getModuleByName('MLib.dll').path,cameraAccess:false,rows};
};
rpc.exports.axes = function(cases, dense) {
  const compiler = Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'), 'uint32', [])();
  const mlib = Process.getModuleByName('MLib.dll'), adapter = Memory.alloc(Process.pageSize);
  const address = mlib.base.add(0xfa40).toUInt32();
  adapter.writeByteArray([0x55,0x8b,0xec,0x8b,0x4d,0x08,0x8b,0x55,0x0c,
    0xff,0x75,0x18,0xff,0x75,0x14,0xff,0x75,0x10,0xb8,
    address&255,(address>>>8)&255,(address>>>16)&255,(address>>>24)&255,
    0xff,0xd0,0x83,0xc4,0x0c,0x5d,0xc3]);
  Memory.protect(adapter,Process.pageSize,'r-x');
  const call = new NativeFunction(adapter,'uint32',['pointer','uint32','pointer','uint32','pointer'],'mscdecl');
  const helperCalls = [];
  let activeCase = null;
  const hook = Interceptor.attach(mlib.base.add(0x10a00), {
    onEnter(args) {
      if (!activeCase || args[0].readU32() !== 5) return;
      this.outputs = [args[3],args[4],args[5],args[6]];
      this.item = {name:activeCase.name,rgb:activeCase.rgb,
        centre:args[0].add(8).readU32(),
        currentGroupHex:Array.from(new Uint8Array(args[0].readByteArray(84)),v=>v.toString(16).padStart(2,'0')).join('')};
      helperCalls.push(this.item);
    },
    onLeave() {
      if (this.item) this.item.adjustments = this.outputs.map(p=>p.readDouble());
    }
  });
  const rows = [], samples = [[0,0,0],[1,1,1],[.5,.5,.5],[1,0,0],[0,1,0],[0,0,1],
    [.8,.2,.2],[.4,.1,.1],[.8,.5,.5],[.8,.4,.2],[.8,.2,.4],[.2,.8,.4],[.4,.2,.8]];
  if (dense) {
    const baseline = cases[0].parametersHex.match(/../g).map(v=>parseInt(v,16));
    for (const word of [16,17,18]) for (const strength of [-100,-50,-10,50,100]) {
      const buffer = Memory.alloc(512); buffer.writeByteArray(baseline);
      buffer.add(word*4).writeS32(strength);
      cases.push({name:'SYNTHETIC_WORD'+word+'_'+strength,parametersHex:
        Array.from(new Uint8Array(buffer.readByteArray(512)),v=>v.toString(16).padStart(2,'0')).join('')});
    }
    for (let axis=1;axis<6;axis++) for (let field=0;field<3;field++) {
      const buffer = Memory.alloc(512); buffer.writeByteArray(baseline);
      buffer.add((16+21*axis+field)*4).writeS32(10);
      cases.push({name:'SYNTHETIC_AXIS'+axis+'_FIELD'+field,parametersHex:
        Array.from(new Uint8Array(buffer.readByteArray(512)),v=>v.toString(16).padStart(2,'0')).join('')});
    }
    for (const combination of [
      [[20,10,10],[-20,-10,-10],[10,20,5],[-10,-20,-5],[30,50,20],[-30,-50,-20]],
      [[10,10,10],[10,10,10],[10,10,10],[10,10,10],[10,10,10],[10,10,10]],
      [[-10,-10,-10],[-10,-10,-10],[-10,-10,-10],[-10,-10,-10],[-10,-10,-10],[-10,-10,-10]]]) {
      const buffer = Memory.alloc(512); buffer.writeByteArray(baseline);
      combination.forEach((values,axis)=>values.forEach((v,field)=>buffer.add((16+21*axis+field)*4).writeS32(v)));
      cases.push({name:'SYNTHETIC_COMBINED_'+cases.length,parametersHex:
        Array.from(new Uint8Array(buffer.readByteArray(512)),v=>v.toString(16).padStart(2,'0')).join('')});
    }
    for (const softness of [0,5,10,30,60]) {
      const buffer = Memory.alloc(512); buffer.writeByteArray(baseline);
      for (let axis=0;axis<6;axis++) buffer.add((20+21*axis)*4).writeS32(softness);
      for (let field=0;field<3;field++) buffer.add((16+field)*4).writeS32(10);
      cases.push({name:'SYNTHETIC_SOFTNESS_'+softness,parametersHex:
        Array.from(new Uint8Array(buffer.readByteArray(512)),v=>v.toString(16).padStart(2,'0')).join('')});
    }
    for (let hue=0;hue<6;hue+=.125) for (const lightness of [.1,.5,.9]) for (const sat of [.25,1]) {
      const high = lightness+(1-Math.abs(2*lightness-1))*sat*.5, low=2*lightness-high;
      const sector=Math.floor(hue),fraction=hue-sector;
      const up=low+(high-low)*fraction,down=high-(high-low)*fraction;
      samples.push([[high,up,low],[down,high,low],[low,high,up],
        [low,down,high],[up,low,high],[high,low,down]][sector]);
    }
  }
  for (const item of cases) {
    if (item.parametersHex.length !== 1024) throw new Error('Invalid parameter block');
    const parameters = Memory.alloc(512);
    parameters.writeByteArray(item.parametersHex.match(/../g).map(v=>parseInt(v,16)));
    for (const rgb of samples) {
      const input = Memory.alloc(24), output = Memory.alloc(24);
      rgb.forEach((v,i)=>{input.add(i*8).writeDouble(v);output.add(i*8).writeDouble(v);});
      activeCase = {name:item.name,rgb};
      call(input,2,parameters,33,output); // Return register is not a status code.
      rows.push({name:item.name,rgb,output:[0,1,2].map(i=>output.add(i*8).readDouble())});
    }
  }
  hook.detach();
  return {mlibPath:mlib.path,cameraAccess:false,rows,helperCalls};
};
rpc.exports.lab = function() {
  const compiler = Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'), 'uint32', [])();
  const mlib = Process.getModuleByName('MLib.dll');
  const adapters = [];
  function wrap(rva) {
    const adapter = Memory.alloc(Process.pageSize), address = mlib.base.add(rva).toUInt32();
    adapters.push(adapter); // Retain allocations while native functions use them.
    // Private cdecl adapter: ECX/EDX, four stack arguments, caller cleanup.
    adapter.writeByteArray([0x55,0x8b,0xec,0x8b,0x4d,0x08,0x8b,0x55,0x0c,
      0xff,0x75,0x1c,0xff,0x75,0x18,0xff,0x75,0x14,0xff,0x75,0x10,0xb8,
      address&255,(address>>>8)&255,(address>>>16)&255,(address>>>24)&255,
      0xff,0xd0,0x83,0xc4,0x10,0x5d,0xc3]);
    Memory.protect(adapter, Process.pageSize, 'r-x');
    return new NativeFunction(adapter, 'int32', ['uint32','uint32','int32','int32','int32','pointer'], 'mscdecl');
  }
  const forward = wrap(0xf070), inverse = wrap(0xee40), rows = [];
  const samples = [[.13,.37,.71],[.01,.02,.03],[.04044,.04045,.04046]];
  for (const r of [0,.02,.2,.5,1]) for (const g of [0,.02,.2,.5,1])
    for (const b of [0,.02,.2,.5,1]) samples.push([r,g,b]);
  for (const bits of [8,12,16,24]) for (const mode of [1,2]) {
    const max = 2**bits-1;
    for (const sample of samples) {
      const rgb = sample.map(v=>Math.floor(v*max)), output = Memory.alloc(12), back = Memory.alloc(12);
      output.writeByteArray(new Uint8Array(12)); back.writeByteArray(new Uint8Array(12));
      forward(bits,mode,...rgb,output);
      const lab = [0,1,2].map(i=>output.add(i*4).readS32());
      inverse(bits,mode,...lab,back);
      rows.push({bits,mode,rgb,lab,inverse:[0,1,2].map(i=>back.add(i*4).readS32())});
    }
  }
  return {mlibPath:mlib.path,cameraAccess:false,rows};
};
// Own isolated host only. Verified cdecl wrapper forwards to internal converter.
rpc.exports.run = function(captured) {
  const compiler = Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'), 'uint32', [])();
  const mlib = Process.getModuleByName('MLib.dll');
  const convert = new NativeFunction(mlib.base.add(0x1b670), 'uint32',
    ['pointer', 'pointer', 'uint32', 'pointer'], 'mscdecl');
  const hex = p => Array.from(new Uint8Array(p.readByteArray(24000)),
    v => v.toString(16).padStart(2, '0')).join('');
  const rows = [];
  const definitions = ['captured', 'identity', 'constant', 'rGain', 'rbSwap', 'product', 'square', 'impulse', 'scrambled'];
  for (const name of definitions) {
    const source = Memory.alloc(12 + 862488);
    source.writeU32(3); source.add(4).writeU32(33); source.add(8).writeU32(862488);
    if (name === 'captured') {
      source.add(12).writeByteArray(captured.match(/../g).map(v => parseInt(v, 16)));
    } else {
      for (let r = 0; r < 33; r++) for (let g = 0; g < 33; g++) for (let b = 0; b < 33; b++) {
        let rgb = [r / 32, g / 32, b / 32];
        if (name === 'constant') rgb = [0.2, 0.4, 0.8];
        if (name === 'rGain') rgb[0] *= 0.75;
        if (name === 'rbSwap') rgb = [rgb[2], rgb[1], rgb[0]];
        if (name === 'product') rgb = [rgb[0] * rgb[1], rgb[1] * rgb[2], rgb[2] * rgb[0]];
        if (name === 'square') rgb = rgb.map(value => value * value);
        if (name === 'impulse') rgb = [r === 16 && g === 16 && b === 16 ? 1 : 0,
          r === 28 && g === 31 && b === 7 ? 1 : 0, r === 32 && g === 32 && b === 32 ? 1 : 0];
        if (name === 'scrambled') rgb = [((r*17 + g*31 + b*13) % 97)/96,
          ((r*7 + g*11 + b*29) % 83)/82, ((r*19 + g*5 + b*23) % 71)/70];
        const index = (r * 1089 + g * 33 + b) * 3;
        for (let channel = 0; channel < 3; channel++) source.add(12 + (index + channel) * 8).writeDouble(rgb[channel]);
      }
    }
    for (const option of [1, 2]) for (const flag of [0, 1, 2]) {
      const destination = Memory.alloc(24016);
      destination.writeU32(3); destination.add(4).writeU32(10);
      destination.add(8).writeU32(24000); destination.add(12).writeU32(flag);
      destination.add(16).writeByteArray(new Uint8Array(24000));
      const rc = convert(source, ptr(0), option, destination);
      rows.push({name, option, flag, rc, outputDenseFloat64Hex: hex(destination.add(16))});
    }
  }
  return {mlibPath: mlib.path, cameraAccess: false, rows};
};

rpc.exports.basis = function() {
  const compiler = Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'), 'uint32', [])();
  const mlib = Process.getModuleByName('MLib.dll');
  // Internal helper uses ECX/EDX but caller cleans the stack. A private x86
  // adapter avoids assuming Microsoft fastcall. No Canon code is modified.
  const adapter = Memory.alloc(Process.pageSize);
  const address = mlib.base.add(0x1d560).toUInt32();
  const code = [0x55,0x8b,0xec,0x8b,0x4d,0x08,0x8b,0x55,0x0c,0xff,0x75,0x10,0xb8,
    address&255,(address>>>8)&255,(address>>>16)&255,(address>>>24)&255,
    0xff,0xd0,0x83,0xc4,0x04,0x5d,0xc3];
  adapter.writeByteArray(code); Memory.protect(adapter, Process.pageSize, 'r-x');
  const call = new NativeFunction(adapter, 'uint32', ['pointer','pointer','pointer'], 'mscdecl');
  const matrix = Memory.alloc(20), coefficients = Memory.alloc(57*8);
  matrix.writePointer(coefficients); matrix.add(4).writeU32(3); matrix.add(8).writeU32(3);
  matrix.add(12).writeU32(3); matrix.add(16).writeU32(0);
  const vectors = [[.2,.4,.8],[.13,.37,.71],[.7,.3,.5],[0,0,0],[1,1,1],[1,0,0],[0,1,0],[0,0,1]];
  // Exact integer-output boundaries expose one-ULP basis ordering mistakes.
  for(let r=0;r<10;r++)for(let g=0;g<10;g++)for(let b=0;b<10;b++)
    vectors.push([r,g,b].map(v=>Math.min(v*32/255,1)));
  const rows = [];
  for (const rgb of vectors) {
    const data = Memory.alloc(24), input = Memory.alloc(8), output = Memory.alloc(8);
    rgb.forEach((v,i) => data.add(i*8).writeDouble(v));
    input.writePointer(data); input.add(4).writeU32(3);
    output.writePointer(ptr(0)); output.add(4).writeU32(0);
    const rc = call(matrix,input,output), count = output.add(4).readU32();
    if (rc !== 0 || count !== 19) throw new Error('Unexpected polynomial basis output');
    const values = Array.from({length: count}, (_,i) => output.readPointer().add(i*8).readDouble());
    rows.push({rgb, rc, values});
    // Small temporary CRT allocations disappear with this isolated host.
  }
  return {mlibPath: mlib.path, cameraAccess: false, rows};
};

rpc.exports.gamut = function() {
  const compiler=Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'),'uint32',[])();
  const mlib=Process.getModuleByName('MLib.dll'),adapter=Memory.alloc(Process.pageSize);
  const address=mlib.base.add(0xf730).toUInt32();
  adapter.writeByteArray([0x55,0x8b,0xec,0x8b,0x4d,0x08,0x8b,0x55,0x0c,
    0xff,0x75,0x10,0xb8,address&255,(address>>>8)&255,(address>>>16)&255,(address>>>24)&255,
    0xff,0xd0,0x83,0xc4,0x04,0x5d,0xc3]);
  Memory.protect(adapter,Process.pageSize,'r-x');
  const call=new NativeFunction(adapter,'uint32',['pointer','pointer','pointer'],'mscdecl');
  const matrix=Memory.alloc(20),coefficients=Memory.alloc(456),data=Memory.alloc(24),input=Memory.alloc(8),
    resultData=Memory.alloc(24),output=Memory.alloc(8),rows=[];
  matrix.writePointer(coefficients);[4,8,12].forEach(o=>matrix.add(o).writeU32(3));matrix.add(16).writeU32(0);
  input.writePointer(data);input.add(4).writeU32(3);output.writePointer(resultData);output.add(4).writeU32(3);
  for(const [name,channel,gain] of [['red_gain',0,1.25],['green_gain',1,1.5],['blue_gain175',2,1.75],['blue_gain',2,2]]){
    const values=Array(57).fill(0);for(let c=0;c<3;c++)values[c*19+c]=c===channel ? gain : 1;
    values.forEach((v,i)=>coefficients.add(i*8).writeDouble(v));
    for(let r=0;r<=4;r++)for(let g=0;g<=4;g++)for(let b=0;b<=4;b++){
      const rgb=[r/4,g/4,b/4],uncorrected=rgb.map((v,c)=>v*(c===channel ? gain : 1));
      if(uncorrected.every(v=>v>=0&&v<=1))continue;
      const centre=(Math.max(...rgb)+Math.min(...rgb)-1)*.25+.5;
      if(rgb.every(v=>v===centre))continue;
      // Only probe rays moving an excessive positive channel toward gamut.
      // Rays with no feasible intersection can fail to terminate natively.
      if(centre>=rgb[channel])continue;
      let lower=0,upper=1000000,feasible=true;
      for(let c=0;c<3;c++){
        const delta=centre-rgb[c],limit=1/(c===channel ? gain : 1);
        if(delta===0){if(rgb[c]>limit)feasible=false;continue;}
        const a=-rgb[c]/delta,z=(limit-rgb[c])/delta;
        lower=Math.max(lower,Math.min(a,z));upper=Math.min(upper,Math.max(a,z));
      }
      if(!feasible || !Number.isFinite(lower) || !Number.isFinite(upper) || lower>=upper)continue;
      rgb.forEach((v,c)=>data.add(c*8).writeDouble(v));
      uncorrected.forEach((v,c)=>resultData.add(c*8).writeDouble(v));
      send({kind:'gamutCaseStart',name,rgb,uncorrected,centre,feasibleInterval:[lower,upper]});
      const rc=call(matrix,input,output);
      rows.push({name,rgb,coefficients:values,uncorrected,rc,output:[0,1,2].map(c=>resultData.add(c*8).readDouble())});
    }
  }
  return {cameraAccess:false,mlibPath:mlib.path,rows};
};

rpc.exports.curves = function(cases,negativeSubsample) {
  const compiler = Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'), 'uint32', [])();
  const mlib = Process.getModuleByName('MLib.dll');
  const adapter = Memory.alloc(Process.pageSize), address = mlib.base.add(0x1dd50).toUInt32();
  // cdecl(pointer,double) -> ECX + XMM1; return XMM0 through x87 ST0.
  adapter.writeByteArray([0x55,0x8b,0xec,0x8b,0x4d,0x08,0xf2,0x0f,0x10,0x4d,0x0c,0xb8,
    address&255,(address>>>8)&255,(address>>>16)&255,(address>>>24)&255,0xff,0xd0,
    0x83,0xec,0x08,0xf2,0x0f,0x11,0x04,0x24,0xdd,0x04,0x24,0x83,0xc4,0x08,0x5d,0xc3]);
  Memory.protect(adapter, Process.pageSize, 'r-x');
  const call = new NativeFunction(adapter, 'double', ['pointer','double'], 'mscdecl');
  const rows = [];
  for (const item of cases) {
    if (item.domainSize < 2 || item.domainSize > 512 || item.pairsHex.length !== item.domainSize*16*2) throw new Error('Invalid curve capture');
    const data = Memory.alloc(item.domainSize*16), curve = Memory.alloc(40);
    data.writeByteArray(item.pairsHex.match(/../g).map(v => parseInt(v,16)));
    curve.writeByteArray(new Uint8Array(40)); curve.add(0x20).writePointer(data); curve.add(0x24).writeU32(item.domainSize);
    const positions = [0,0.0001,0.02,0.13,0.25,0.3333333333333333,0.5,0.67,0.83,0.9999,1,1.1];
    if(negativeSubsample)for(const fraction of [.000001,.1,.5,.999999])positions.push(-fraction/(item.domainSize-1));
    for (const position of positions) rows.push({domainSize: item.domainSize, pairsHex: item.pairsHex,
      position, value: call(curve,position)});
  }
  return {mlibPath: mlib.path, cameraAccess: false, rows};
};
