'use strict';
rpc.exports.loadcompiler = function(path) { Module.load(path); return true; };
rpc.exports.compile = function(source,idHex,descriptorHex) {
  const module=Process.getModuleByName('EdsCFParse.dll');
  const api=(name,args)=>new NativeFunction(module.getExportByName(name),'uint32',args);
  const init=api('EdsCfpInitialize',[]);
  const create=api('EdsCfpCreateRef',['pointer','uint32','uint32','pointer']);
  const set=api('EdsCfpSetPropertyData',['pointer','uint32','uint32','uint32','pointer']);
  const sizeOf=api('EdsCfpGetPropertySize',['pointer','uint32','uint32','pointer','pointer']);
  const get=api('EdsCfpGetPropertyData',['pointer','uint32','uint32','uint32','pointer']);
  const reflect=api('EdsCfpReflectProperty',['pointer']);
  const release=api('EdsCfpRelease',['pointer']);
  const bytes=hex=>Uint8Array.from(hex.match(/../g)||[],v=>parseInt(v,16));
  const hex=(p,n)=>Array.from(new Uint8Array(p.readByteArray(n)),v=>v.toString(16).padStart(2,'0')).join('');
  const out=Memory.alloc(Process.pointerSize);out.writePointer(ptr(0));
  const report={cameraAccess:false,exportedApisOnly:true,nodeCreations:[]};
  const factoryHook=Interceptor.attach(module.base.add(0x4dee0),{
    onEnter(args) {
      const property=args[0].toUInt32();
      if(![0x1007,0x1022,0x102a].includes(property)||report.nodeCreations.length>=64)return;
      this.item={property:property,callerRva:this.returnAddress.sub(module.base).toString()};
      report.nodeCreations.push(this.item);
    },
    onLeave(value) {
      if(!this.item)return;
      this.item.created=!value.isNull();
      if(!value.isNull()) {
        try {this.item.storedType=value.add(8).readU32();this.item.storedSize=value.add(12).readU32();}
        catch(error){this.item.metadataError=String(error);}
      }
    }
  });
  report.rcInitialize=init();
  report.rcCreate=create(Memory.allocAnsiString(source),2,0,out);
  const ref=out.readPointer();
  if(report.rcCreate!==0||ref.isNull()){factoryHook.detach();return report;}
  function propertyState(stage) {
    return {stage:stage,properties:[0x40001007,0x40001022,0x4000102a].map(property=>{
      const type=Memory.alloc(4),size=Memory.alloc(4);type.writeU32(0);size.writeU32(0);
      return {property:property,rcSize:sizeOf(ref,property,0,type,size),size:size.readU32(),type:type.readU32()};
    })};
  }
  try {
    report.stages=[propertyState('opened')];
    for(const [name,property,value] of [['rcId',0x01000001,bytes(idHex)],['rcDescriptor',0x01000210,bytes(descriptorHex)]]) {
      const buffer=Memory.alloc(value.length);buffer.writeByteArray(value);
      report[name]=set(ref,property,0,value.length,buffer);
    }
    report.stages.push(propertyState('after-inputs'));
    report.rcReflect=reflect(ref);
    report.stages.push(propertyState('after-reflect'));
    const type=Memory.alloc(4),size=Memory.alloc(4);type.writeU32(0);size.writeU32(0);
    report.rcSize=sizeOf(ref,0x01000203,0,type,size);report.outputSize=size.readU32();
    if(report.rcSize===0&&report.outputSize>0&&report.outputSize<=1048576) {
      const buffer=Memory.alloc(report.outputSize);buffer.writeByteArray(new Uint8Array(report.outputSize));
      report.rcGet=get(ref,0x01000203,0,report.outputSize,buffer);
      if(report.rcGet===0)report.outputHex=hex(buffer,report.outputSize);
    }
    report.stages.push(propertyState('after-compile'));
    return report;
  } finally {release(ref);factoryHook.detach();}
};
