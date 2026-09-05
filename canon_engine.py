from __future__ import annotations

import os
import re
import io
import mmap
import math
import json
import time
import struct
import ctypes
import colorsys
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageCms

from canon_runtime import cache_dir as runtime_cache_dir, discover_pse
from creative_controls import (
    creative_lut_entry, normalize_creative_controls,
    normalize_recipe_wb, recipe_wb_lut_entry,
)

try:
    import tifffile
except Exception:
    tifffile = None

try:
    import imageio.v3 as iio
except Exception:
    iio = None

try:
    import rawpy
except Exception:
    rawpy = None

ENGINE_VERSION = "1.0.0"

CANON_RAW_EXTENSIONS = {".cr3", ".cr2", ".crw", ".tif", ".cip", ".crn"}
CANON_STRONG_RAW_EXTENSIONS = {".cr3", ".cr2", ".crw", ".cip", ".crn"}
HALD_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}
NORMAL_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}

PROPERTY_ORDER = [
    (0x00000114,   4), (0x00000115,  32), (0x40001002,  32),
    (0x4000100A,  64), (0x40001021, 240), (0x40001029, 240),
    (0x40001019, 300), (0x40001018, 300), (0x40001065, 300),
    (0x40001061, 512), (0x40001062, 512), (0x40001023,   8),
    (0x4000102B,   8), (0x40001008, 456), (0x40001012,   4),
    (0x40001070, 215628), (0x40001071, 215628),
    (0x4000100D,   3), (0x4000100C,   2), (0x40001011,   4),
    (0x40001080,   4),
]
BIG_TABLES = (0x40001070, 0x40001071)
OPEN_EXISTING = 2
CREATE_ALWAYS = 1
READ = 0
WRITE = 1

PICTURE_STYLE_IDS = {
    "Standard": 0x81,
    "Portrait": 0x82,
    "Landscape": 0x83,
    "Neutral": 0x84,
    "Faithful": 0x85,
    "Fine Detail": 0x88,
}

VALIDATED_BASE_SHA256 = {
    "Neutral": "51959f04d1eeac4ec41f4158c9ec2dfabea79c4380473edf8eaccce6274e481c",
    "Standard": "f29f9ee8e0469171d29730c79fb7751a50d0f34624c654f8283951aea611283e",
    "Faithful": "499e3d2f69775b5092e13eefde8d6cd21b685439c5c1ee3c6656955c5c7efbfd",
    "Portrait": "380a9576ee4cc346ea83ea6c17948605ca51d9e0cf92ed5b64071119a3489137",
    "Landscape": "259f67ed1b73162649f68931b2c542be380981163747f128fcd7a76c937aa3f8",
    "Fine Detail": "126611fb855066506b4752c287d51d2c62f07349679280f7378206f44fc4dd02",
}


def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else float(v))


def srgb_to_linear(v):
    """Convert a normalized sRGB component to linear light."""
    v=clamp01(v)
    return v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4


def linear_to_srgb(v):
    """Convert a normalized linear-light component to sRGB."""
    v=clamp01(v)
    return 12.92*v if v<=0.0031308 else 1.055*(v**(1.0/2.4))-0.055


def normalize_rgb_gains(mult):
    values=[max(1e-6,float(x)) for x in mult]
    middle=sum(values)/3.0
    return tuple(x/max(middle,1e-6) for x in values)


@lru_cache(maxsize=256)
def _linear_gain_point_table(r_gain,g_gain,b_gain):
    """Cached exact sRGB point table for separable linear-light RGB gains."""
    table=[]
    for gain in (r_gain,g_gain,b_gain):
        for value in range(256):
            linear=srgb_to_linear(value/255.0)*float(gain)
            table.append(int(round(clamp01(linear_to_srgb(linear))*255.0)))
    return tuple(table)


def apply_linear_rgb_gains(image,mult):
    """Apply exposure/WB channel gains using a fast 1D LUT per channel."""
    gains=tuple(round(max(0.0,float(x)),8) for x in mult)
    return image.convert("RGB").point(_linear_gain_point_table(*gains))


def win_bytes(path):
    s = str(Path(path))
    try:
        return s.encode("mbcs")
    except LookupError:
        return os.fsencode(s)


def find_dll():
    install = discover_pse()
    return install.edscfparse_dll if install else None


def file_fingerprint(path: Path) -> str:
    path = Path(path)
    try:
        st = path.stat()
        return f"{path.resolve()}|{st.st_size}|{st.st_mtime_ns}"
    except Exception:
        return str(path)


def validate_pf3_header(path):
    data = Path(path).read_bytes()
    if len(data) < 12 or data[4:7] != b"PSP":
        raise ValueError(f"{Path(path).name} is not a valid Canon PSP/PF3 file.")
    return len(data)


def parse_cube(path):
    path = Path(path)
    size = None
    dmin = [0.0, 0.0, 0.0]
    dmax = [1.0, 1.0, 1.0]
    title = path.stem
    values = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        p = line.split()
        key = p[0].upper()
        if key == "TITLE":
            m = re.search(r'"(.*)"', line)
            title = m.group(1) if m else " ".join(p[1:])
        elif key == "LUT_3D_SIZE":
            size = int(p[1])
        elif key == "DOMAIN_MIN":
            dmin = list(map(float, p[1:4]))
        elif key == "DOMAIN_MAX":
            dmax = list(map(float, p[1:4]))
        elif key == "LUT_1D_SIZE":
            raise ValueError("1D .cube LUTs are not supported.")
        else:
            try:
                if len(p) >= 3:
                    values.extend(map(float, p[:3]))
            except ValueError:
                pass
    if not size:
        raise ValueError("LUT_3D_SIZE is missing.")
    if len(values) != size ** 3 * 3:
        raise ValueError(
            f"{path.name}: LUT_3D_SIZE {size} expects {size**3:,} rows; found {len(values)//3:,}."
        )
    if any(dmax[i] <= dmin[i] for i in range(3)):
        raise ValueError("Invalid DOMAIN_MIN / DOMAIN_MAX.")
    return {
        "path": path, "title": title, "size": size,
        "domain_min": dmin, "domain_max": dmax,
        "values": np.asarray(values, dtype=np.float32),
        "source": "cube", "bit_depth": None, "color_space": "RGB",
        "lossy": False, "fingerprint": file_fingerprint(path),
    }


def detect_hald_level_from_size(w, h):
    if w != h or w < 8:
        return None
    level = round(w ** (1.0 / 3.0))
    if level < 2 or level ** 3 != w:
        return None
    return level


def _icc_description(path: Path) -> str:
    try:
        with Image.open(path) as im:
            icc = im.info.get("icc_profile")
        if not icc:
            return "Unspecified"
        profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        desc = ImageCms.getProfileDescription(profile).strip()
        return desc or "Embedded ICC"
    except Exception:
        return "Embedded ICC" if Path(path).suffix.lower() in {".tif", ".tiff"} else "Unspecified"


def _read_hald_array(path: Path):
    ext = path.suffix.lower()
    arr = None
    if ext in {".tif", ".tiff"} and tifffile is not None:
        arr = tifffile.imread(path)
    elif iio is not None:
        try:
            arr = iio.imread(path)
        except Exception:
            arr = None
    if arr is None:
        with Image.open(path) as im:
            im.load()
            arr = np.asarray(im.convert("RGB"))

    arr = np.asarray(arr)
    if arr.ndim == 3 and arr.shape[0] in (3, 4) and arr.shape[-1] not in (3, 4):
        arr = np.moveaxis(arr, 0, -1)
    if arr.ndim == 2:
        arr = np.repeat(arr[..., None], 3, axis=2)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError(f"{path.name}: expected an RGB Hald image.")
    arr = arr[..., :3]

    if np.issubdtype(arr.dtype, np.integer):
        bits = int(arr.dtype.itemsize * 8)
        maxv = float(np.iinfo(arr.dtype).max)
        norm = arr.astype(np.float32) / maxv
    elif np.issubdtype(arr.dtype, np.floating):
        bits = 32 if arr.dtype.itemsize <= 4 else 64
        norm = np.clip(arr.astype(np.float32), 0.0, 1.0)
    else:
        raise ValueError(f"Unsupported Hald pixel type: {arr.dtype}")
    return norm, bits


def parse_hald_image(path):
    """Parse standard Hald ordering: row-major R-fastest, then G, then B.

    A Hald level L is an L³×L³ image representing an L²-sample cube.
    Its flattened RGB pixel stream is already the standard CUBE sequence; it
    must not be reinterpreted as B-plane tiles.
    """
    path = Path(path)
    arr, bits = _read_hald_array(path)
    h, w = arr.shape[:2]
    level = detect_hald_level_from_size(w, h)
    if level is None:
        raise ValueError(
            f"{path.name} is not a valid Hald CLUT image.\n"
            "Expected a square image where width = height = level³ (for example 512×512)."
        )
    cube_size = level * level
    expected_pixels = cube_size ** 3
    values = np.ascontiguousarray(arr[..., :3], dtype=np.float32).reshape(-1, 3)
    if values.shape[0] != expected_pixels:
        raise ValueError(
            f"{path.name}: Hald level {level} expects {expected_pixels:,} pixels; "
            f"found {values.shape[0]:,}."
        )
    color_space = _icc_description(path)
    return {
        "path": path, "title": path.stem, "size": cube_size,
        "domain_min": [0.0, 0.0, 0.0], "domain_max": [1.0, 1.0, 1.0],
        "values": values.reshape(-1), "source": "hald", "hald_level": level,
        "image_size": (w, h), "bit_depth": bits, "color_space": color_space,
        "lossy": path.suffix.lower() in {".jpg", ".jpeg"},
        "fingerprint": file_fingerprint(path),
    }


def parse_lut_file(path):
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".cube":
        return parse_cube(path)
    if ext in HALD_IMAGE_EXTENSIONS:
        return parse_hald_image(path)
    raise ValueError(f"Unsupported LUT: {path.name}")


def load_lut_metadata(path, cube=None):
    """Load descriptive LUT metadata without changing the LUT transformation."""
    path=Path(path);cube=cube or {}
    metadata={
        "inputColorSpace":None,"outputColorSpace":None,"transferFunction":None,
        "preferredBaseStyle":None,"calibrationSource":None,"calibrationTarget":None,
        "lutSize":int(cube.get("size",0) or 0),
        "sourceHash":hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    known={
        "velvia50_frontier_canon_full_match_v4_33.cube":{
            "preferredBaseStyle":"Standard","calibrationSource":"Canon Standard",
            "calibrationTarget":"Lightroom Fuji Velvia 50 +0EV Frontier",
        },
        "goldpushed_noritsu_canon_full_match_v4_33.cube":{
            "preferredBaseStyle":"Standard","calibrationSource":"Canon Standard",
            "calibrationTarget":"Lightroom Kodak Gold pushed +0EV Noritsu",
        },
    }
    metadata.update(known.get(path.name.lower(),{}))
    sidecars=(path.with_suffix(path.suffix+".json"),path.with_suffix(".json"),path.parent/(path.stem+".lut.json"))
    for sidecar in sidecars:
        if not sidecar.is_file():continue
        try:
            value=json.loads(sidecar.read_text(encoding="utf-8"))
            if isinstance(value,dict):
                allowed=set(metadata)
                metadata.update({key:value[key] for key in allowed if key in value})
            break
        except Exception:
            continue
    metadata["lutSize"]=int(cube.get("size",metadata.get("lutSize") or 0))
    metadata["sourceHash"]=hashlib.sha256(path.read_bytes()).hexdigest()
    return metadata


class CubeSampler:
    def __init__(self, cube):
        self.n = int(cube["size"])
        self.v = np.asarray(cube["values"], dtype=np.float32)
        self.dmin = cube["domain_min"]
        self.dmax = cube["domain_max"]

    def _idx(self, r, g, b, c):
        return (((b * self.n + g) * self.n + r) * 3 + c)

    def sample(self, r, g, b):
        coords = []
        for value, mn, mx in zip((r, g, b), self.dmin, self.dmax):
            coords.append(clamp01((value - mn) / (mx - mn)) * (self.n - 1))
        xr, xg, xb = coords
        r0, g0, b0 = int(xr), int(xg), int(xb)
        r1, g1, b1 = min(r0 + 1, self.n - 1), min(g0 + 1, self.n - 1), min(b0 + 1, self.n - 1)
        tr, tg, tb = xr-r0, xg-g0, xb-b0
        out = [0.0, 0.0, 0.0]
        for c in range(3):
            c000=self.v[self._idx(r0,g0,b0,c)]; c100=self.v[self._idx(r1,g0,b0,c)]
            c010=self.v[self._idx(r0,g1,b0,c)]; c110=self.v[self._idx(r1,g1,b0,c)]
            c001=self.v[self._idx(r0,g0,b1,c)]; c101=self.v[self._idx(r1,g0,b1,c)]
            c011=self.v[self._idx(r0,g1,b1,c)]; c111=self.v[self._idx(r1,g1,b1,c)]
            c00=c000*(1-tr)+c100*tr; c10=c010*(1-tr)+c110*tr
            c01=c001*(1-tr)+c101*tr; c11=c011*(1-tr)+c111*tr
            c0=c00*(1-tg)+c10*tg; c1=c01*(1-tg)+c11*tg
            out[c]=float(c0*(1-tb)+c1*tb)
        return out


def cube_to_pillow_lut(cube, force_size=None):
    n = int(cube["size"])
    dmin, dmax = cube["domain_min"], cube["domain_max"]
    if force_size is None and n <= 65 and all(abs(x) < 1e-9 for x in dmin) and all(abs(x-1.0) < 1e-9 for x in dmax):
        vals = np.clip(np.asarray(cube["values"], dtype=np.float32), 0.0, 1.0)
        return ImageFilter.Color3DLUT(n, vals.tolist(), channels=3)
    sampler = CubeSampler(cube)
    size = int(force_size or 33)
    table = []
    for b in range(size):
        bz=b/(size-1)
        for g in range(size):
            gy=g/(size-1)
            for r in range(size):
                rx=r/(size-1)
                table.extend(clamp01(x) for x in sampler.sample(rx,gy,bz))
    return ImageFilter.Color3DLUT(size, table, channels=3)


def validate_canon_table(data):
    if len(data) != 215628:
        raise ValueError(f"Unexpected Canon table size: {len(data)}")
    hdr = struct.unpack_from("<HHH", data, 0)
    if hdr != (12,3,33):
        raise ValueError(f"Unexpected Canon table header: {hdr}")
    return 33


def canon_table_to_pillow_lut(data):
    n = validate_canon_table(data)
    out = []
    for b in range(n):
        for g in range(n):
            for r in range(n):
                ci = ((r*n + g)*n + b)
                rr,gg,bb = struct.unpack_from("<HHH", data, 6+ci*6)
                out.extend((rr/4095.0, gg/4095.0, bb/4095.0))
    return ImageFilter.Color3DLUT(n, out, channels=3)


def transform_canon_table_stack(data, lut_entries, progress=None):
    n = validate_canon_table(data)
    out = bytearray(data)
    samplers = [(CubeSampler(e["cube"]), float(e["opacity"])) for e in lut_entries if e.get("enabled", True) and e.get("opacity",0)>0]
    if not samplers:
        if progress: progress(1.0)
        return bytes(out)
    count = n**3
    for i in range(count):
        o=6+i*6
        r,g,b=struct.unpack_from("<HHH",out,o)
        cur=[r/4095.0,g/4095.0,b/4095.0]
        for sampler,opacity in samplers:
            q=sampler.sample(*cur)
            cur=[clamp01(cur[c]*(1-opacity)+q[c]*opacity) for c in range(3)]
        struct.pack_into("<HHH",out,o,round(cur[0]*4095),round(cur[1]*4095),round(cur[2]*4095))
        if progress and i%1000==0: progress(i/count)
    if progress: progress(1.0)
    return bytes(out)


def modify_basic_0115(base, contrast, saturation, color_tone, sharpness_override=False, sharp_strength=0, fineness=0, threshold=0):
    if len(base) != 32:
        raise ValueError("Expected 32-byte property 0x00000115.")
    b=bytearray(base)
    def put(offset,value): b[offset:offset+4]=int(value).to_bytes(4,"little",signed=True)
    put(4,contrast); put(8,saturation); put(12,color_tone)
    if sharpness_override:
        put(0,sharp_strength); put(24,fineness); put(28,threshold)
    return bytes(b)


def parse_basic_0115(data):
    if len(data) != 32:
        raise ValueError("Expected 32-byte property 0x00000115.")
    def get(offset): return int.from_bytes(data[offset:offset+4], "little", signed=True)
    return {
        "sharp_strength": get(0), "contrast": get(4), "saturation": get(8),
        "color_tone": get(12), "fineness": get(24), "threshold": get(28),
    }


@lru_cache(maxsize=96)
def preview_basic_lut(contrast,saturation,color_tone):
    cf=1.0+contrast*0.115; sf=1.0+saturation*0.10; hue_step=color_tone*5.0/360.0
    def fn(r,g,b):
        r=clamp01((r-0.5)*cf+0.5); g=clamp01((g-0.5)*cf+0.5); b=clamp01((b-0.5)*cf+0.5)
        h,l,s=colorsys.rgb_to_hls(r,g,b); s=clamp01(s*sf)
        deg=h*360.0; delta=abs(((deg-30.0+180.0)%360.0)-180.0); weight=max(0.0,1.0-delta/55.0)
        h=(h+hue_step*weight)%1.0
        return colorsys.hls_to_rgb(h,l,s)
    return ImageFilter.Color3DLUT.generate(17,fn)


@lru_cache(maxsize=128)
def make_exposure_lut(ev):
    gain = 2.0 ** float(ev)
    def fn(r,g,b):
        out=[]
        for c in (r,g,b):
            linear=srgb_to_linear(c)*gain; out.append(linear_to_srgb(linear))
        return tuple(out)
    return ImageFilter.Color3DLUT.generate(17,fn)


def kelvin_to_rgb(kelvin):
    k=max(1000.0,min(40000.0,float(kelvin)))/100.0
    if k<=66:
        r=255; g=99.4708025861*math.log(k)-161.1195681661
        b=0 if k<=19 else 138.5177312231*math.log(k-10)-305.0447927307
    else:
        r=329.698727446*((k-60)**-0.1332047592)
        g=288.1221695283*((k-60)**-0.0755148492); b=255
    return [max(0,min(255,x))/255.0 for x in (r,g,b)]


def wb_gains_from_kelvin(target_kelvin, baseline_kelvin=5200):
    base=kelvin_to_rgb(baseline_kelvin); targ=kelvin_to_rgb(target_kelvin)
    mult=[base[i]/max(targ[i],1e-6) for i in range(3)]
    # The black-body RGB ratio alone becomes much too weak after gamma, highlight
    # clipping and the Canon/PF3 base transform. A calibrated chroma exponent keeps
    # 5200 K neutral while matching the strong blue Tungsten response observed in
    # the native DPP4Lib render much more closely.
    return normalize_rgb_gains([m ** 2.40 for m in mult])


def wb_shift_gains(ab_shift=0.0, gm_shift=0.0):
    """Return post-Canon WB grid gains (+AB=amber, +GM=magenta)."""
    ab=float(ab_shift); gm=float(gm_shift)
    # A Canon WB grid step is deliberately visible but still fine-grained.  These
    # gains operate in linear light, so they are stronger and more predictable
    # than the old gamma-space approximation.
    return normalize_rgb_gains((
        2.0 ** (ab * 0.050),
        2.0 ** (-gm * 0.042),
        2.0 ** (-ab * 0.050),
    ))


@lru_cache(maxsize=128)
def make_wb_lut_from_kelvin(target_kelvin, baseline_kelvin=5200, ab_shift=0.0, gm_shift=0.0):
    mult=list(wb_gains_from_kelvin(target_kelvin,baseline_kelvin))
    # Canon-like preview shift: +AB warms (R up/B down); +GM moves toward magenta (G down).
    shift=wb_shift_gains(ab_shift,gm_shift)
    mult=normalize_rgb_gains([mult[i]*shift[i] for i in range(3)])
    def fn(r,g,b):
        out=[]
        for i,c in enumerate((r,g,b)):
            linear=srgb_to_linear(c)*mult[i]; out.append(linear_to_srgb(linear))
        return tuple(out)
    return ImageFilter.Color3DLUT.generate(17,fn)


@lru_cache(maxsize=128)
def make_wb_shift_lut(ab_shift=0.0, gm_shift=0.0):
    mult=wb_shift_gains(ab_shift,gm_shift)
    def fn(r,g,b):
        out=[]
        for i,c in enumerate((r,g,b)):
            linear=srgb_to_linear(c)*mult[i]; out.append(linear_to_srgb(linear))
        return tuple(out)
    return ImageFilter.Color3DLUT.generate(17,fn)


def make_custom_wb_lut(mult):
    mult=normalize_rgb_gains(mult)
    def fn(r,g,b):
        out=[]
        for i,c in enumerate((r,g,b)):
            linear=srgb_to_linear(c)*mult[i]; out.append(linear_to_srgb(linear))
        return tuple(out)
    return ImageFilter.Color3DLUT.generate(17,fn)


def custom_wb_from_rgb(rgb):
    vals=[max(srgb_to_linear(float(v)/255.0),1e-6) for v in rgb[:3]]
    gray=sum(vals)/3.0
    return list(normalize_rgb_gains([gray/v for v in vals]))


def sample_custom_wb(image,x,y,radius=8):
    """Measure a robust neutral patch and return gains plus sampling metadata.

    Dark and clipped pixels are rejected, then channel medians are measured in
    linear light.  A patch is substantially less sensitive to Bayer/detail noise
    and JPEG artefacts than the previous single-pixel eyedropper.
    """
    im=image.convert("RGB")
    x=int(x);y=int(y);radius=max(2,int(radius))
    left=max(0,x-radius);top=max(0,y-radius)
    right=min(im.width,x+radius+1);bottom=min(im.height,y+radius+1)
    arr=np.asarray(im.crop((left,top,right,bottom)),dtype=np.float32).reshape(-1,3)/255.0
    if not len(arr):
        raise ValueError("The WB sample is outside the image.")
    mask=(arr.max(axis=1)<0.985)&(arr.max(axis=1)>0.035)&(arr.min(axis=1)>0.008)
    usable=arr[mask]
    if len(usable)<max(9,len(arr)//12):
        raise ValueError("Choose a neutral area that is not clipped or nearly black.")
    linear=np.where(usable<=0.04045,usable/12.92,((usable+0.055)/1.055)**2.4)
    luminance=linear@np.asarray([0.2126,0.7152,0.0722],dtype=np.float32)
    lo,hi=np.percentile(luminance,[10,90])
    trimmed=linear[(luminance>=lo)&(luminance<=hi)]
    if len(trimmed)>=9:linear=trimmed
    channels=np.median(linear,axis=0)
    gray=float(channels.mean())
    mult=normalize_rgb_gains([gray/max(float(v),1e-6) for v in channels])
    srgb=np.where(channels<=0.0031308,channels*12.92,1.055*np.power(channels,1/2.4)-0.055)
    representative=tuple(int(round(clamp01(v)*255.0)) for v in srgb)
    return {
        "rgb":representative,
        "mult":list(mult),
        "pixels":int(len(linear)),
        "box":(left,top,right,bottom),
        "point":(x,y),
    }


def extract_largest_embedded_jpeg(path, max_segment=64*1024*1024):
    path=Path(path); best=None; best_area=0
    with path.open("rb") as f:
        mm=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
        try:
            pos=0; candidates=0
            while candidates<40:
                soi=mm.find(b"\xff\xd8\xff",pos)
                if soi<0: break
                eoi=mm.find(b"\xff\xd9",soi+4)
                if eoi<0: break
                length=eoi+2-soi; pos=soi+3; candidates+=1
                if length<16000 or length>max_segment: continue
                try:
                    im=Image.open(io.BytesIO(mm[soi:eoi+2])); im.load(); im=ImageOps.exif_transpose(im).convert("RGB")
                    area=im.width*im.height
                    if area>best_area: best,best_area=im,area
                except Exception: pass
        finally: mm.close()
    if best is None: raise RuntimeError("No usable embedded JPEG preview was found.")
    return best


def detect_embedded_raw_metadata(path,max_segment=64*1024*1024):
    """Read non-sensitive camera metadata from the largest embedded JPEG."""
    path=Path(path);best=None;best_area=0
    try:
        with path.open("rb") as f:
            mm=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
            try:
                pos=0;candidates=0
                while candidates<40:
                    soi=mm.find(b"\xff\xd8\xff",pos)
                    if soi<0:break
                    eoi=mm.find(b"\xff\xd9",soi+4)
                    if eoi<0:break
                    length=eoi+2-soi;pos=soi+3;candidates+=1
                    if length<16000 or length>max_segment:continue
                    try:
                        im=Image.open(io.BytesIO(mm[soi:eoi+2]));area=im.width*im.height
                        if area<=best_area:continue
                        exif=im.getexif();best_area=area
                        best={
                            "camera_make":str(exif.get(0x010F) or "").strip() or None,
                            "camera_model":str(exif.get(0x0110) or "").strip() or None,
                            "exif_orientation":int(exif.get(0x0112) or 1),
                            "embedded_preview_size":(int(im.width),int(im.height)),
                        }
                    except Exception:pass
            finally:mm.close()
    except Exception:pass
    return best or {"camera_make":None,"camera_model":None,"exif_orientation":None}


def decode_canon_raw(path, wb_mode="As Shot", shot_select=0):
    if rawpy is None:
        raise RuntimeError("rawpy is not installed. Run the launcher so RAW support can be installed.")
    shot_select=max(0,int(shot_select)); raw=rawpy.RawPy()
    try:
        raw.open_file(str(path)); raw.set_unpack_params(shot_select=shot_select); raw.unpack(); sizes=raw.sizes
        use_camera=wb_mode=="As Shot"; use_auto=wb_mode=="Auto"
        # Preview baseline: allow LibRaw to normalize RAW brightness conservatively.
        # The old no_auto_bright=True path exposed sensor headroom directly and
        # made many Canon RAW files look ~1 EV or more too dark for visual editing.
        # 0.001 (0.1% clipped pixels) is deliberately more conservative than
        # LibRaw/dcraw's legacy 0.01 default. Exposure in the UI is applied later
        # and remains relative to this baseline.
        kwargs=dict(half_size=True,use_camera_wb=use_camera,use_auto_wb=use_auto,output_color=rawpy.ColorSpace.sRGB,
                    output_bps=8,no_auto_bright=False,auto_bright_thr=0.001,bright=1.0,gamma=(2.222,4.5))
        try:
            arr=raw.postprocess(**kwargs); wb_fallback=False
        except Exception:
            if use_camera:
                kwargs["use_camera_wb"]=False; arr=raw.postprocess(**kwargs); wb_fallback=True
            else: raise
        im=Image.fromarray(arr,"RGB")
        metadata=detect_embedded_raw_metadata(path)
        return im, {
            "decoder":"rawpy/LibRaw", "shot_select":shot_select, "wb_mode":wb_mode, "wb_fallback":wb_fallback,
            "raw_size":(getattr(sizes,"raw_width",None),getattr(sizes,"raw_height",None)),
            "visible_size":(getattr(sizes,"width",None),getattr(sizes,"height",None)), "render_size":im.size,
            "raw_type":str(getattr(raw,"raw_type","unknown")),
            "brightness_baseline":"LibRaw auto-bright 0.1%",
            **metadata,
        }
    finally: raw.close()


class EdsCFParse:
    def __init__(self,dll_path):
        self.dll_path=Path(dll_path); self._dll_dir=None
        if not hasattr(ctypes,"WinDLL"):
            raise RuntimeError("Canon EdsCFParse.dll requires Windows.")
        if hasattr(os,"add_dll_directory"):
            try:self._dll_dir=os.add_dll_directory(str(self.dll_path.parent))
            except Exception:pass
        self.dll=ctypes.WinDLL(str(self.dll_path)); U32=ctypes.c_uint32; VOIDP=ctypes.c_void_p; PVOIDP=ctypes.POINTER(VOIDP)
        self.dll.EdsCfpInitialize.argtypes=[]; self.dll.EdsCfpInitialize.restype=U32
        self.dll.EdsCfpTerminate.argtypes=[]; self.dll.EdsCfpTerminate.restype=U32
        self.dll.EdsCfpCreateRef.argtypes=[ctypes.c_char_p,U32,U32,PVOIDP]; self.dll.EdsCfpCreateRef.restype=U32
        self.dll.EdsCfpRelease.argtypes=[VOIDP]; self.dll.EdsCfpRelease.restype=U32
        self.dll.EdsCfpGetPropertySize.argtypes=[VOIDP,U32,U32,ctypes.POINTER(U32),ctypes.POINTER(U32)]; self.dll.EdsCfpGetPropertySize.restype=U32
        self.dll.EdsCfpGetPropertyData.argtypes=[VOIDP,U32,U32,U32,VOIDP]; self.dll.EdsCfpGetPropertyData.restype=U32
        self.dll.EdsCfpSetPropertyData.argtypes=[VOIDP,U32,U32,U32,VOIDP]; self.dll.EdsCfpSetPropertyData.restype=U32
        self.dll.EdsCfpReflectProperty.argtypes=[VOIDP]; self.dll.EdsCfpReflectProperty.restype=U32
    @staticmethod
    def check(rc,what):
        if rc!=0: raise RuntimeError(f"{what} failed: Canon rc=0x{rc:08X} ({rc})")
    def initialize(self): self.check(self.dll.EdsCfpInitialize(),"EdsCfpInitialize")
    def terminate(self): self.check(self.dll.EdsCfpTerminate(),"EdsCfpTerminate")
    def create_ref(self,path,disposition,access):
        ref=ctypes.c_void_p(); self.check(self.dll.EdsCfpCreateRef(win_bytes(path),disposition,access,ctypes.byref(ref)),f"EdsCfpCreateRef({Path(path).name})")
        if not ref.value: raise RuntimeError("Canon returned a null PF3 reference.")
        return ref
    def release(self,ref):
        if ref and ref.value:self.dll.EdsCfpRelease(ref)
    def get_property(self,ref,prop,expected=None):
        dt=ctypes.c_uint32(); sz=ctypes.c_uint32(); self.check(self.dll.EdsCfpGetPropertySize(ref,prop,0,ctypes.byref(dt),ctypes.byref(sz)),f"GetPropertySize(0x{prop:08X})")
        if expected is not None and sz.value!=expected: raise RuntimeError(f"0x{prop:08X}: Canon reports {sz.value} bytes; expected {expected}.")
        buf=(ctypes.c_ubyte*sz.value)(); self.check(self.dll.EdsCfpGetPropertyData(ref,prop,0,sz.value,ctypes.cast(buf,ctypes.c_void_p)),f"GetPropertyData(0x{prop:08X})")
        return bytes(buf)
    def set_property(self,ref,prop,data):
        buf=(ctypes.c_ubyte*len(data)).from_buffer_copy(data); self.check(self.dll.EdsCfpSetPropertyData(ref,prop,0,len(data),ctypes.cast(buf,ctypes.c_void_p)),f"SetPropertyData(0x{prop:08X})")
    def reflect(self,ref): self.check(self.dll.EdsCfpReflectProperty(ref),"EdsCfpReflectProperty")


@lru_cache(maxsize=1)
def identity_canon_table():
    """Build our own 33³/12-bit identity table; no Canon table blob is bundled."""
    n=33;out=bytearray(6+n**3*6);struct.pack_into("<HHH",out,0,12,3,n)
    for r in range(n):
        for g in range(n):
            for b in range(n):
                index=((r*n+g)*n+b);offset=6+index*6
                struct.pack_into("<HHH",out,offset,round(r*4095/(n-1)),round(g*4095/(n-1)),round(b*4095/(n-1)))
    return bytes(out)


def generated_pf3_properties(style="Neutral",title=None):
    """Generate a conservative PF3 property set without embedding a Canon PF3.

    Canon's EdsCFParse serializes and checksums the result. The base Picture Style
    selector remains Canon-native; LUT tables start as an identity transform and
    are populated by the user's LUT stack during export.
    """
    style=style if style in PICTURE_STYLE_IDS else "Neutral"
    title=(title or style).encode("ascii",errors="replace")[:31]
    table=identity_canon_table()
    props={prop:bytes(expected) for prop,expected in PROPERTY_ORDER}
    props[0x00000114]=int(PICTURE_STYLE_IDS[style]).to_bytes(4,"little")
    props[0x00000115]=bytes(32)
    props[0x40001002]=title+b"\x00"*(32-len(title))
    # User-defined marker and format version are small public field values, not
    # copied resources. EdsCFParse will reject them if an installed version differs.
    props[0x4000100D]=b"UD "
    props[0x4000100C]=b"\x01\x00"
    props[0x40001070]=table
    props[0x40001071]=table
    return props


def create_generated_base_pf3(dll_path,output_path,style="Neutral"):
    output_path=Path(output_path);output_path.parent.mkdir(parents=True,exist_ok=True)
    api=EdsCFParse(dll_path);ref=None
    try:
        api.initialize();ref=api.create_ref(output_path,CREATE_ALWAYS,WRITE)
        props=generated_pf3_properties(style,style)
        for prop,expected in PROPERTY_ORDER:
            api.set_property(ref,prop,props[prop])
        api.reflect(ref)
    finally:
        try:
            if ref:api.release(ref)
        except Exception:pass
        try:api.terminate()
        except Exception:pass
    validate_pf3_header(output_path)
    return output_path


def ensure_runtime_base_pf3(dll_path,style="Neutral",directory=None):
    style=style if style in PICTURE_STYLE_IDS else "Neutral"
    directory=Path(directory or (runtime_cache_dir()/"generated_pf3_bases"))
    path=directory/(style.lower().replace(" ","_")+".pf3")
    try:
        if path.is_file() and path.stat().st_size==434511:
            validate_pf3_header(path);return path
    except Exception:
        pass
    return create_generated_base_pf3(dll_path,path,style)


def read_base_properties(dll_path,base_path,wanted=None):
    api=EdsCFParse(dll_path); ref=None
    try:
        api.initialize(); ref=api.create_ref(base_path,OPEN_EXISTING,READ); props={}
        for prop,expected in (PROPERTY_ORDER if wanted is None else wanted): props[prop]=api.get_property(ref,prop,expected)
        return props
    finally:
        try:
            if ref: api.release(ref)
        except Exception: pass
        try: api.terminate()
        except Exception: pass


def resolve_validated_base_pf3(dll_path,style,search_directories=()):
    """Resolve a user/local validated base without bundling it in public builds."""
    if style not in PICTURE_STYLE_IDS:raise ValueError(f"Unsupported Canon base Picture Style: {style}")
    slug=style.lower().replace(" ","_")
    names=(f"BASE_{style.upper().replace(' ','_')}_RP.pf3",f"{slug}.pf3")
    directories=[]
    env=os.environ.get("CANON_STYLE_STUDIO_BASE_PF3_DIR")
    for item in (*search_directories,env):
        if not item:continue
        path=Path(item)
        for candidate in (path,path/"SOURCE",path/"bases"):
            try:candidate=candidate.resolve()
            except Exception:pass
            if candidate not in directories:directories.append(candidate)
    for directory in directories:
        for name in names:
            path=directory/name
            if not path.is_file():continue
            try:
                validate_pf3_header(path)
                props=read_base_properties(dll_path,path,wanted=[(0x00000114,4)])
                style_id=int.from_bytes(props[0x00000114],"little")
                if style_id!=PICTURE_STYLE_IDS[style]:continue
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                exact=digest.lower()==VALIDATED_BASE_SHA256.get(style,"").lower()
                return {"path":path,"style":style,"source":"validated local PF3","validated":exact,"sha256":digest}
            except Exception:
                continue
    return None


def inspect_pf3(dll_path, path):
    validate_pf3_header(path)
    props=read_base_properties(dll_path,path,wanted=[(0x40001071,215628),(0x40001070,215628),(0x00000115,32),(0x40001002,32),(0x00000114,4)])
    title=props[0x40001002].split(b"\x00",1)[0].decode("ascii",errors="replace") or Path(path).stem
    return {"path":Path(path),"title":title,"basic":parse_basic_0115(props[0x00000115]),"table":props[0x40001071],"table70":props[0x40001070],"props":props}


def export_pf3(dll_path,base_path,output_path,lut_entries,controls,title,log=lambda s:None,progress=lambda v:None):
    validate_pf3_header(base_path); api=EdsCFParse(dll_path); src=dst=None
    try:
        api.initialize(); log("Canon EdsCFParse initialized."); src=api.create_ref(base_path,OPEN_EXISTING,READ); props={}
        for prop,expected in PROPERTY_ORDER: props[prop]=api.get_property(src,prop,expected)
        props[0x00000115]=modify_basic_0115(props[0x00000115],controls["contrast"],controls["saturation"],controls["color_tone"],controls.get("sharpness_override",False),controls.get("sharp_strength",0),controls.get("fineness",2),controls.get("threshold",4))
        effective=list(lut_entries)
        recipe_wb=recipe_wb_lut_entry(controls.get("recipe_wb"),size=33)
        if recipe_wb:effective.insert(0,recipe_wb)
        creative=creative_lut_entry(controls.get("creative"),size=33)
        if creative:effective.append(creative)
        enabled=[e for e in effective if e.get("enabled") and e.get("opacity",0)>0]
        if enabled:
            for idx,prop in enumerate(BIG_TABLES):
                log(f"Composing LUT stack into 0x{prop:08X}…")
                props[prop]=transform_canon_table_stack(props[prop],enabled,progress=lambda v,idx=idx:progress((idx+v)/2.0))
        else: progress(1.0)
        output_path=Path(output_path); output_path.parent.mkdir(parents=True,exist_ok=True)
        if output_path.resolve()==Path(base_path).resolve(): raise RuntimeError("Output cannot overwrite the selected Canon base.")
        dst=api.create_ref(output_path,CREATE_ALWAYS,WRITE)
        for prop,expected in PROPERTY_ORDER:
            data=props[prop]
            if prop==0x40001002:
                t=title.encode("ascii",errors="replace")[:31]; data=t+b"\x00"*(32-len(t))
            api.set_property(dst,prop,data)
        log("Serializing/checksumming with Canon DLL…"); api.reflect(dst)
    finally:
        try:
            if dst:api.release(dst)
        except Exception:pass
        try:
            if src:api.release(src)
        except Exception:pass
        try:api.terminate()
        except Exception:pass
    size=validate_pf3_header(output_path)
    if size!=434511: raise RuntimeError(f"Output PF3 is {size:,} bytes; expected 434,511. Do not register it.")
    sha=hashlib.sha256(Path(output_path).read_bytes()).hexdigest(); return size,sha


class CanonRenderEngine:
    """Shared state-free rendering/cache layer used by both V0.3.6 and V0.4.x UI."""
    def __init__(self):
        self.base_cache={}; self.pillow_cache={}; self.composite_cache={}; self.stack33_cache={}; self.creative_cache={}; self.recipe_wb_cache={}

    def clear(self):
        self.base_cache.clear(); self.pillow_cache.clear(); self.composite_cache.clear(); self.stack33_cache.clear(); self.creative_cache.clear(); self.recipe_wb_cache.clear()

    def load_base(self,dll_path,base_path):
        key=(file_fingerprint(Path(dll_path)),file_fingerprint(Path(base_path)))
        if key not in self.base_cache:
            props=read_base_properties(dll_path,base_path,wanted=[(0x40001071,215628),(0x00000115,32)])
            self.base_cache[key]={"table":props[0x40001071],"basic":props[0x00000115],"lut":canon_table_to_pillow_lut(props[0x40001071])}
        return self.base_cache[key]

    def pillow_for_cube(self,cube):
        key=cube.get("fingerprint") or str(id(cube))
        if key not in self.pillow_cache:
            self.pillow_cache[key]=cube_to_pillow_lut(cube)
            if len(self.pillow_cache)>96:self.pillow_cache.pop(next(iter(self.pillow_cache)))
        return self.pillow_cache[key]

    @staticmethod
    def stack_key(luts):
        return tuple((e["cube"].get("fingerprint",e["cube"].get("title","")),bool(e.get("enabled",True)),round(float(e.get("opacity",1.0)),6)) for e in luts)

    def effective_luts(self,luts,controls):
        effective=list(luts)
        normalized_wb=normalize_recipe_wb((controls or {}).get("recipe_wb"))
        wb_key=json.dumps(normalized_wb,sort_keys=True,separators=(",",":"))
        if wb_key not in self.recipe_wb_cache:
            self.recipe_wb_cache[wb_key]=recipe_wb_lut_entry(normalized_wb,size=33)
            if len(self.recipe_wb_cache)>24:self.recipe_wb_cache.pop(next(iter(self.recipe_wb_cache)))
        recipe_wb=self.recipe_wb_cache[wb_key]
        if recipe_wb:effective.insert(0,recipe_wb)
        normalized=normalize_creative_controls((controls or {}).get("creative"))
        key=json.dumps(normalized,sort_keys=True,separators=(",",":"))
        if key not in self.creative_cache:
            self.creative_cache[key]=creative_lut_entry(normalized,size=33)
            if len(self.creative_cache)>12:self.creative_cache.pop(next(iter(self.creative_cache)))
        creative=self.creative_cache[key]
        if creative:effective.append(creative)
        return effective

    def canon33_lut(self,dll_path,base_path,luts):
        base=self.load_base(dll_path,base_path); key=(file_fingerprint(Path(base_path)),self.stack_key(luts))
        if key not in self.composite_cache:
            table=transform_canon_table_stack(base["table"],luts)
            self.composite_cache[key]={"table":table,"lut":canon_table_to_pillow_lut(table)}
        return self.composite_cache[key]


    def quantized_stack_lut(self, luts):
        """Resample only the user LUT stack to a 33^3 LUT.

        For Canon RAW preview the Canon base style is already rendered by DPP4Lib,
        so the base PF3 table must NOT be applied a second time. This method simulates
        only the 33^3 quantization of the user LUT stack on top of the Canon render.
        """
        enabled=[e for e in luts if e.get("enabled",True) and float(e.get("opacity",0))>0]
        if not enabled:
            return None
        key=self.stack_key(enabled)
        if key in self.stack33_cache:
            return self.stack33_cache[key]
        samplers=[(CubeSampler(e["cube"]),float(e.get("opacity",1.0))) for e in enabled]
        def cb(r,g,b):
            x=(float(r),float(g),float(b))
            for sampler,opacity in samplers:
                y=sampler.sample(*x)
                if opacity>=0.999:
                    x=y
                else:
                    x=tuple(x[i]*(1.0-opacity)+y[i]*opacity for i in range(3))
            return tuple(clamp01(v) for v in x)
        lut=ImageFilter.Color3DLUT.generate(33,cb)
        self.stack33_cache[key]=lut
        if len(self.stack33_cache)>24:self.stack33_cache.pop(next(iter(self.stack33_cache)))
        return lut

    def render_from_canon_base(self, canon_base, luts, controls, preview_mode="working", post_wb=None, max_side=1800):
        """Apply Canon Style Studio edits on top of a real Canon DPP4Lib render."""
        # DPP4Lib already returns an oriented RGB frame. Reusing it here avoids a
        # full extra 75–80 MB copy for native EOS RP zoom renders; every operation
        # below that changes pixels returns a new Pillow image.
        im=canon_base if canon_base.mode=="RGB" else canon_base.convert("RGB")
        if max(im.size)>max_side:
            im=im.copy();im.thumbnail((max_side,max_side),Image.Resampling.LANCZOS)
        post_wb=post_wb or {}
        ab_shift=post_wb.get("ab_shift",0);gm_shift=post_wb.get("gm_shift",0)
        gains=(1.0,1.0,1.0)
        if abs(float(ab_shift))>1e-9 or abs(float(gm_shift))>1e-9:
            gains=wb_shift_gains(ab_shift,gm_shift)
        if post_wb.get("custom_wb_mult"):
            custom=normalize_rgb_gains(post_wb["custom_wb_mult"])
            gains=tuple(gains[i]*custom[i] for i in range(3))
        if any(abs(g-1.0)>1e-9 for g in gains):
            im=apply_linear_rgb_gains(im,gains)
        input_view=im
        effective=self.effective_luts(luts,controls)
        if preview_mode=="canon33":
            lut=self.quantized_stack_lut(effective)
            result=input_view if lut is None else input_view.filter(lut)
        else:
            result=input_view
            for e in effective:
                if not e.get("enabled",True) or float(e.get("opacity",0))<=0:continue
                transformed=result.filter(self.pillow_for_cube(e["cube"]));opacity=float(e.get("opacity",1.0))
                result=transformed if opacity>=0.999 else Image.blend(result,transformed,opacity)
        # DPP standalone sharpening properties are not visually active yet. Preserve
        # the PF3-native export values and provide the previous clearly-marked preview approximation.
        if controls.get("sharpness_override") and controls.get("sharp_strength",0)>0:
            result=ImageEnhance.Sharpness(result).enhance(1.0+controls["sharp_strength"]*0.28)
        return input_view,result

    def render(self,source,dll_path,base_path,luts,controls,preview_mode="working",raw_preview=None,max_side=1800):
        im=ImageOps.exif_transpose(source).convert("RGB")
        if max(im.size)>max_side:
            im=im.copy(); im.thumbnail((max_side,max_side),Image.Resampling.LANCZOS)
        raw_preview=raw_preview or {}
        ev=float(raw_preview.get("exposure",0.0))
        gains=[2.0**ev]*3
        wb_kelvin=raw_preview.get("kelvin")
        if wb_kelvin is not None:
            wb=wb_gains_from_kelvin(wb_kelvin)
            gains=[gains[i]*wb[i] for i in range(3)]
        ab_shift=raw_preview.get("ab_shift",0); gm_shift=raw_preview.get("gm_shift",0)
        if abs(float(ab_shift)) > 1e-9 or abs(float(gm_shift)) > 1e-9:
            shift=wb_shift_gains(ab_shift,gm_shift)
            gains=[gains[i]*shift[i] for i in range(3)]
        if raw_preview.get("custom_wb_mult"):
            custom=normalize_rgb_gains(raw_preview["custom_wb_mult"])
            gains=[gains[i]*custom[i] for i in range(3)]
        if any(abs(g-1.0)>1e-9 for g in gains):
            im=apply_linear_rgb_gains(im,gains)
        input_view=im
        effective=self.effective_luts(luts,controls)
        if preview_mode=="canon33":
            lut=self.quantized_stack_lut(effective)
            result=input_view if lut is None else input_view.filter(lut)
        else:
            # Public Alpha remains usable for ordinary images/LUT work when PSE is
            # missing. A generated runtime base is identity, while an imported PF3
            # still supplies its explicit table approximation.
            result=input_view
            if dll_path and base_path and Path(base_path).is_file():
                result=input_view.filter(self.load_base(dll_path,base_path)["lut"])
            for e in effective:
                if not e.get("enabled",True) or float(e.get("opacity",0))<=0: continue
                transformed=result.filter(self.pillow_for_cube(e["cube"])); opacity=float(e.get("opacity",1.0))
                result=transformed if opacity>=0.999 else Image.blend(result,transformed,opacity)
        if controls.get("contrast",0) or controls.get("saturation",0) or controls.get("color_tone",0):
            result=result.filter(preview_basic_lut(controls.get("contrast",0),controls.get("saturation",0),controls.get("color_tone",0)))
        if controls.get("sharpness_override") and controls.get("sharp_strength",0)>0:
            result=ImageEnhance.Sharpness(result).enhance(1.0+controls["sharp_strength"]*0.28)
        return input_view,result


def load_reference_image(path, wb_mode="As Shot", shot_select=0):
    path=Path(path); ext=path.suffix.lower()
    if ext in CANON_STRONG_RAW_EXTENSIONS:
        try:
            return (*decode_canon_raw(path,wb_mode=wb_mode,shot_select=shot_select),True,False)
        except Exception as e:
            im=extract_largest_embedded_jpeg(path); return im,{"decoder":"embedded JPEG","raw_error":str(e)},True,True
    if ext in {".tif",".tiff"}:
        try:
            im=Image.open(path); im.load(); return ImageOps.exif_transpose(im).convert("RGB"),{},False,False
        except Exception:
            try: return (*decode_canon_raw(path,wb_mode=wb_mode,shot_select=shot_select),True,False)
            except Exception as e:
                im=extract_largest_embedded_jpeg(path); return im,{"decoder":"embedded JPEG","raw_error":str(e)},True,True
    im=Image.open(path); im.load(); return ImageOps.exif_transpose(im).convert("RGB"),{},False,False
