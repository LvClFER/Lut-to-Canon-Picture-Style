from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from canon_engine import CANON_STRONG_RAW_EXTENSIONS, load_reference_image, parse_lut_file
from canon_runtime import BUILD_ID, PUBLIC_VERSION, discover_pse, ensure_runtime_input_profile, runtime_environment, sanitize_path
from dpp_client import DppBackendClient
from render_geometry import fit_size_within_box, oriented_native_size


HERE=Path(__file__).resolve().parent
STYLES=("Standard","Portrait","Landscape","Neutral","Faithful","Fine Detail")
WB_MODES=("As Shot","Auto — Ambience","Auto — White","Daylight","Shade","Cloudy","Tungsten","White Fluorescent","Flash","Kelvin")


def metrics(reference: Image.Image, candidate: Image.Image) -> dict:
    a=np.asarray(reference.convert("RGB"),dtype=np.int16)
    b=np.asarray(candidate.convert("RGB").resize(reference.size,Image.Resampling.LANCZOS),dtype=np.int16)
    delta=np.abs(a-b)
    return {"mae":round(float(delta.mean()),5),"max":int(delta.max()),"changed_percent":round(float((delta.max(axis=2)>0).mean()*100),4)}


def base_settings(**changes):
    value={"style":"Neutral","wb":"As Shot","kelvin":5200,"exposure":0.0,"contrast":0,"saturation":0,"color_tone":0,"wb_ab_shift":0,"wb_gm_shift":0}
    value.update(changes);return value


def main(argv=None):
    parser=argparse.ArgumentParser(description="Canon Style Studio Public Alpha regression matrix")
    parser.add_argument("--test-dir",type=Path,default=HERE/"test_files")
    parser.add_argument("--output",type=Path,default=HERE/"PUBLIC_ALPHA_REGRESSION_REPORT.json")
    parser.add_argument("--max-raws",type=int,default=0,help="0 tests every RAW")
    args=parser.parse_args(argv)
    started=time.perf_counter();install=discover_pse()
    report={"application_version":PUBLIC_VERSION,"build_id":BUILD_ID,"created_utc":datetime.now(timezone.utc).isoformat(),
            "test_directory":sanitize_path(args.test_dir),"pse_found":bool(install),"files":[],"summary":{}}
    files=sorted(path for path in args.test_dir.rglob("*") if path.is_file()) if args.test_dir.is_dir() else []
    raws=[p for p in files if p.suffix.lower() in CANON_STRONG_RAW_EXTENSIONS]
    images=[p for p in files if p.suffix.lower() in {".jpg",".jpeg",".png",".tif",".tiff"}]
    if args.max_raws>0:raws=raws[:args.max_raws]
    failures=[];client=None
    try:
        if install:
            profile=ensure_runtime_input_profile(install)
            temp=tempfile.TemporaryDirectory()
            client=DppBackendClient(HERE/"canon_dpp_worker.py",Path(temp.name)/"cache",runtime_environment(install,profile))
            report["canon_runtime"]={"pse_version":install.pse_version,"dppcore_version":install.dppcore_version}
        for path in raws:
            item={"file":path.name,"kind":"RAW","status":"PASS","checks":{}}
            try:
                if client is None:raise RuntimeError("Picture Style Editor not found")
                preview,info,_,_=load_reference_image(path,"As Shot",0)
                native=oriented_native_size(preview.size,info);target=fit_size_within_box(native,600,600)
                neutral,_=client.render(path,base_settings(),*target)
                item["geometry"]={"native":native,"rendered":neutral.size,"orientation":"portrait" if native[1]>native[0] else "landscape"}
                for wb in WB_MODES:
                    image,_=client.render(path,base_settings(wb=wb,kelvin=4700 if wb=="Kelvin" else 5200),*target)
                    item["checks"]["wb_"+wb]=metrics(neutral,image)
                for style in STYLES:
                    image,_=client.render(path,base_settings(style=style),*target)
                    item["checks"]["style_"+style]=metrics(neutral,image)
                for name,changes in (("exposure",{"exposure":1.0}),("contrast",{"contrast":4}),("saturation",{"saturation":4}),("color_tone",{"color_tone":4})):
                    image,_=client.render(path,base_settings(**changes),*target);item["checks"][name]=metrics(neutral,image)
                tungsten=item["checks"]["wb_Tungsten"]
                if tungsten["mae"]<1.0:raise AssertionError("Tungsten produced insufficient pixel change")
                if len({hashlib.sha256(client.render(path,base_settings(style=s),*target)[0].tobytes()).hexdigest() for s in STYLES})!=6:
                    raise AssertionError("Picture Styles are not all distinct")
            except Exception as exc:
                item["status"]="FAIL";item["error"]=str(exc);failures.append(f"{path.name}: {exc}")
            report["files"].append(item);print(f"[{item['status']}] {path.name}",flush=True)
        for path in images:
            item={"file":path.name,"kind":"image","status":"PASS"}
            try:
                image,info,_,_=load_reference_image(path,"As Shot",0);item["dimensions"]=image.size;item["decoder"]=info.get("decoder")
            except Exception as exc:item["status"]="FAIL";item["error"]=str(exc);failures.append(f"{path.name}: {exc}")
            report["files"].append(item);print(f"[{item['status']}] {path.name}",flush=True)
        # Public example LUT/Hald parser coverage, independent of RAW availability.
        for path in sorted((HERE/"example_luts").glob("*")):
            if path.suffix.lower() not in {".cube",".png",".tif",".tiff"}:continue
            try:
                lut=parse_lut_file(path);report.setdefault("luts",[]).append({"file":path.name,"status":"PASS","type":lut["source"],"size":lut["size"],"bit_depth":lut.get("bit_depth")})
            except Exception as exc:
                report.setdefault("luts",[]).append({"file":path.name,"status":"FAIL","error":str(exc)});failures.append(f"{path.name}: {exc}")
    finally:
        if client:client.close()
        if 'temp' in locals():temp.cleanup()
    report["summary"]={"raw_count":len(raws),"image_count":len(images),"failures":len(failures),"elapsed_seconds":round(time.perf_counter()-started,2),
                       "status":"PASS" if not failures and (raws or images) else ("SKIP" if not files else "FAIL")}
    report["failures"]=failures;args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(report["summary"],indent=2),flush=True)
    print(f"Report: {args.output}",flush=True)
    return 1 if failures else 0


if __name__=="__main__":raise SystemExit(main())
