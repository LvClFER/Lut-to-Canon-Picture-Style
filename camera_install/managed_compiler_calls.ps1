param([Parameter(Mandatory=$true)][string]$OutputPath,
 [string]$MethodPattern='^EOSUtility\.(SetDevelopParamCommand::execute|View\.CameraSetting\.PSFileRegister::|CameraModel::get_PictureStyleLutParam|CaptureView::setCameraPictureStyleFile)',
 [string]$TypePattern='^EDSDKLib\.EDSDK\+EdsUsersetData$')
# Windows PowerShell/.NET Framework reflection-only metadata. Never Assembly.Load,
# method invocation, app startup, EDSDK session or installed-file modification.
$ErrorActionPreference='Stop'
$binary='C:/Program Files (x86)/Canon/EOS Utility/EU3/EOS Utility 3.exe'
$expected='728bcb732431855c411bf742d5f4e9c810666f5676b364f3448a6938d171d09e'
if((Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){throw 'Unknown application revision'}
if(Test-Path -LiteralPath $OutputPath){throw 'Refusing research-output overwrite'}
$handler=[ResolveEventHandler]{param($sender,$eventArgs) [Reflection.Assembly]::ReflectionOnlyLoad($eventArgs.Name)}
[AppDomain]::CurrentDomain.add_ReflectionOnlyAssemblyResolve($handler)
$rows=New-Object 'System.Collections.Generic.List[object]'
$errors=New-Object 'System.Collections.Generic.List[object]'
$unresolved=New-Object 'System.Collections.Generic.List[object]'
$methodCount=0
$selectedMethods=New-Object 'System.Collections.Generic.List[object]'
try {
 $assembly=[Reflection.Assembly]::ReflectionOnlyLoadFrom($binary)
 try{$types=$assembly.GetTypes()}catch [Reflection.ReflectionTypeLoadException]{
  $types=$_.Exception.Types|Where-Object{$null -ne $_}
  $errors.Add(@{stage='type-load';error=$_.Exception.Message})
 }
 $opcodes=@{}
 foreach($field in [Reflection.Emit.OpCodes].GetFields([Reflection.BindingFlags]'Public,Static')){
  $op=$field.GetValue($null);$opcodes[[int]$op.Value -band 65535]=$op
 }
 $flags=[Reflection.BindingFlags]'Public,NonPublic,Static,Instance,DeclaredOnly'
 foreach($type in $types){
  try{$methods=@($type.GetMethods($flags))+@($type.GetConstructors($flags))}catch{
   $errors.Add(@{stage='methods';type=$type.FullName;error=$_.Exception.Message});continue
  }
  foreach($method in $methods){
   $methodCount++
   try {
    $signature=@{method=$type.FullName+'::'+$method.Name;token=$method.MetadataToken;
     returnType=if($method -is [Reflection.MethodInfo]){$method.ReturnType.FullName}else{$null};
     parameters=@($method.GetParameters()|ForEach-Object{@{name=$_.Name;type=$_.ParameterType.FullName;position=$_.Position}})}
    $body=$method.GetMethodBody();if($null -eq $body){
     if($signature.method -match $MethodPattern){$signature.instructions=@();$selectedMethods.Add($signature)}
     continue
    }
    $bytes=$body.GetILAsByteArray();$instructions=New-Object 'System.Collections.Generic.List[object]';$offset=0
    while($offset -lt $bytes.Length){
     $start=$offset;$code=[int]$bytes[$offset];$offset++
     if($code -eq 254){$code=65024+[int]$bytes[$offset];$offset++}
     if(-not $opcodes.ContainsKey($code)){throw 'Unknown IL opcode'}
     $op=$opcodes[$code];$length=0;$operand=$null;$target=$null;$literal=$null
     switch($op.OperandType.ToString()){
      'InlineNone'{$length=0}
      {$_ -in 'ShortInlineI','ShortInlineVar','ShortInlineBrTarget'}{
       $length=1;$operand=[int]$bytes[$offset]
       if($_ -ne 'ShortInlineVar' -and $operand -ge 128){$operand-=256}
      }
      'InlineVar'{$length=2;$operand=[BitConverter]::ToUInt16($bytes,$offset)}
      {$_ -in 'InlineI','InlineBrTarget','InlineField','InlineMethod','InlineSig','InlineString','InlineTok','InlineType','ShortInlineR'}{
       $length=4;$operand=[BitConverter]::ToInt32($bytes,$offset)
      }
      {$_ -in 'InlineI8','InlineR'}{$length=8}
      'InlineSwitch'{
       $count=[BitConverter]::ToInt32($bytes,$offset);if($count -lt 0 -or $count -gt 65536){throw 'Invalid IL switch'}
       $length=4+4*$count;$operand=@()
       if($offset+$length -gt $bytes.Length){throw 'Truncated IL switch'}
       for($j=0;$j -lt $count;$j++){$operand+=([BitConverter]::ToInt32($bytes,$offset+4+4*$j))}
      }
      default{throw ('Unknown operand '+$op.OperandType)}
     }
     if($offset+$length -gt $bytes.Length){throw 'Truncated IL operand'}
     if($op.OperandType.ToString() -eq 'InlineMethod'){
      try{
       $typeArguments=$method.DeclaringType.GetGenericArguments()
       $methodArguments=[Type[]]@();if($method.IsGenericMethod){$methodArguments=$method.GetGenericArguments()}
       $resolved=$method.Module.ResolveMethod($operand,$typeArguments,$methodArguments)
       $target=$resolved.DeclaringType.FullName+'::'+$resolved.Name
      }catch{
       $unresolved.Add(@{caller=$type.FullName+'::'+$method.Name;offset=$start;token=$operand;error=$_.Exception.Message})
      }
     }
     if($op.OperandType.ToString() -eq 'InlineField'){
      try{
       $resolvedField=$method.Module.ResolveField($operand,$method.DeclaringType.GetGenericArguments(),[Type[]]@())
       $target=$resolvedField.DeclaringType.FullName+'::'+$resolvedField.Name
      }catch{}
     }
     if($op.OperandType.ToString() -eq 'InlineString'){$literal=$method.Module.ResolveString($operand)}
     $branchTargets=@()
     if($op.OperandType.ToString() -in @('InlineBrTarget','ShortInlineBrTarget')){$branchTargets=@($offset+$length+$operand)}
     if($op.OperandType.ToString() -eq 'InlineSwitch'){$branchTargets=@($operand|ForEach-Object{$offset+$length+$_})}
     $instructions.Add(@{offset=$start;opcode=$op.Name;operand=$operand;target=$target;literal=$literal;branchTargets=$branchTargets});$offset+=$length
    }
    $boundaries=@{};foreach($instruction in $instructions){$boundaries[$instruction.offset]=$true}
    foreach($instruction in $instructions){foreach($branch in $instruction.branchTargets){
     if(-not $boundaries.ContainsKey($branch)){throw 'Branch target is not an instruction boundary'}
    }}
    if(($type.FullName+'::'+$method.Name) -match $MethodPattern -or
       @($instructions|Where-Object{$_.opcode -eq 'stfld' -and $_.target -eq 'EOSUtility.CameraModel::pictureStyleLutParam'}).Count -gt 0){
     $signature.instructions=@($instructions.ToArray());$selectedMethods.Add($signature)
    }
    for($index=0;$index -lt $instructions.Count;$index++){
     $item=$instructions[$index]
     if($item.target -and $item.opcode -in @('call','callvirt','newobj','ldftn','ldvirtftn') -and ($item.target -match '::EdsCfp' -or $item.target -match '::Eds(Get|Set)PropertyData$' -or $item.target -match '^EDSDKLib.CustomFileParser::')){
      $first=[Math]::Max(0,$index-20);$last=[Math]::Min($instructions.Count-1,$index+10)
      $rows.Add(@{caller=$type.FullName+'::'+$method.Name;callerToken=$method.MetadataToken;
       offset=$item.offset;target=$item.target;context=@($instructions.GetRange($first,$last-$first+1))})
     }
    }
   }catch{$errors.Add(@{stage='method-body';method=$type.FullName+'::'+$method.Name;error=$_.Exception.Message})}
  }
 }
 if((Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){throw 'Original binary changed'}
 $selectedTypes=@($types|Where-Object{$_.FullName -match $TypePattern}|ForEach-Object{
  $selectedType=$_
  @{type=$selectedType.FullName;attributes=$selectedType.Attributes.ToString();
   fields=@($selectedType.GetFields([Reflection.BindingFlags]'Public,NonPublic,Instance,DeclaredOnly')|ForEach-Object{
    @{name=$_.Name;type=$_.FieldType.FullName;token=$_.MetadataToken;
     attributes=@([Reflection.CustomAttributeData]::GetCustomAttributes($_)|ForEach-Object{
      @{type=$_.AttributeType.FullName;constructorArguments=@($_.ConstructorArguments|ForEach-Object{$_.Value.ToString()});
       namedArguments=@($_.NamedArguments|ForEach-Object{@{name=$_.MemberName;value=$_.TypedValue.Value.ToString()}})}
     })}
   })}
 })
 $report=@{cameraAccess=$false;applicationExecuted=$false;dllModified=$false;
  binarySha256=$expected;scope='Reflection-only IL call contexts, not transaction execution';
  types=$types.Count;methods=$methodCount;complete=($errors.Count -eq 0 -and $unresolved.Count -eq 0);
  instructionDecodeComplete=($errors.Count -eq 0);callTargetResolutionComplete=($unresolved.Count -eq 0);
  methodPattern=$MethodPattern;selectedMethods=@($selectedMethods.ToArray());selectedTypes=$selectedTypes;
  unresolved=@($unresolved.ToArray());errors=@($errors.ToArray());calls=@($rows.ToArray())}
 $stream=[IO.File]::Open([IO.Path]::GetFullPath($OutputPath),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
 try{$writer=New-Object IO.StreamWriter($stream,[Text.UTF8Encoding]::new($false));$writer.Write(($report|ConvertTo-Json -Depth 12));$writer.Flush()}finally{$stream.Dispose()}
 Write-Output ('Methods: '+$methodCount+'; Calls: '+$rows.Count+'; Errors: '+$errors.Count+'; Unresolved targets: '+$unresolved.Count)
}finally{[AppDomain]::CurrentDomain.remove_ReflectionOnlyAssemblyResolve($handler)}
