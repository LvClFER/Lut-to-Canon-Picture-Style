from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Any

import numpy as np


DEFAULT_RECIPE = {
    "highlight": 0,
    "shadow": 0,
    "color": 0,
    "color_chrome": "Off",
    "color_chrome_fx_blue": "Off",
}



def _clampi(v, lo, hi):
    return max(lo, min(hi, int(round(float(v)))))


def normalize_recipe_settings(settings: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Normalize only controls that are actually baked into the 3D LUT."""
    s = dict(DEFAULT_RECIPE)
    if settings:
        # Ignore obsolete camera-side/unsupported keys from older reports.
        for key in DEFAULT_RECIPE:
            if key in settings:
                s[key] = settings[key]

    def level(name):
        v = str(s.get(name, "Off")).strip().title()
        return v if v in {"Off", "Weak", "Strong"} else "Off"

    return {
        "highlight": _clampi(s.get("highlight", 0), -2, 4),
        "shadow": _clampi(s.get("shadow", 0), -2, 4),
        "color": _clampi(s.get("color", 0), -4, 4),
        "color_chrome": level("color_chrome"),
        "color_chrome_fx_blue": level("color_chrome_fx_blue"),
    }


def recipe_is_neutral(settings: Dict[str, Any] | None) -> bool:
    s = normalize_recipe_settings(settings)
    return (
        s["highlight"] == 0
        and s["shadow"] == 0
        and s["color"] == 0
        and s["color_chrome"] == "Off"
        and s["color_chrome_fx_blue"] == "Off"
    )


def smoothstep(edge0, edge1, x):
    x = np.asarray(x, dtype=np.float64)
    if edge1 == edge0:
        return (x >= edge1).astype(np.float64)
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def srgb_to_linear(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    # Keep sign for temporary out-of-gamut values. Final gamut compression clips safely.
    return np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * np.maximum(rgb, 0.0) ** (1.0/2.4) - 0.055)


def linear_srgb_to_oklab(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    r, g, b = np.moveaxis(rgb, -1, 0)
    l = 0.4122214708*r + 0.5363325363*g + 0.0514459929*b
    m = 0.2119034982*r + 0.6806995451*g + 0.1073969566*b
    s = 0.0883024619*r + 0.2817188376*g + 0.6299787005*b
    l_ = np.cbrt(l); m_ = np.cbrt(m); s_ = np.cbrt(s)
    L = 0.2104542553*l_ + 0.7936177850*m_ - 0.0040720468*s_
    a = 1.9779984951*l_ - 2.4285922050*m_ + 0.4505937099*s_
    bb = 0.0259040371*l_ + 0.7827717662*m_ - 0.8086757660*s_
    return np.stack([L, a, bb], axis=-1)


def oklab_to_linear_srgb(lab):
    lab = np.asarray(lab, dtype=np.float64)
    L, a, b = np.moveaxis(lab, -1, 0)
    l_ = L + 0.3963377774*a + 0.2158037573*b
    m_ = L - 0.1055613458*a - 0.0638541728*b
    s_ = L - 0.0894841775*a - 1.2914855480*b
    l = l_**3; m = m_**3; s = s_**3
    r = +4.0767416621*l - 3.3077115913*m + 0.2309699292*s
    g = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s
    bb = -0.0041960863*l - 0.7034186147*m + 1.7076147010*s
    return np.stack([r, g, bb], axis=-1)


def _hue_gaussian(h_deg, center, sigma):
    d = np.abs((h_deg - center + 180.0) % 360.0 - 180.0)
    return np.exp(-0.5 * (d / sigma) ** 2)



def _gamut_map_oklch(L, C, h):
    """Reduce chroma only when needed to fit linear sRGB, preserving L/h as far as possible."""
    L = np.asarray(L, dtype=np.float64)
    C = np.maximum(np.asarray(C, dtype=np.float64), 0.0)
    h = np.asarray(h, dtype=np.float64)
    rad = np.deg2rad(h)

    def rgb_for(chroma):
        a = chroma * np.cos(rad)
        b = chroma * np.sin(rad)
        return oklab_to_linear_srgb(np.stack([L, a, b], axis=-1))

    rgb = rgb_for(C)
    good = np.all((rgb >= 0.0) & (rgb <= 1.0), axis=-1)
    if np.all(good):
        return np.clip(linear_to_srgb(rgb), 0.0, 1.0)

    lo = np.zeros_like(C)
    hi = C.copy()
    # Already-in-gamut pixels keep their original chroma.
    lo[good] = C[good]
    hi[good] = C[good]
    for _ in range(10):
        mid = (lo + hi) * 0.5
        test = rgb_for(mid)
        ok = np.all((test >= 0.0) & (test <= 1.0), axis=-1)
        lo = np.where(ok, mid, lo)
        hi = np.where(ok, hi, mid)
    rgb = rgb_for(lo)
    return np.clip(linear_to_srgb(rgb), 0.0, 1.0)


def apply_post_recipe(rgb, settings):
    s = normalize_recipe_settings(settings)
    rgb = np.clip(np.asarray(rgb, dtype=np.float64), 0.0, 1.0)
    lab = linear_srgb_to_oklab(srgb_to_linear(rgb))
    L = lab[...,0].copy()
    a = lab[...,1]; b = lab[...,2]
    C = np.sqrt(a*a + b*b)
    h = (np.degrees(np.arctan2(b, a)) + 360.0) % 360.0

    # Tone-control approximation: negative highlight softens/lowers upper tones;
    # positive shadow deepens lower tones.
    hi = float(s["highlight"])
    if hi:
        hm = smoothstep(0.52, 0.90, L) * (1.0 - smoothstep(0.97, 1.0, L))
        L += hi * 0.0105 * hm
    sh = float(s["shadow"])
    if sh:
        sm = (1.0 - smoothstep(0.16, 0.58, L)) * smoothstep(0.015, 0.12, L)
        L -= sh * 0.0120 * sm

    # Generic Color adjustment in perceptual chroma, with a soft ceiling near already-high chroma.
    color = float(s["color"])
    if color:
        raw_gain = 1.0 + color * 0.050
        protect = smoothstep(0.20, 0.38, C)
        eff_gain = 1.0 + (raw_gain - 1.0) * (1.0 - 0.55*protect)
        C *= np.maximum(eff_gain, 0.0)

    # Use the source RGB peak as a proxy for strongly-exposed saturated color.
    peak = np.max(rgb, axis=-1)
    sat_mask = smoothstep(0.055, 0.22, C)
    peak_mask = smoothstep(0.50, 0.94, peak)

    chrome_level = {"Off":0.0, "Weak":0.50, "Strong":1.0}[s["color_chrome"]]
    if chrome_level:
        # Weighted toward red/orange/yellow/green, with a little magenta support.
        hue_w = np.maximum.reduce([
            1.00*_hue_gaussian(h,   5.0, 34.0),
            0.92*_hue_gaussian(h,  42.0, 30.0),
            0.72*_hue_gaussian(h,  82.0, 30.0),
            0.78*_hue_gaussian(h, 132.0, 38.0),
            0.42*_hue_gaussian(h, 330.0, 30.0),
        ])
        e = np.clip(sat_mask * peak_mask * hue_w, 0.0, 1.0) * chrome_level
        L -= 0.028 * e
        C *= (1.0 - 0.018 * e)

    blue_level = {"Off":0.0, "Weak":0.50, "Strong":1.0}[s["color_chrome_fx_blue"]]
    if blue_level:
        blue_w = np.maximum(
            0.65*_hue_gaussian(h, 195.0, 30.0),
            1.00*_hue_gaussian(h, 235.0, 38.0),
        )
        e = np.clip(sat_mask * peak_mask * blue_w, 0.0, 1.0) * blue_level
        L -= 0.038 * e
        C *= (1.0 + 0.012 * e)

    L = np.clip(L, 0.0, 1.0)
    return _gamut_map_oklch(L, C, h)


def _sample_cube_vectorized(cube, rgb):
    """Trilinear sample a parsed canon_engine cube at Nx3 RGB positions."""
    n = int(cube["size"])
    vals = np.asarray(cube["values"], dtype=np.float64).reshape(n, n, n, 3)
    # Parsed .cube values are R-fastest in flattened order. Reshape is [B,G,R,C].
    dmin = np.asarray(cube["domain_min"], dtype=np.float64)
    dmax = np.asarray(cube["domain_max"], dtype=np.float64)
    p = (np.asarray(rgb, dtype=np.float64) - dmin) / (dmax - dmin)
    p = np.clip(p, 0.0, 1.0) * (n - 1)
    r0 = np.floor(p[:,0]).astype(np.int32); g0 = np.floor(p[:,1]).astype(np.int32); b0 = np.floor(p[:,2]).astype(np.int32)
    r1 = np.minimum(r0+1, n-1); g1 = np.minimum(g0+1, n-1); b1 = np.minimum(b0+1, n-1)
    tr = (p[:,0]-r0)[:,None]; tg = (p[:,1]-g0)[:,None]; tb = (p[:,2]-b0)[:,None]
    c000=vals[b0,g0,r0]; c100=vals[b0,g0,r1]
    c010=vals[b0,g1,r0]; c110=vals[b0,g1,r1]
    c001=vals[b1,g0,r0]; c101=vals[b1,g0,r1]
    c011=vals[b1,g1,r0]; c111=vals[b1,g1,r1]
    c00=c000*(1-tr)+c100*tr; c10=c010*(1-tr)+c110*tr
    c01=c001*(1-tr)+c101*tr; c11=c011*(1-tr)+c111*tr
    c0=c00*(1-tg)+c10*tg; c1=c01*(1-tg)+c11*tg
    return c0*(1-tb)+c1*tb


def bake_recipe_cube(base_cube, settings=None, size=33):
    """Bake the supported generic LUT adjustments into one standard RGB CUBE dict."""
    s = normalize_recipe_settings(settings)
    size = int(size)
    rows = []
    # Standard .cube ordering: R fastest, then G, then B.
    for b in range(size):
        bz = b/(size-1)
        for g in range(size):
            gy = g/(size-1)
            for r in range(size):
                rows.append((r/(size-1), gy, bz))
    inp = np.asarray(rows, dtype=np.float64)
    base_out = _sample_cube_vectorized(base_cube, inp)
    final = apply_post_recipe(base_out, s)
    title = f"{base_cube.get('title','LUT')} + adjustments"
    fp_src = str(base_cube.get("fingerprint", base_cube.get("title", "lut")))
    fp = hashlib.sha256((fp_src + repr(sorted(s.items())) + f"|{size}").encode("utf-8")).hexdigest()
    return {
        "path": None,
        "title": title,
        "size": size,
        "domain_min": [0.0,0.0,0.0],
        "domain_max": [1.0,1.0,1.0],
        "values": final.astype(np.float32).reshape(-1),
        "source": "generated_adjustments",
        "bit_depth": None,
        "color_space": "sRGB-like working RGB",
        "lossy": False,
        "fingerprint": "recipe:"+fp,
        "recipe": s,
    }


def write_cube(path, cube, title=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(cube["size"])
    vals = np.asarray(cube["values"], dtype=np.float64).reshape(-1,3)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f'TITLE "{title or cube.get("title", path.stem)}"\n')
        f.write(f"LUT_3D_SIZE {n}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n\n")
        for r,g,b in vals:
            f.write(f"{r:.9f} {g:.9f} {b:.9f}\n")
    return path


def recipe_summary(settings):
    s = normalize_recipe_settings(settings)
    return (
        f"Highlight {s['highlight']:+d} | "
        f"Shadow {s['shadow']:+d} | "
        f"Color {s['color']:+d} | "
        f"Color Chrome {s['color_chrome']} | "
        f"FX Blue {s['color_chrome_fx_blue']}"
    )
