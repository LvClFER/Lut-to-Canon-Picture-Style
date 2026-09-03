from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

from canon_runtime import discover_pse, ensure_runtime_input_profile

HERE=Path(__file__).resolve().parent
errors=[]

def ok(msg): print('[OK]',msg)
def bad(msg): print('[FAIL]',msg);errors.append(msg)

# Canon resources must come from the user's local PSE installation and private
# runtime cache. The public package deliberately contains no Canon ICC/PF3/DLL.
install=discover_pse()
if install:
    try:
        profile=ensure_runtime_input_profile(install)
        ok(f'PSE discovered · {install.pse_version or "version unknown"}')
        ok(f'Runtime input profile · {profile.stat().st_size:,} B · local cache')
        from canon_engine import ensure_runtime_base_pf3, inspect_pf3
        if not install.edscfparse_dll:bad('PSE EdsCFParse.dll unavailable')
        else:
            for style in ('Standard','Portrait','Landscape','Neutral','Faithful','Fine Detail'):
                p=ensure_runtime_base_pf3(install.edscfparse_dll,style)
                data=inspect_pf3(install.edscfparse_dll,p)
                if len(data['table'])!=215628:bad(f'{style} generated PF3 table invalid')
                else:ok(f'{style} runtime PF3 · {p.stat().st_size:,} B')
    except Exception as exc:bad('PSE runtime resource preparation: '+str(exc))
else:
    print('[SKIP] Picture Style Editor not installed; image/LUT mode remains available.')

try:
    from canon_engine import parse_lut_file
    cube=parse_lut_file(HERE/'example_luts'/'hald_identity_8.png')
    ok(f'Hald LUT parser · {cube["size"]}^3')
except Exception as e: bad('LUT parser: '+str(e))

# Windows-only DPP startup smoke test. No RAW required.
if os.name=='nt':
    try:
        p=subprocess.Popen([sys.executable,'-u',str(HERE/'canon_dpp_worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',cwd=str(HERE))
        line=p.stdout.readline().strip()
        msg=json.loads(line) if line else {}
        if msg.get('ok'):
            ok('DPP4Lib worker initialized · '+msg.get('dpp4lib',''))
            p.stdin.write(json.dumps({'id':1,'cmd':'shutdown'})+'\n');p.stdin.flush();p.stdout.readline();p.wait(timeout=3)
        else:
            bad('DPP4Lib worker: '+str(msg.get('error') or 'no ready response'))
            try:p.terminate()
            except:pass
    except Exception as e: bad('DPP4Lib worker smoke test: '+str(e))
else:
    print('[SKIP] DPP4Lib worker smoke test requires Windows.')

print('\nRESULT:', 'PASS' if not errors else f'{len(errors)} FAILURE(S)')
if errors:
    for e in errors: print(' -',e)
    raise SystemExit(1)
