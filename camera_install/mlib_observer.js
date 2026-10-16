'use strict';
// Read-only observer in an isolated x86 compiler host. Never loaded into EOS Utility.
const captures = [];
const hooks = [];
const counts = {};
const curvesSeen = new Set();
const curveItems = new Map();
const callerNames = new Map();
const normalizedSeen = new Set();
const finalizedSeen = new Set();
let polynomialPhase = 0;
let polynomialPhaseIndex = 0;
let watchedPixel = null;
  function read(pointer, size) {
  if (pointer.isNull()) return null;
  try {
    const bytes = new Uint8Array(pointer.readByteArray(size));
    return Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('');
  } catch (_) { return null; }
}
rpc.exports.start = function(observeColor, observeDense, packingOnly) {
  const compiler = Process.getModuleByName('EdsCFParse.dll');
  new NativeFunction(compiler.getExportByName('EdsCfpInitialize'), 'uint32', [])();
  const mlib = Process.getModuleByName('MLib.dll');
  if (observeDense) {
    const iccColorGrids=[];
    const iccPolynomialGrids=[];
    hooks.push(Interceptor.attach(mlib.base.add(0x1d380), {
      onEnter(args) {
        if (!this.returnAddress.equals(mlib.base.add(0x5176))) return;
        const index=counts.iccPolynomialNodes || 0;
        counts.iccPolynomialNodes=index+1;
        if (index>=2*33**3) return;
        const node=index % (33**3),profileIndex=Math.floor(index/(33**3));
        const matrix=this.context.ecx,vector=this.context.edx;
        if (node===0) {
          const record={functionRva:'0x1d380ICCGrid',ownerModule:'MLib.dll',callerRva:'0x5176',
            profileIndex,nodes:33**3,completedNodes:0,failedCalls:0,
            coefficientsFloat64Hex:read(matrix.readPointer(),57*8)};
          iccPolynomialGrids.push({record,input:Memory.alloc(33**3*24),output:Memory.alloc(33**3*24)});
          captures.push(record);
        }
        this.iccPolynomialGrid=iccPolynomialGrids[profileIndex];this.iccPolynomialNode=node;
        this.iccPolynomialDestination=args[0];
        Memory.copy(this.iccPolynomialGrid.input.add(node*24),vector.readPointer(),24);
      },
      onLeave(result) {
        if (!this.iccPolynomialGrid) return;
        const grid=this.iccPolynomialGrid,node=this.iccPolynomialNode;
        Memory.copy(grid.output.add(node*24),this.iccPolynomialDestination.readPointer(),24);
        grid.record.completedNodes++;
        if (result.toUInt32()!==0)grid.record.failedCalls++;
        if (node===33**3-1) {
          grid.record.inputDoublesHex=read(grid.input,33**3*24);
          grid.record.outputDoublesHex=read(grid.output,33**3*24);
        }
      }
    }));
    hooks.push(Interceptor.attach(mlib.base.add(0x1000), {
      onEnter() {
        if (!this.returnAddress.equals(mlib.base.add(0x52fb))) return;
        const index=counts.iccColorNodes || 0;
        counts.iccColorNodes=index+1;
        const node=index % (33**3);
        if (index >= 2*33**3) return;
        const stack=this.context.esp;
        this.iccXYZDest=[this.context.ecx,this.context.edx,stack.add(4).readPointer()];
        const profileIndex=Math.floor(index/(33**3));
        if (node===0) {
          const record={functionRva:'0x1000ICCGrid',ownerModule:'MLib.dll',callerRva:'0x52fb',
            profileIndex,nodes:33**3,completedNodes:0,mode:stack.add(8).readU32(),modeChanged:false,failedCalls:0};
          iccColorGrids.push({record,rgb:Memory.alloc(33**3*24),xyz:Memory.alloc(33**3*24)});
          captures.push(record);
        }
        this.iccFullGrid=iccColorGrids[profileIndex];this.iccFullNode=node;
        if (this.iccFullGrid.record.mode!==stack.add(8).readU32())this.iccFullGrid.record.modeChanged=true;
        Memory.copy(this.iccFullGrid.rgb.add(node*24),stack.add(12),24);
        if (![0,1,32,33,1088,1089,17968,35936].includes(node)) return;
        this.iccXYZ={functionRva:'0x1000ICCColor',ownerModule:'MLib.dll',callerRva:'0x52fb',
          profileIndex:Math.floor(index/(33**3)),nodeIndex:node,mode:stack.add(8).readU32(),
          rgb:[stack.add(12).readDouble(),stack.add(20).readDouble(),stack.add(28).readDouble()]};
        captures.push(this.iccXYZ);
      },
      onLeave(result) {
        if (this.iccFullGrid) {
          const grid=this.iccFullGrid,node=this.iccFullNode;
          this.iccXYZDest.forEach((p,c)=>grid.xyz.add(node*24+c*8).writeDouble(p.readDouble()));
          grid.record.completedNodes++;
          if (result.toUInt32()!==0)grid.record.failedCalls++;
          if (node===33**3-1) {
            grid.record.rgbDoublesHex=read(grid.rgb,33**3*24);
            grid.record.xyzDoublesHex=read(grid.xyz,33**3*24);
          }
        }
        if (!this.iccXYZ) return;
        this.iccXYZ.xyz=this.iccXYZDest.map(p=>p.readDouble());
        this.iccXYZ.rc=result.toUInt32();
      }
    }));
    hooks.push(Interceptor.attach(mlib.base.add(0x2590), {
      onEnter() {
        counts.iccLabWriter=(counts.iccLabWriter || 0)+1;
        if (counts.iccLabWriter > 2) return;
        const source=this.context.ecx;
        const depth=source.readU32(),grid=source.add(4).readU32();
        const inputs=source.add(8).readU32(),outputs=source.add(12).readU32();
        if (depth !== 16 || grid !== 33 || inputs !== 3 || outputs !== 3) return;
        this.iccLabOutput=this.context.edx;
        this.iccLabRequired=44+inputs*16*2+grid**inputs*outputs*2+outputs*256*2;
        this.iccLab={functionRva:'0x2590LabWriter',ownerModule:'MLib.dll',
          callerRva:this.returnAddress.sub(mlib.base).toString(),depth,grid,inputs,outputs,
          labDoublesHex:read(source.add(16).readPointer(),grid**inputs*outputs*8),
          alignmentBeforeHex:read(this.iccLabOutput.add(this.iccLabRequired),2)};
        captures.push(this.iccLab);
      },
      onLeave() {
        if (!this.iccLab) return;
        // Writer starts after the eight-byte mft2 type/reserved envelope.
        this.iccLab.clutHex=read(this.iccLabOutput.add(44+this.iccLab.inputs*16*2),
          this.iccLab.grid**this.iccLab.inputs*this.iccLab.outputs*2);
        this.iccLab.alignmentAfterHex=read(this.iccLabOutput.add(this.iccLabRequired),2);
      }
    }));
    const iccTarget=compiler.base.add(0xd11e4).readPointer();
    const iccOwner=iccTarget.isNull() ? null : Process.findModuleByAddress(iccTarget);
    captures.push({functionRva:'0x46b80DynamicBinding',ownerModule:'EdsCFParse.dll',
      targetModule:iccOwner ? iccOwner.name : null,
      targetRva:iccOwner ? iccTarget.sub(iccOwner.base).toString() : null,
      targetExport:iccOwner ? (iccOwner.enumerateExports().find(e=>e.address.equals(iccTarget)) || {}).name || null : null});
    if (iccOwner && iccOwner.name === 'MLib.dll' && iccTarget.sub(iccOwner.base).toString() === '0x1b690') {
      hooks.push(Interceptor.attach(iccTarget, {
        onEnter(args) {
          counts.iccBuilder=(counts.iccBuilder || 0)+1;
          if (counts.iccBuilder > 4) return;
          this.iccBuild={functionRva:'0x1b690ICCBuilder',ownerModule:'MLib.dll',
            callerRva:this.returnAddress.sub(compiler.base).toString(),
            argument1:args[1].toUInt32(),argument2:args[2].toUInt32(),
            inputHeaderHex:read(args[0],64),inputModeZeroHex:args[0].readU32()===0 ? read(args[0],848) : null};
          captures.push(this.iccBuild);
        },
        onLeave(result) {
          if (!this.iccBuild) return;
          this.iccBuild.resultNull=result.isNull();
          if (result.isNull()) return;
          try {
            const output=result.readPointer(),size=result.add(4).readU32();
            this.iccBuild.resultSize=size;
            if (!output.isNull() && size >= 128 && size <= 1048576)
              this.iccBuild.profileHeaderHex=read(output,128);
          } catch (_) { this.iccBuild.resultLayoutReadable=false; }
        }
      }));
    }
    hooks.push(Interceptor.attach(compiler.base.add(0x494d0), {
      onEnter() {
        counts.legacyAliasPreparation=(counts.legacyAliasPreparation || 0)+1;
        if (counts.legacyAliasPreparation > 16) return;
        this.legacyPreparation={functionRva:'0x494d0',ownerModule:'EdsCFParse.dll',
          callerRva:this.returnAddress.sub(compiler.base).toString()};
        captures.push(this.legacyPreparation);
      },
      onLeave(result) {
        if (this.legacyPreparation) {
          this.legacyPreparation.returnValue=result.toUInt32();
          this.legacyPreparation.booleanLowByte=(result.toUInt32() & 255) !== 0;
        }
      }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x46be0), {
      onEnter() {
        counts.gridEngineConstructor=(counts.gridEngineConstructor || 0)+1;
        if (counts.gridEngineConstructor > 32) return;
        this.engine=this.context.ecx;
        this.constructor={functionRva:'0x46be0',ownerModule:'EdsCFParse.dll',
          callerRva:this.returnAddress.sub(compiler.base).toString()};
        captures.push(this.constructor);
      },
      onLeave() {
        if (this.constructor) this.constructor.initialFlagByte=this.engine.add(8).readU8();
      }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x4a2b0), {
      onEnter(args) {
        const property = args[0].toUInt32();
        if (![0x1004,0x1005,0x1007,0x1022,0x102a,0x1f00,0x1f01].includes(property)) return;
        counts.derivedRecordSetCalls = (counts.derivedRecordSetCalls || 0)+1;
        if (counts.derivedRecordSetCalls > 128) return;
        this.derivedSet = {functionRva:'0x4a2b0DerivedSet',ownerModule:'EdsCFParse.dll',
          property:'0x'+property.toString(16),inputSize:args[1].toUInt32(),
          callerRva:this.returnAddress.sub(compiler.base).toString()};
        if ((property === 0x1004 && this.derivedSet.inputSize === 300) ||
            (property === 0x1005 && this.derivedSet.inputSize === 240))
          this.derivedSet.inputHex = read(args[2], this.derivedSet.inputSize);
        captures.push(this.derivedSet);
      },
      onLeave(result) { if (this.derivedSet) this.derivedSet.rc = result.toUInt32(); }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x4a120), {
      onEnter(args) {
        const node = this.context.ecx;
        let property;
        try { property = node.add(4).readU32(); } catch (_) { return; }
        if (![0x1004,0x1005,0x1007,0x1022,0x102a,0x1f00,0x1f01].includes(property)) return;
        counts.derivedNodeDataWrites = (counts.derivedNodeDataWrites || 0)+1;
        if (counts.derivedNodeDataWrites > 128) return;
        this.nodeWrite = {functionRva:'0x4a120NodeDataWrite',ownerModule:'EdsCFParse.dll',
          property:'0x'+property.toString(16),inputSize:args[1].toUInt32(),
          storedType:node.add(8).readU32(),sizeConstraint:node.add(20).readU32(),
          callerRva:this.returnAddress.sub(compiler.base).toString()};
        captures.push(this.nodeWrite);
      },
      onLeave(result) { if (this.nodeWrite) this.nodeWrite.success = (result.toUInt32() & 255) !== 0; }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x46c10), {
      onEnter(args) {
        this.sourceProperty = args[0].toUInt32();
          this.sourceSelected = [0x1007,0x1022,0x102a,0x1070,0x1071].includes(this.sourceProperty);
      },
      onLeave(result) {
        if (!this.sourceSelected) return;
        counts.sourcePropertyMetadata = (counts.sourcePropertyMetadata || 0)+1;
        if (counts.sourcePropertyMetadata > 128) return;
        const item = {functionRva:'0x46c10SourceMetadata',ownerModule:'EdsCFParse.dll',
          property:'0x'+this.sourceProperty.toString(16),found:!result.isNull()};
        if (!result.isNull()) {
            try {
              item.storedType = result.add(8).readU32(); item.storedSize = result.add(12).readU32();
              if ([0x1070,0x1071].includes(this.sourceProperty) && item.storedSize === 215628) {
                item.denseRecordHex = read(result.add(16).readPointer(), item.storedSize);
              }
            }
          catch (_) { item.metadataReadable = false; }
        }
        captures.push(item);
      }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x51500), {
      onEnter(args) {
        const property = args[0].toUInt32();
        if (![0x1004,0x1005,0x1007,0x1022,0x102a,0x1f00,0x1f01].includes(property)) return;
        counts.legacyRecordWrites = (counts.legacyRecordWrites || 0)+1;
        if (counts.legacyRecordWrites > 128) return;
        this.writeItem = {functionRva:'0x51500RecordWrite',ownerModule:'EdsCFParse.dll',
          property:'0x'+property.toString(16),size:args[1].toUInt32(),
          nullData:args[2].isNull(),endianArgument:args[3].toUInt32(),
          callerRva:this.returnAddress.sub(compiler.base).toString()};
        captures.push(this.writeItem);
      },
      onLeave(result) { if (this.writeItem) this.writeItem.rc = result.toUInt32(); }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x4e160), {
      onEnter(args) {
        this.lookupProperty = args[0].toUInt32();
        this.lookupCaller = this.returnAddress.sub(compiler.base).toString();
      },
      onLeave(result) {
        if (this.lookupCaller !== '0x4ef31') return;
        counts.rawPropertyMetadata = (counts.rawPropertyMetadata || 0)+1;
        if (counts.rawPropertyMetadata > 256) return;
        const item = {functionRva:'0x4e160Metadata',ownerModule:'EdsCFParse.dll',
          property:'0x'+this.lookupProperty.toString(16),found:!result.isNull()};
        if (!result.isNull()) {
          try {
            item.storedType = result.add(8).readU32();
            item.storedSize = result.add(12).readU32();
          } catch (_) { item.metadataReadable = false; }
        }
        captures.push(item);
      }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x4ef20), {
      onEnter(args) {
        const property = args[0].toUInt32();
        const size = args[1].toUInt32();
        counts.rawPropertyReads = (counts.rawPropertyReads || 0)+1;
        if (counts.rawPropertyReads <= 256) {
          this.rawOutput = args[2]; this.rawLength = size;
          this.rawItem = {functionRva:'0x4ef20Raw',ownerModule:'EdsCFParse.dll',
            property:'0x'+property.toString(16),size:size,
            callerRva:this.returnAddress.sub(compiler.base).toString()};
          captures.push(this.rawItem);
        }
        if (!(property >= 0x1030 && property <= 0x1035 || [0x100c,0x1011,0x1012,0x1080].includes(property)) || ![2,4].includes(size)) return;
        counts.basicAuxiliaryRawReads = (counts.basicAuxiliaryRawReads || 0)+1;
        if (counts.basicAuxiliaryRawReads > 256) return;
        this.output = args[2]; this.length = size;
        this.item = {functionRva:'0x4ef20',ownerModule:'EdsCFParse.dll',
          property:'0x'+property.toString(16),size:size,endianArgument:args[3].toUInt32(),
          callerRva:this.returnAddress.sub(compiler.base).toString()};
        captures.push(this.item);
      },
      onLeave(result) {
        if (this.rawItem) {
          this.rawItem.rc = result.toUInt32();
          if (this.rawItem.rc === 0 && this.rawLength > 0 && this.rawLength <= 32)
            this.rawItem.rawValueHex = read(this.rawOutput,this.rawLength);
          if (this.rawItem.rc === 0 && this.rawLength === 4096 &&
              ['0x1022','0x102a','0x1f00','0x1f01'].includes(this.rawItem.property))
            this.rawItem.rawValueHex = read(this.rawOutput,this.rawLength);
        }
        if (!this.item) return;
        this.item.rc = result.toUInt32();
        if (this.item.rc === 0) this.item.rawValueHex = read(this.output,this.length);
      }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x4ef70), {
      onEnter(args) {
        const property = args[0].toUInt32();
        if (property < 0x40001030 || property > 0x40001035 || args[2].toUInt32() !== 4) return;
        counts.basicScalarReads = (counts.basicScalarReads || 0)+1;
        if (counts.basicScalarReads > 64) return;
        this.output = args[3];
        this.item = {functionRva:'0x4ef70',ownerModule:'EdsCFParse.dll',
          property:'0x'+property.toString(16),callerRva:this.returnAddress.sub(compiler.base).toString()};
        captures.push(this.item);
      },
      onLeave(result) {
        if (!this.item) return;
        this.item.rc = result.toUInt32();
        if (this.item.rc === 0 && !this.output.isNull()) this.item.signedValue = this.output.readS32();
      }
    }));
    let currentIntegerConversion = null;
    hooks.push(Interceptor.attach(compiler.base.add(0x475c0), {
      onEnter(args) {
        counts.compactPixelGrid = (counts.compactPixelGrid || 0)+1;
        if (counts.compactPixelGrid > 8) return;
        this.destination=args[1];
        this.grid={functionRva:'0x475c0',ownerModule:'EdsCFParse.dll',
          callerRva:this.returnAddress.sub(compiler.base).toString(),
          inputHeaderHex:read(args[0],16),
          inputPlanarFloat64Hex:read(args[0].add(16),24000)};
        captures.push(this.grid);
      },
      onLeave() {
        if (this.grid) this.grid.outputPlanarInt32Hex=read(this.destination.add(12),12000);
      }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x4a3b0), {
      onEnter(args) {
        counts.integerGridConversion = (counts.integerGridConversion || 0)+1;
        if (counts.integerGridConversion > 8) return;
        this.destination = args[2];
        this.conversion = {functionRva:'0x4a3b0',ownerModule:'EdsCFParse.dll',
          callerRva:this.returnAddress.sub(compiler.base).toString(),
          inputPlanarFloat64Hex:read(args[0],24000),
          tablePlanarInt32Hex:read(args[1],12000),
          roundingConstantHex:read(compiler.base.add(0xbb668),8),
          upperBoundConstantHex:read(compiler.base.add(0xbb6e8),8)};
        currentIntegerConversion = this.conversion;
        captures.push(this.conversion);
      },
      onLeave() {
        if (this.conversion) {
          this.conversion.outputPlanarInt32Hex=read(this.destination.add(12),12000);
          currentIntegerConversion=null;
        }
      }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x47af0), {
      onEnter(args) {
        counts.integerTetrahedral = (counts.integerTetrahedral || 0)+1;
        if (counts.integerTetrahedral > 24) return;
        const table = read(args[6],12000);
        if (!table) return;
        this.outputs = [args[3],args[4],args[5]];
        this.item = {functionRva:'0x47af0',ownerModule:'EdsCFParse.dll',
          coordinates:[args[0].toInt32(),args[1].toInt32(),args[2].toInt32()],
          tablePlanarInt32Hex:table};
        captures.push(this.item);
      },
      onLeave() {
        if (this.item) this.item.output = this.outputs.map(p=>p.readS32());
      }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x49e00), {
      onEnter(args) {
        counts.packed10Integer = (counts.packed10Integer || 0)+1;
        if (counts.packed10Integer > 8) return;
        this.output = args[1];
        const input = read(args[0],3000*4);
        if (!input) return;
        this.item = {functionRva:'0x49e00',ownerModule:'EdsCFParse.dll',inputPlanarInt32Hex:input};
        this.item.callerRva=this.returnAddress.sub(compiler.base).toString();
        captures.push(this.item);
      },
      onLeave() {
        if (this.item) this.item.nativePackedHex = read(this.output,4096);
      }
    }));
    let currentCompactPack = null;
    hooks.push(Interceptor.attach(compiler.base.add(0x4b290), {
      onEnter() {
        const caller=this.returnAddress.sub(compiler.base).toString();
        if (!['0x4c82f','0x4d71f'].includes(caller)) return;
        this.branch={functionRva:'0x4b290Branch',callerRva:caller,
          objectFlagByte:this.context.ecx.add(8).readU8()};
        captures.push(this.branch);
      },
      onLeave(result) {
        if (this.branch) this.branch.coefficientMode=Boolean(result.toUInt32() & 255);
        if (currentCompactPack) currentCompactPack.coefficientMode = Boolean(result.toUInt32() & 255);
        if (currentIntegerConversion) currentIntegerConversion.coefficientMode = Boolean(result.toUInt32() & 255);
      }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x4b760), {
      onEnter(args) {
        counts.packed10 = (counts.packed10 || 0)+1;
        if (counts.packed10 > 8) return;
        this.output = args[1];
        const input = read(args[0],10**3*3*8);
        if (!input) return;
        this.item = {functionRva:'0x4b760',ownerModule:'EdsCFParse.dll',
          inputPlanarFloat64Hex:input};
        currentCompactPack = this.item;
        captures.push(this.item);
      },
      onLeave() {
        if (this.item) this.item.nativePackedHex = read(this.output,4096);
        currentCompactPack = null;
      }
    }));
    hooks.push(Interceptor.attach(compiler.base.add(0x4bb40), {
      onEnter(args) {
        counts.packed17 = (counts.packed17 || 0)+1;
        if (counts.packed17 > 8) return;
        this.output = args[1];
        const input = read(args[0],17**3*3*8);
        if (!input) return;
        this.item = {functionRva:'0x4bb40',ownerModule:'EdsCFParse.dll',
          tableIndex:args[2].toUInt32(),inputPlanarFloat64Hex:input};
        captures.push(this.item);
      },
      onLeave() {
        if (this.item) this.item.nativePackedHex = read(this.output,17**3*4);
      }
    }));
    if (packingOnly) return {mlibPath:mlib.path,mlibSize:mlib.size,packingOnly:true};
    const axisSamples = {};
    hooks.push(Interceptor.attach(mlib.base.add(0xfa40), {
      onEnter(args) {
        const index = axisSamples[polynomialPhase] = (axisSamples[polynomialPhase] || 0) + 1;
          if (index > 16 && ![1057,2113,2114].includes(index)) return;
        try {
          const parameters = args[0];
          if (parameters.readU32() !== 2 || parameters.add(4).readU32() !== 6) return;
          this.destination = args[2];
          this.item = {functionRva:'0xfa40',phase:polynomialPhase,callIndex:index,
            callerRva:this.returnAddress.sub(mlib.base).toString(),mode:this.context.edx.toUInt32(),
            parameters512Hex:read(parameters,512),
            input:[0,1,2].map(i=>this.context.ecx.add(i*8).readDouble())};
          captures.push(this.item);
        } catch (_) { return; }
      },
      onLeave() {
        if (this.item) this.item.output = [0,1,2].map(i=>this.destination.add(i*8).readDouble());
      }
    }));
    const curveSamples = {};
    hooks.push(Interceptor.attach(mlib.base.add(0x1dd50), {
      onEnter() {
        const index = curveSamples[polynomialPhase] = (curveSamples[polynomialPhase] || 0) + 1;
        if (index > 24) return;
        try {
          const curve = this.context.ecx, size = curve.add(0x24).readU32();
          if (size < 2 || size > 512 || curve.add(0x20).readPointer().isNull()) return;
          this.item = {functionRva:'0x1dd50',phase:polynomialPhase,callIndex:index,
            callerRva:this.returnAddress.sub(mlib.base).toString(),
            domainSize:size,
            pairsHex:read(curve.add(0x20).readPointer(),size*16)};
          captures.push(this.item);
        } catch (_) { return; }
      }
    }));
    const gamutSamples = {};
    hooks.push(Interceptor.attach(mlib.base.add(0xf730), {
      onEnter(args) {
        counts.gamut = (counts.gamut || 0) + 1;
        const index = gamutSamples[polynomialPhase] = (gamutSamples[polynomialPhase] || 0) + 1;
        if (index > 8 && ![17,113,521,1317].includes(index)) return;
        try {
          const vector = this.context.edx, destination = args[0];
          if (vector.add(4).readU32() !== 3 || destination.add(4).readU32() !== 3) return;
          this.destination = destination;
          this.item = {functionRva:'0xf730',phase:polynomialPhase,callIndex:index,
            input:[0,1,2].map(i=>vector.readPointer().add(i*8).readDouble()),
            before:[0,1,2].map(i=>destination.readPointer().add(i*8).readDouble())};
          captures.push(this.item);
        } catch (_) { return; }
      },
      onLeave(result) {
        if (!this.item) return;
        this.item.result = result.toUInt32();
        try { this.item.after = [0,1,2].map(i=>this.destination.readPointer().add(i*8).readDouble()); }
        catch (_) { this.item.outputCaptureFailed = true; }
      }
    }));
    hooks.push(Interceptor.attach(mlib.base.add(0x1d380), {
      onEnter(args) {
        counts.polynomial = (counts.polynomial || 0) + 1;
        const index = ++polynomialPhaseIndex;
        if (index > 8 && ![17,113,521,1317].includes(index)) return;
        try {
          const matrix = this.context.ecx, vector = this.context.edx;
          if (matrix.add(4).readU32() !== 3 || matrix.add(8).readU32() !== 3 || matrix.add(12).readU32() !== 3 || vector.add(4).readU32() !== 3) return;
          this.destination = args[0];
          this.item = {functionRva: '0x1d380', callIndex: index,
            phase: polynomialPhase,
            callerRva:this.returnAddress.sub(mlib.base).toString(),
            coefficientsFloat64Hex: read(matrix.readPointer(), 57*8),
            input: [0,1,2].map(i => vector.readPointer().add(i*8).readDouble())};
          captures.push(this.item);
        } catch (_) { return; }
      },
      onLeave(result) {
        if (!this.item) return;
        this.item.result = result.toUInt32();
        if (this.destination.add(4).readU32() === 3) this.item.output = [0,1,2].map(i =>
          this.destination.readPointer().add(i*8).readDouble());
      }
    }));
  }
  function parameterBlock(pointer) {
    try {
      if (pointer.isNull()) return null;
      const kind=pointer.readU32(),count=pointer.add(4).readU32();
      if (![1,2].includes(kind) || count>12) return null;
      if (!count) return {kind,count,bytes:8,initializedHex:read(pointer,8)};
      // fa40 computes the group stride from the first group's point count.
      const points=pointer.add(8).readU32();
      if (points>12) return null;
      const bytes=8+count*(4+points*16);
      return {kind,count,points,bytes,initializedHex:read(pointer,bytes)};
    } catch (_) { return null; }
  }
  if(observeDense) {
    // Read-only cdecl wrapper: three doubles, eight settings, three outputs.
    // Keep contexts once and bound samples; never retain heap addresses.
    const pixelContexts=new Map();
    for(const rva of [0xf070,0xee40])hooks.push(Interceptor.attach(mlib.base.add(rva),{
      onEnter(args){
        if(!watchedPixel)return;
        this.pixelStage={functionRva:'0x'+rva.toString(16),bits:this.context.ecx.toUInt32(),
          mode:this.context.edx.toUInt32(),input:[0,1,2].map(i=>args[i].toInt32())};
        this.pixelDestination=args[3];watchedPixel.stages.push(this.pixelStage);
      },
      onLeave(){if(this.pixelStage)this.pixelStage.output=[0,1,2].map(i=>this.pixelDestination.add(i*4).readS32());}
    }));
    hooks.push(Interceptor.attach(mlib.base.add(0xfa40),{
      onEnter(args){
        if(!watchedPixel)return;
        this.pixelStage={functionRva:'0xfa40',input:[0,1,2].map(i=>this.context.ecx.add(i*8).readDouble()),
          parameterBlock:parameterBlock(args[0]),nodes:args[1].toUInt32()};
        this.pixelDestination=args[2];watchedPixel.stages.push(this.pixelStage);
      },
      onLeave(){if(this.pixelStage)this.pixelStage.output=[0,1,2].map(i=>this.pixelDestination.add(i*8).readDouble());}
    }));
    hooks.push(Interceptor.attach(mlib.base.add(0x1cab0),{
      onEnter() {
        try {
          const stack=this.context.esp;
          const parameters=[28,32,36,40,56,52].map(o=>stack.add(o).readPointer());
          const mode=stack.add(44).readU32(),splitCount=stack.add(48).readU32();
          const key=parameters.map(p=>p.toString()).join(':')+':'+[mode,splitCount].join(':');
          let context=pixelContexts.get(key);
          if(!context) {
            if(pixelContexts.size>=12)return;
            const caller=Process.findModuleByAddress(this.returnAddress);
            context={functionRva:'0x1cab0',callerModule:caller?caller.name:null,
              callerRva:caller?this.returnAddress.sub(caller.base).toString():null,
              initializedArguments:{preCurvesHex:read(parameters[0],300),postCurvesHex:read(parameters[1],300),
                thirdCurvesHex:read(parameters[2],300),matrix240Hex:read(parameters[3],240),
                mode,splitCount,axisBlock:parameterBlock(parameters[5]),selectorBlock:parameterBlock(parameters[4])},
              observedCalls:0,samples:[]};
            pixelContexts.set(key,context);captures.push(context);
          }
          context.observedCalls++;
          if(context.samples.length>=1000)return;
          this.pixelOutputs=[60,64,68].map(o=>stack.add(o).readPointer());
          this.pixelSample={callIndex:context.observedCalls,input:[4,12,20].map(o=>stack.add(o).readDouble())};
          if(context.observedCalls==832){this.pixelSample.stages=[];watchedPixel=this.pixelSample;}
          context.samples.push(this.pixelSample);
        }catch(_){return;}
      },
      onLeave(){if(this.pixelSample){this.pixelSample.output=this.pixelOutputs.map(p=>p.readDouble());if(watchedPixel===this.pixelSample)watchedPixel=null;}}
    }));
  }
  if (observeColor) {
    const samples = {};
    for (const rva of [0xf070,0xee40]) {
      hooks.push(Interceptor.attach(mlib.base.add(rva), {
        onEnter(args) {
          const key = 'lab_' + rva.toString(16) + '_phase_' + polynomialPhase;
          counts[key] = (counts[key] || 0) + 1;
            // Retain the full33 green endpoint in addition to the initial samples.
            if (counts[key] > 8 && ![2113,2114].includes(counts[key])) return;
          this.destination = args[3];
          this.item = {functionRva:'0x'+rva.toString(16),phase:polynomialPhase,
            callIndex:counts[key],callerRva:this.returnAddress.sub(mlib.base).toString(),
            bits:this.context.ecx.toUInt32(),mode:this.context.edx.toUInt32(),
            input:[args[0].toInt32(),args[1].toInt32(),args[2].toInt32()]};
          captures.push(this.item);
        },
        onLeave() {
          if (this.item) this.item.output = [0,1,2].map(i=>this.destination.add(i*4).readS32());
        }
      }));
    }
    for (const rva of [0x1000, 0x1790]) {
      hooks.push(Interceptor.attach(mlib.base.add(rva), {
        onEnter() {
          const stack = this.context.esp;
          const mode = stack.add(8).readU32();
          const key = 'color_' + rva.toString(16) + '_mode_' + mode;
          counts[key] = (counts[key] || 0) + 1;
          const sampleKey = key + '_phase_' + polynomialPhase;
          if ((samples[sampleKey] || 0) >= 8) return;
          samples[sampleKey] = (samples[sampleKey] || 0) + 1;
          this.outputs = [this.context.ecx, this.context.edx, stack.add(4).readPointer()];
          this.item = {functionRva: '0x' + rva.toString(16), mode: mode,
            phase:polynomialPhase,callIndex:samples[sampleKey],
            callerRva:this.returnAddress.sub(mlib.base).toString(),
            input: [stack.add(12).readDouble(), stack.add(20).readDouble(), stack.add(28).readDouble()]};
          captures.push(this.item);
        },
        onLeave(result) {
          if (!this.item) return;
          this.item.output = this.outputs.map(pointer => pointer.readDouble());
          this.item.result = result.toUInt32();
        }
      }));
    }
  }
  hooks.push(Interceptor.attach(mlib.base.add(0x1df30), {
    onEnter() {
      if (!this.returnAddress.equals(mlib.base.add(0xf5f7))) return;
      counts.curveFinalized = (counts.curveFinalized || 0) + 1;
      this.destination = this.context.ecx;
      try {
        const count = this.destination.readU32();
        const domain = this.destination.add(0x24).readU32();
        if (count < 1 || count > 12 || domain > 512) return;
        const pairs = read(this.destination.add(0x14).readPointer(), count * 16);
        const key = domain + ':' + pairs;
        if (pairs === null || finalizedSeen.has(key) || finalizedSeen.size >= 128) return;
        finalizedSeen.add(key);
        this.item = {functionRva: '0x1df30', curveCount: count, domainSize: domain,
          normalizedPairsFloat64Hex: pairs};
        captures.push(this.item);
      } catch (_) { return; }
    },
    onLeave(result) {
      if (!this.item || result.toInt32() !== 0) return;
      this.item.finalizedPairsFloat64Hex = read(this.destination.add(0x20).readPointer(), this.item.domainSize * 16);
    }
  }));
  hooks.push(Interceptor.attach(mlib.base.add(0x1dc90), {
    onEnter(args) {
      if (!this.returnAddress.equals(mlib.base.add(0xf5f0))) return;
      counts.curveNormalized = (counts.curveNormalized || 0) + 1;
      const count = args[0].toUInt32();
      if (count < 1 || count > 12) return;
      const pairs = read(this.context.edx, count * 16);
      const normalizedKey = args[1].toUInt32() + ':' + pairs;
      if (pairs === null || normalizedSeen.has(normalizedKey) || normalizedSeen.size >= 128) return;
      normalizedSeen.add(normalizedKey);
      this.destination = this.context.ecx;
      this.item = {functionRva: '0x1dc90', callerRva: '0xf5f0', curveCount: count,
        domainSize: args[1].toUInt32(), normalizedPairsFloat64Hex: pairs};
      captures.push(this.item);
    },
    onLeave(result) {
      if (!this.item || result.toInt32() !== 0 || this.item.domainSize > 512) return;
      try {
        const buffer = this.destination.add(0x20).readPointer();
        this.item.sampledPairsFloat64Hex = read(buffer, this.item.domainSize * 16);
      } catch (_) { this.item.sampleCaptureFailed = true; }
    }
  }));
  for (const rva of [0x11220, 0x14bd0, 0x1bd30, 0x1c190]) {
    hooks.push(Interceptor.attach(mlib.base.add(rva), {
      onEnter(args) {
        const key = 'rva_' + rva.toString(16); counts[key] = (counts[key] || 0) + 1;
        if (rva === 0x11220 || rva === 0x14bd0) { polynomialPhase++; polynomialPhaseIndex = 0; }
        if (!observeDense || counts[key] > 8) return;
        this.grids = [];
        const pointers = [['ecx', this.context.ecx], ['edx', this.context.edx]];
        const argumentCount = (rva === 0x11220 || rva === 0x14bd0) ? 8 : 10;
        for (let index = 0; index < argumentCount; index++) pointers.push(['stack' + index, args[index]]);
        for (const [argument, pointer] of pointers) {
          try {
            if (pointer.isNull() || pointer.readU32() !== 3) continue;
            const nodes = pointer.add(4).readU32(), bytes = pointer.add(8).readU32();
            if (nodes < 2 || nodes > 33 || bytes !== nodes ** 3 * 24) continue;
            // Output data may not be initialized before the call. Header only.
            const item = {argument, nodes, bytes, beforeHeader16Hex: read(pointer, 16)};
            this.grids.push({pointer, item});
          } catch (_) { /* Not a verified dense grid; do not read further. */ }
        }
        this.item = {functionRva: '0x' + rva.toString(16), gridArguments: this.grids.map(grid => grid.item)};
        const callerModule=Process.findModuleByAddress(this.returnAddress);
        if(callerModule)this.item.caller={module:callerModule.name,
          rva:this.returnAddress.sub(callerModule.base).toString()};
        if(rva===0x1c190)this.item.parameterSplit={count:args[5].toUInt32(),
          incoming:parameterBlock(args[7])};
        if (rva === 0x11220 || rva === 0x14bd0) {
          this.item.initializedArguments = {
              oldParameterBlock:parameterBlock(args[3]),axisParameterBlock:parameterBlock(args[4]),
              additionalParameterBlock:parameterBlock(args[5]),
            preCurvesHex:read(this.context.ecx,300),postCurvesHex:read(this.context.edx,300),
            thirdCurvesHex:read(args[0],300),matrix240Hex:read(args[1],240),
              oldParameters512Hex:read(args[3],512),
              sixAxes512Hex:(!args[4].isNull() && args[4].readU32()===2 && args[4].add(4).readU32()===6) ? read(args[4],512) : null,
              axisParametersHex:(!args[4].isNull() && args[4].readU32()===2 && args[4].add(4).readU32()>=1 && args[4].add(4).readU32()<=6) ? read(args[4],8+args[4].add(4).readU32()*84) : null,
              additionalParametersHeader8Hex:read(args[5],8),
            // The empty legacy parameter list is only an eight-byte header;
            // never retain the unrelated heap bytes following that object.
            additionalEmptyParametersHex:(!args[5].isNull() && args[5].readU32()===1 && args[5].add(4).readU32()===0) ? read(args[5],8) : null,
            numericArguments:[args[2].toUInt32(),args[6].toUInt32()]
          };
        }
        if (rva === 0x11220 || rva === 0x14bd0) this.item.gamutPolicyArgument = args[6].toUInt32();
        captures.push(this.item);
      },
      onLeave(result) {
        if (!this.item) return;
        this.item.result = result.toUInt32();
        for (const grid of this.grids) {
          grid.item.afterHeader24Hex = read(grid.pointer, 24);
          grid.item.afterData72Hex = [12,16,20].map(offset => ({offset, hex: read(grid.pointer.add(offset), 72)}));
          if ((rva === 0x11220 || rva === 0x14bd0) && grid.item.argument === 'stack7' && result.toUInt32() === 1) {
            grid.item.initializedOutputFloat64Hex = read(grid.pointer.add(16), grid.item.bytes);
          }
        }
      }
    }));
  }
  hooks.push(Interceptor.attach(mlib.base.add(0xf490), {
    onEnter() {
      counts.f490 = (counts.f490 || 0) + 1;
      const addressKey = this.returnAddress.toString();
      let caller = callerNames.get(addressKey);
      if (caller === undefined) {
        const callerModule = Process.findModuleByAddress(this.returnAddress);
        caller = callerModule ? callerModule.name + '+' + this.returnAddress.sub(callerModule.base).toString() : 'unknown';
        callerNames.set(addressKey, caller);
      }
      let length;
      try { length = this.context.edx.readU32(); } catch (_) { return; }
      if (length < 1 || length > 12) return;
      // Only the initialized count/pairs, not unrelated stack bytes beyond them.
      const meaningful = read(this.context.edx, 4 + 8 * length);
      if (meaningful === null) return;
      if (curveItems.has(meaningful)) {
        const previous = curveItems.get(meaningful);
        previous.occurrences++;
        previous.callers[caller] = (previous.callers[caller] || 0) + 1;
        if (previous.firstCallIndices.length < 24) previous.firstCallIndices.push(counts.f490);
        return;
      }
      if (curvesSeen.size >= 128) return;
      curvesSeen.add(meaningful);
      this.item = {functionRva: '0xf490', curveCount: length, inputPairsHex: meaningful,
                   occurrences: 1, firstCallIndices: [counts.f490],
                   callers: {[caller]: 1},
                   outputPointer: this.context.ecx.toString()};
      curveItems.set(meaningful, this.item);
      captures.push(this.item);
    },
    onLeave(result) { if (this.item) this.item.result = result.toString(); }
  }));
  hooks.push(Interceptor.attach(mlib.base.add(0x196a0), {
    onEnter(args) {
      counts.converter = (counts.converter || 0) + 1;
      if (counts.converter > 64) return;
      this.item = {functionRva: '0x196a0', sourceHeader24Hex: read(this.context.ecx, 24),
        converterOption: args[0].toUInt32(),
        optionalCurves300Hex: read(this.context.edx, 300),
        outputHeader24Hex: read(args[1], 24)};
      // Bounded initialized grid data only; no heap addresses or trailing allocation bytes.
      this.destination = args[1];
      const gridSamples = pointer => {
        try {
          const channels = pointer.readU32(), nodes = pointer.add(4).readU32();
          const bytes = pointer.add(8).readU32();
          if (channels !== 3 || nodes < 2 || nodes > 33 || bytes !== nodes ** 3 * 24) return null;
          const indices = [0, 1, 2, Math.floor(nodes ** 3 / 2), nodes ** 3 - 2];
          // Source has a 12-byte header; destination has a 16-byte header.
          // Keep rejected candidates in evidence to expose identity-grid false positives.
          return {channels, nodes, bytes, headerWord12: pointer.add(12).readU32(),
            candidateLayouts: [12, 16, 20].map(offset => ({offset,
              samples: indices.map(index => ({index, rgb: [0, 1, 2].map(channel =>
                pointer.add(offset + (index * 3 + channel) * 8).readDouble())}))}))};
        } catch (_) { return null; }
      };
      this.gridSamples = gridSamples;
      this.item.sourceGrid = gridSamples(this.context.ecx);
      if (observeDense && this.item.sourceGrid) {
        this.item.sourceDenseFloat64Hex = read(this.context.ecx.add(12), this.item.sourceGrid.bytes);
      }
      captures.push(this.item);
    },
    onLeave(result) { if (this.item) {
      this.item.result = result.toString();
      this.item.outputGrid = this.gridSamples(this.destination);
      if (observeDense && this.item.outputGrid) {
        this.item.outputDenseFloat64Hex = read(this.destination.add(16), this.item.outputGrid.bytes);
      }
    } }
  }));
  return {mlibPath: mlib.path, mlibSize: mlib.size};
};
rpc.exports.finish = function() {
  for (const hook of hooks) hook.detach();
  return {counts: counts, captures: captures, uniqueCurveLimit: 128, converterLimit: 64};
};
