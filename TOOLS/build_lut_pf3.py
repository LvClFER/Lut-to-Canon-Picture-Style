from pathlib import Path
import sys, json, hashlib, unicodedata
from canon_engine import find_dll, parse_lut_file, export_pf3
from recipe_lut import (
    normalize_recipe_settings, recipe_is_neutral, bake_recipe_cube,
    write_cube, recipe_summary,
)

HERE = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    RESOURCE_ROOT = HERE.parent


def canon_style_name(name, fallback="Picture Style"):
    name = (name or fallback or "Picture Style").strip()
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    value = (value.strip() or fallback or "Picture Style")[:31]
    return value


def build_pf3_from_source(source_path, requested_title=None, work_dir=None, log=print, recipe_settings=None, baked_cube_output=None):
    source_path = Path(source_path).resolve()
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if source_path.suffix.lower() not in {'.cube', '.tif', '.tiff'}:
        raise ValueError('Supported LUT inputs are .cube, .tif and .tiff Hald CLUT files.')

    dll = find_dll()
    if not dll:
        raise RuntimeError("EdsCFParse.dll not found. Install Canon Picture Style Editor or DPP.")

    base = RESOURCE_ROOT/'SOURCE'/'BASE_NEUTRAL_RP.pf3'
    if not base.exists():
        raise FileNotFoundError(f"Bundled PF3 base not found: {base}")

    work = Path(work_dir) if work_dir else RESOURCE_ROOT/'WORK'
    work.mkdir(parents=True, exist_ok=True)
    out = work/'CURRENT_LUT_70_71.pf3'

    cube = parse_lut_file(source_path)
    canon_title = canon_style_name(requested_title, source_path.stem)
    recipe = normalize_recipe_settings(recipe_settings)

    effective_cube = cube
    if recipe_is_neutral(recipe):
        log("Recipe adjustments: none — source LUT will be used as-is.")
    else:
        log("Baking LUT adjustments into one 33^3 LUT…")
        log("  "+recipe_summary(recipe))
        effective_cube = bake_recipe_cube(cube, recipe, size=33)
        if baked_cube_output:
            write_cube(Path(baked_cube_output), effective_cube, title=canon_title + " adjusted")
            log(f"  Baked CUBE: {Path(baked_cube_output)}")

    entry = {"cube":effective_cube, "enabled":True, "opacity":1.0}
    controls = {
        "contrast":0, "saturation":0, "color_tone":0,
        "sharpness_override":False, "sharp_strength":0, "fineness":2, "threshold":4
    }

    log(f"Building exact dense PF3 from: {source_path.name}")
    size, sha = export_pf3(
        dll, base, out, [entry], controls,
        title=canon_title,
        log=lambda s: log("  "+s),
        progress=lambda v: None,
    )

    source_type = "hald_tiff" if source_path.suffix.lower() in {'.tif','.tiff'} else "cube"
    manifest = {
        "source":str(source_path),
        "sourceType":source_type,
        "sourceSha256":hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "sourceLutSize":int(cube['size']),
        "effectiveLutSize":int(effective_cube['size']),
        "recipe":recipe,
        "recipeActive":not recipe_is_neutral(recipe),
        "recipeSummary":recipe_summary(recipe),
        "haldLevel":cube.get('hald_level'),
        "sourceBitDepth":cube.get('bit_depth'),
        "pf3":str(out),
        "pf3Size":size,
        "pf3Sha256":sha,
        "method":"Neutral PF3 + Canon dense 33^3 0x70/0x71 LUT bake",
        "pictureStyleName":canon_title,
    }
    (work/'CURRENT_LUT.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    log(f"Picture Style name: {canon_title}")
    if source_type == 'hald_tiff':
        log(f"Hald CLUT: level {cube.get('hald_level')} / {cube['size']} samples per channel / {cube.get('bit_depth')}-bit source")
    log(f"READY: {out}")
    return out, manifest, canon_title


def main():
    if len(sys.argv) < 2:
        print("Usage: py build_lut_pf3.py LUT.cube|HALD.tif|HALD.tiff [Picture Style name]")
        return 2
    src = Path(sys.argv[1])
    title = sys.argv[2] if len(sys.argv) >= 3 else None
    build_pf3_from_source(src, title)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as e:
        print("\\nBUILD ERROR:", e)
        raise SystemExit(10)
