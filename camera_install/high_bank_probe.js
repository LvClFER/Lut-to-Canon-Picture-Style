'use strict';
// Own hidden laboratory host only. No EDSDK, serialization or compiler patch.
// EXPERIMENT is injected by the hash-checking research driver.
rpc.exports.loadcompiler = function(path) { Module.load(path); return true; };
rpc.exports.compile = function(source,idHex,descriptorHex) {
  const module=Process.getModuleByName('EdsCFParse.dll');
  const api=(name,args)=>new NativeFunction(module.getExportByName(name),'uint32',args);
  const init=api('EdsCfpInitialize',[]);
  const create=api('EdsCfpCreateRef',['pointer','uint32','uint32','pointer']);
  const set=api('EdsCfpSetPropertyData',['pointer','uint32','uint32','uint32','pointer']);
  const sizeOf=api('EdsCfpGetPropertySize',['pointer','uint32','uint32','pointer','pointer']);
  const get=api('EdsCfpGetPropertyData',['pointer','uint32','uint32','uint32','pointer']);
  const release=api('EdsCfpRelease',['pointer']);
  const bytes=hex=>Uint8Array.from(hex.match(/../g)||[],v=>parseInt(v,16));
  const hex=(p,n)=>Array.from(new Uint8Array(p.readByteArray(n)),v=>v.toString(16).padStart(2,'0')).join('');
  const report={cameraAccess:false,compilerPatched:false,mutation:EXPERIMENT.mutation};
  const hooks=[];
  let observing=false;
  let observationStage='compile';
  if(EXPERIMENT.traceSelection) {
    report.basicReads=[];
    report.recordLookups={};report.inputRecordLookups={};report.builders=[];report.consumedRecords=[];report.familyClassifications=[];
    hooks.push(Interceptor.attach(module.base.add(0x4eaf0),{
      onEnter(){if(observing)this.caller=this.returnAddress.sub(module.base).toString();},
      onLeave(value){
        if(!this.caller)return;
        const item={stage:observationStage,callerRva:this.caller,value:value.toUInt32()};
        if(!report.familyClassifications.some(row=>row.stage===item.stage&&row.callerRva===item.callerRva&&row.value===item.value))
          report.familyClassifications.push(item);
      }
    }));
    report.descriptorGates=[];
    report.descriptorCopies=[];
    report.descriptorReaderCalls=[];
    report.descriptorNodeReads=[];
    report.descriptorImports=[];
    report.modernDescriptorSources=[];
    report.compactDescriptorSources=[];
    report.modernDescriptorMatrices=[];
    report.descriptorFourPointPreparations=[];
    report.mlibPreparationCalls=[];
    hooks.push(Interceptor.attach(module.base.add(0x46a30),{
      onEnter(args){
        if(observing&&report.mlibPreparationCalls.length<32){
          const item={stage:observationStage,callerRva:this.returnAddress.sub(module.base).toString(),
            mode:args[4].toUInt32(),splitCount:args[5].toUInt32(),
            axisNull:args[6].isNull(),fourPointNull:args[7].isNull()};
          try{if(!args[9].isNull())item.outputNodes=args[9].add(4).readU32();}catch(_){item.outputHeaderUnreadable=true;}
          report.mlibPreparationCalls.push(item);
        }
        if(!observing||!this.returnAddress.equals(module.base.add(0x48ce5))||
            report.descriptorFourPointPreparations.length>=16)return;
        const pointer=args[7],count=pointer.add(4).readU32();
        if(count>8)return;
        report.descriptorFourPointPreparations.push({stage:observationStage,
          index:args[4].toUInt32(),kind:pointer.readU32(),count:count,
          initializedHex:hex(pointer,8+count*68)});
      }
    }));
    hooks.push(Interceptor.attach(module.base.add(0x51760),{
      onEnter(args){
        if(observing&&report.compactDescriptorSources.length<4)
          report.compactDescriptorSources.push({stage:observationStage,
            length:7492,dataHex:hex(args[0],7492)});
      }
    }));
    hooks.push(Interceptor.attach(module.base.add(0x51b90),{
      onEnter(args){
        if(observing&&report.modernDescriptorSources.length<4)
          report.modernDescriptorSources.push({stage:observationStage,
            length:14796,dataHex:hex(args[0],14796)});
      }
    }));
    hooks.push(Interceptor.attach(module.base.add(0x51500),{
      onEnter(args){
        if(!observing||args[0].toUInt32()!==0x210||report.descriptorImports.length>=8)return;
        const length=args[1].toUInt32();
        if(![7492,14796].includes(length))return;
        report.descriptorImports.push({stage:observationStage,
          callerRva:this.returnAddress.sub(module.base).toString(),length:length,
          dataHex:hex(args[2],length)});
      }
    }));
    hooks.push(Interceptor.attach(module.base.add(0x46de0),{
      onEnter(args){
        const caller=this.returnAddress.sub(module.base).toUInt32();
        if(!observing||![0x47272,0x472b2].includes(caller)||report.descriptorNodeReads.length>=64)return;
        const node=this.context.ecx;
        this.nodeRead={stage:observationStage,callerRva:'0x'+caller.toString(16),
          storageType:node.add(8).readU32(),storedLength:node.add(12).readU32(),
          requestedLength:args[1].toUInt32(),endianMode:args[2].toUInt32()};
        report.descriptorNodeReads.push(this.nodeRead);
      },
      onLeave(value){if(this.nodeRead)this.nodeRead.succeeded=(value.toUInt32()&255)!==0;}
    }));
    report.contextDispatch=[];
    report.formatConstructors=[];
    for(const [name,rva] of [['baseFormatContext',0x53290],['pf3FormatContext',0x53f70]]) {
      hooks.push(Interceptor.attach(module.base.add(rva),{
        onEnter(args){
          if(report.formatConstructors.length>=32)return;
          report.formatConstructors.push({name:name,version:args[1].toUInt32(),
            callerRva:this.returnAddress.sub(module.base).toString(),stage:observationStage});
        }
      }));
    }
    // Known-revision read-only observers: distinguish base and PF3 contexts.
    // Caller compile_stock verifies the exact DLL hash before this agent runs.
    for(const [name,rva] of [['baseOutput',0x4f2d0],['pf3Output',0x54cd0],
                            ['baseFull33Reflect',0x49420],['baseFull33Builder',0x49b50],
                            ['pf3Full33Builder',0x4dac0],['modern17OutputPrepare',0x492a0],
                            ['modern17DescriptorParameters',0x48a30],['compactTailPrepare',0x49830]]) {
      hooks.push(Interceptor.attach(module.base.add(rva),{
        onEnter(){
          if(!observing||report.contextDispatch.length>=64)return;
          this.item={name:name,stage:observationStage,callerRva:this.returnAddress.sub(module.base).toString()};
          report.contextDispatch.push(this.item);
        },
        onLeave(value){if(this.item)this.item.returnLowByte=value.toUInt32()&255;}
      }));
    }
    let activeDescriptorGate=null;
    hooks.push(Interceptor.attach(module.base.add(0x472d0),{
      onLeave(value){if(activeDescriptorGate)activeDescriptorGate.styleOrdinal=value.toUInt32();}
    }));
    for(const [rva,length,stride] of [[0x47250,0x1d44,0x5d8],[0x47290,0x39cc,0x9a0]]) {
      hooks.push(Interceptor.attach(module.base.add(rva),{
        onEnter(args){
          if(observing&&report.descriptorReaderCalls.length<64){
            this.reader={stage:observationStage,readerRva:'0x'+rva.toString(16),requestedLength:length,
              callerRva:this.returnAddress.sub(module.base).toString()};
            report.descriptorReaderCalls.push(this.reader);
          }
          if(activeDescriptorGate){this.gate=activeDescriptorGate;this.buffer=args[0];}
        },
        onLeave(value){
          if(this.reader)this.reader.succeeded=(value.toUInt32()&255)!==0;
          if(!this.gate)return;
          this.gate.descriptorReaderRva='0x'+rva.toString(16);
          this.gate.descriptorCopySucceeded=(value.toUInt32()&255)!==0;
          if(!this.gate.descriptorCopySucceeded)return;
          const copied=hex(this.buffer,length);
          let copyIndex=report.descriptorCopies.findIndex(row=>row.length===length&&row.dataHex===copied);
          if(copyIndex<0&&report.descriptorCopies.length<8){
            copyIndex=report.descriptorCopies.length;
            report.descriptorCopies.push({readerRva:'0x'+rva.toString(16),length:length,dataHex:copied});
          }
          if(copyIndex>=0)this.gate.descriptorCopyIndex=copyIndex;
          const ordinal=this.gate.styleOrdinal,index=this.gate.index;
          if(ordinal===undefined||ordinal>5||index>2)return;
          const offset=0x1ee+ordinal*stride+index*2;
          if(offset+2>length)return;
          this.gate.descriptorFlagOffset=offset;
          this.gate.descriptorFlagWord=this.buffer.add(offset).readU16();
        }
      }));
    }
    hooks.push(Interceptor.attach(module.base.add(0x4b4f0),{
      onEnter(args){
        if(!observing||report.descriptorGates.length>=32)return;
        this.item={stage:observationStage,index:args[0].toUInt32(),callerRva:this.returnAddress.sub(module.base).toString()};
        activeDescriptorGate=this.item;
        report.descriptorGates.push(this.item);
      },
      onLeave(value){if(this.item){this.item.enabled=(value.toUInt32()&255)!==0;if(activeDescriptorGate===this.item)activeDescriptorGate=null;}}
    }));
    hooks.push(Interceptor.attach(module.base.add(0x4ef20),{
      onEnter(args) {
        if(!observing||report.basicReads.length>=64)return;
        const property=args[0].toUInt32(),length=args[1].toUInt32();
        if(property<0x1030||property>0x1035||length!==4)return;
        this.item={stage:observationStage,property:property.toString(16),length:length,
          callerRva:this.returnAddress.sub(module.base).toString()};this.buffer=args[2];
      },
      onLeave(value) {
        if(!this.item)return;
        this.item.rc=value.toUInt32();
        if(this.item.rc===0)this.item.dataHex=hex(this.buffer,4);
        report.basicReads.push(this.item);
      }
    }));
    hooks.push(Interceptor.attach(module.base.add(0x4ef20),{
      onEnter(args) {
        if(!observing)return;
        const property=args[0].toUInt32(),length=args[1].toUInt32();
        if(![0x1022,0x102a,0x1f00,0x1f01,0x1f02,0x1f03,0x1f04].includes(property)||length>215628||report.consumedRecords.length>=32)return;
        this.item={stage:observationStage,property:property.toString(16),length:length,
          callerRva:this.returnAddress.sub(module.base).toString()};this.buffer=args[2];
      },
      onLeave(value) {
        if(!this.item)return;
        this.item.rc=value.toUInt32();
        if(this.item.rc===0&&this.item.length>0)this.item.dataHex=hex(this.buffer,this.item.length);
        report.consumedRecords.push(this.item);
      }
    }));
    for(const rva of [0x46c10,0x4e160]) {
      hooks.push(Interceptor.attach(module.base.add(rva),{
        onEnter(args) {
          if(!observing)return;
          const id=args[0].toUInt32();
          if(id<0x1000||id>0x90ff)return;
          const key=id.toString(16);
          const collection=observationStage==='inputs'?report.inputRecordLookups:report.recordLookups;
          const row=collection[key]||(collection[key]={count:0,callers:[],nodeSizes:[]});
          row.count++;
          const caller=this.returnAddress.sub(module.base).toString();
          if(!row.callers.includes(caller)&&row.callers.length<16)row.callers.push(caller);
          this.row=row;
        },
        onLeave(value) {
          if(!this.row||value.isNull())return;
          try {const size=value.add(12).readU32();if(!this.row.nodeSizes.includes(size))this.row.nodeSizes.push(size);}
          catch(error){this.row.metadataReadError=String(error);}
        }
      }));
    }
    for(const [name,pattern,adjustment] of [
      ['dense17','c7 07 03 00 00 00 50 56 8b cb c7 47 04 11 00 00 00 c7 47 08 98 cc 01 00 c7 47 0c 02 00 00 00',-0xc2],
      ['dense10','55 8b ec b8 10 58 00 00 e8 ?? ?? ?? ?? a1 ?? ?? ?? ?? 33 c5 89 45 fc 53 8b 5d 0c 56 57 8b f1',0],
      ['readDense','55 8b ec 33 c0 83 7d 08 01 53 0f 95 c0 57 05 70 10 00 00 50 e8 ?? ?? ?? ?? 8b f8 85 ff 74 39',0]
      ,['convertDense','55 8b ec b8 d0 4c 00 00 e8 ?? ?? ?? ?? a1 ?? ?? ?? ?? 33 c5 89 45 fc 53 56 57 8b f1 c7 85 30 b3 ff ff 00 00 00 00',0]
    ]) {
      const hits=Memory.scanSync(module.base,module.size,pattern);
      if(hits.length!==1)throw new Error('Ambiguous observer signature '+name);
      hooks.push(Interceptor.attach(hits[0].address.add(adjustment),{
        onEnter(args) {
          if(!observing||report.builders.length>=64)return;
          this.item={name:name,stage:observationStage,index:name==='convertDense'?null:args[0].toUInt32(),callerRva:this.returnAddress.sub(module.base).toString()};
          report.builders.push(this.item);
        },
        onLeave(value){if(this.item){this.item.returnValue=value.toUInt32();this.item.booleanLowByte=value.toUInt32()&255;}}
      }));
    }
  }
  function open(path) {
    const out=Memory.alloc(Process.pointerSize);out.writePointer(ptr(0));
    const previousStage=observationStage;observationStage='reference-open';
    let rc;
    try {rc=create(Memory.allocAnsiString(path),2,0,out);}
    finally {observationStage=previousStage;}
    if(rc!==0||out.readPointer().isNull())throw new Error('Read-only reference open failed '+rc);
    return out.readPointer();
  }
  function read(ref,property) {
    const type=Memory.alloc(4),size=Memory.alloc(4);type.writeU32(0);size.writeU32(0);
    const rcSize=sizeOf(ref,property,0,type,size),length=size.readU32();
    const item={rcSize:rcSize,type:type.readU32(),length:length};
    if(rcSize===0&&length>0&&length<=1048576) {
      const buffer=Memory.alloc(length);item.rcGet=get(ref,property,0,length,buffer);
      if(item.rcGet===0){item.dataHex=hex(buffer,length);item.buffer=buffer;}
    }
    return item;
  }
  function snapshot(ref) {
    const result={};
    // 0x115/0x8115 here are PF3-reference aggregates, never EDSDK state.
    for(const property of [0x115,0x8115,0x114,0x8114,
      0x40001011,0x40009011,0x40001032,0x40009032,0x40001022,0x4000102a,
      0x40001070,0x40001071]) {
      const item=read(ref,property);delete item.buffer;result[property.toString(16)]=item;
    }
    return result;
  }
  report.rcInitialize=init();
  const ref=open(source);report.rcCreate=0;
  try {
    report.before=snapshot(ref);
    if(EXPERIMENT.mutation==='grid1070'||EXPERIMENT.mutation==='grid1071') {
      const donor=open(EXPERIMENT.donor);
      try {
        const property=EXPERIMENT.mutation==='grid1070'?0x40001070:0x40001071;
        const value=read(donor,property);
        if(value.rcGet!==0||value.length!==215628)throw new Error('Unexpected donor grid');
        report.rcMutation=set(ref,property,0,value.length,value.buffer);
      } finally {release(donor);}
    } else if(['bank9011zero','bank9011one','bank9032two','active1032two','active1011one'].includes(EXPERIMENT.mutation)) {
      const settings={bank9011zero:[0x40009011,0],bank9011one:[0x40009011,1],
        bank9032two:[0x40009032,2],active1032two:[0x40001032,2],active1011one:[0x40001011,1]};
      const [property,number]=settings[EXPERIMENT.mutation];
      const value=Memory.alloc(4);value.writeU32(number);
      report.rcMutation=set(ref,property,0,4,value);
    } else if(EXPERIMENT.mutation!=='control')throw new Error('Unknown bounded mutation');
    if(report.rcMutation!==undefined&&report.rcMutation!==0)throw new Error('Mutation rejected '+report.rcMutation);
    report.afterMutation=snapshot(ref);
    observing=true;observationStage='inputs';
    for(const [name,property,value] of [['rcId',0x01000001,bytes(idHex)],['rcDescriptor',0x01000210,bytes(descriptorHex)]]) {
      const buffer=Memory.alloc(value.length);buffer.writeByteArray(value);
      report[name]=set(ref,property,0,value.length,buffer);
    }
    observing=false;
    report.afterInputs=snapshot(ref);
    observing=true;observationStage='compile';
    const output=read(ref,0x01000203);
    observing=false;
    report.afterCompile=snapshot(ref);
    report.rcSize=output.rcSize;report.rcGet=output.rcGet;report.outputSize=output.length;
    if(output.dataHex)report.outputHex=output.dataHex;
    return report;
  } finally {observing=false;release(ref);for(const hook of hooks)hook.detach();}
};
