from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import numpy as np


TONE_X = np.asarray([0.0, 0.25, 0.50, 0.75, 1.0], dtype=np.float64)
IDENTITY_TONE_CURVE = [0.0, 0.25, 0.50, 0.75, 1.0]
AXIS_NAMES = ("Red", "Yellow", "Green", "Cyan", "Blue", "Magenta")
AXIS_CENTERS = {
    "Red": 29.0,
    "Yellow": 90.0,
    "Green": 142.0,
    "Cyan": 195.0,
    "Blue": 264.0,
    "Magenta": 330.0,
}


def _default_axes():
    return {name: {"hue": 0, "saturation": 0, "luminance": 0} for name in AXIS_NAMES}


DEFAULT_CREATIVE_CONTROLS = {
    "recipe_highlight": 0,
    "recipe_shadow": 0,
    "recipe_color": 0,
    "tone_curve": list(IDENTITY_TONE_CURVE),
    "color_axes": _default_axes(),
    "color_chrome": "Off",
    "color_chrome_fx_blue": "Off",
}


def _clampi(value, minimum, maximum):
    return max(minimum, min(maximum, int(round(float(value)))))


def _level(value):
    value = str(value or "Off").strip().title()
    return value if value in {"Off", "Weak", "Strong"} else "Off"


def normalize_creative_controls(settings=None):
    source = settings if isinstance(settings, dict) else {}
    raw_curve = source.get("tone_curve", IDENTITY_TONE_CURVE)
    try:
        curve = [float(value) for value in raw_curve]
    except Exception:
        curve = list(IDENTITY_TONE_CURVE)
    if len(curve) != len(TONE_X):
        curve = list(IDENTITY_TONE_CURVE)
    curve = np.maximum.accumulate(np.clip(curve, 0.0, 1.0)).tolist()

    axes = _default_axes()
    raw_axes = source.get("color_axes") or {}
    for name in AXIS_NAMES:
        values = raw_axes.get(name) or {}
        axes[name] = {
            "hue": _clampi(values.get("hue", 0), -30, 30),
            "saturation": _clampi(values.get("saturation", 0), -50, 50),
            "luminance": _clampi(values.get("luminance", 0), -50, 50),
        }
    return {
        "recipe_highlight": _clampi(source.get("recipe_highlight", 0), -2, 4),
        "recipe_shadow": _clampi(source.get("recipe_shadow", 0), -2, 4),
        "recipe_color": _clampi(source.get("recipe_color", 0), -4, 4),
        "tone_curve": curve,
        "color_axes": axes,
        "color_chrome": _level(source.get("color_chrome")),
        "color_chrome_fx_blue": _level(source.get("color_chrome_fx_blue")),
    }


def creative_is_neutral(settings=None):
    normalized = normalize_creative_controls(settings)
    if any(normalized[key] for key in ("recipe_highlight", "recipe_shadow", "recipe_color")):
        return False
    if any(abs(a - b) > 1e-9 for a, b in zip(normalized["tone_curve"], IDENTITY_TONE_CURVE)):
        return False
    if normalized["color_chrome"] != "Off" or normalized["color_chrome_fx_blue"] != "Off":
        return False
    return all(not any(axis.values()) for axis in normalized["color_axes"].values())


def smoothstep(edge0, edge1, value):
    value = np.asarray(value, dtype=np.float64)
    if edge1 == edge0:
        return (value >= edge1).astype(np.float64)
    t = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def srgb_to_linear(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    return np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * np.maximum(rgb, 0.0) ** (1.0 / 2.4) - 0.055)


def linear_srgb_to_oklab(rgb):
    r, g, b = np.moveaxis(np.asarray(rgb, dtype=np.float64), -1, 0)
    ll = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    mm = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    ss = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l0, m0, s0 = np.cbrt(ll), np.cbrt(mm), np.cbrt(ss)
    return np.stack([
        0.2104542553 * l0 + 0.7936177850 * m0 - 0.0040720468 * s0,
        1.9779984951 * l0 - 2.4285922050 * m0 + 0.4505937099 * s0,
        0.0259040371 * l0 + 0.7827717662 * m0 - 0.8086757660 * s0,
    ], axis=-1)


def oklab_to_linear_srgb(lab):
    light, aa, bb = np.moveaxis(np.asarray(lab, dtype=np.float64), -1, 0)
    l0 = light + 0.3963377774 * aa + 0.2158037573 * bb
    m0 = light - 0.1055613458 * aa - 0.0638541728 * bb
    s0 = light - 0.0894841775 * aa - 1.2914855480 * bb
    ll, mm, ss = l0 ** 3, m0 ** 3, s0 ** 3
    return np.stack([
        4.0767416621 * ll - 3.3077115913 * mm + 0.2309699292 * ss,
        -1.2684380046 * ll + 2.6097574011 * mm - 0.3413193965 * ss,
        -0.0041960863 * ll - 0.7034186147 * mm + 1.7076147010 * ss,
    ], axis=-1)


def _hue_gaussian(hue, center, sigma):
    distance = np.abs((hue - center + 180.0) % 360.0 - 180.0)
    return np.exp(-0.5 * (distance / sigma) ** 2)


def _monotone_curve(values, points):
    """Evaluate a monotone cubic Hermite curve through five fixed input nodes."""
    y = np.asarray(points, dtype=np.float64)
    delta = np.diff(y) / np.diff(TONE_X)
    tangent = np.empty_like(y)
    tangent[0], tangent[-1] = delta[0], delta[-1]
    for index in range(1, len(y) - 1):
        left, right = delta[index - 1], delta[index]
        tangent[index] = 0.0 if left <= 0.0 or right <= 0.0 else 2.0 * left * right / (left + right)
    for index, slope in enumerate(delta):
        if slope <= 1e-12:
            tangent[index] = tangent[index + 1] = 0.0
            continue
        aa, bb = tangent[index] / slope, tangent[index + 1] / slope
        length = aa * aa + bb * bb
        if length > 9.0:
            scale = 3.0 / np.sqrt(length)
            tangent[index], tangent[index + 1] = scale * aa * slope, scale * bb * slope

    x = np.clip(np.asarray(values, dtype=np.float64), 0.0, 1.0)
    segment = np.clip(np.searchsorted(TONE_X, x, side="right") - 1, 0, len(TONE_X) - 2)
    x0, x1 = TONE_X[segment], TONE_X[segment + 1]
    t = (x - x0) / (x1 - x0)
    t2, t3 = t * t, t * t * t
    h00, h10 = 2 * t3 - 3 * t2 + 1, t3 - 2 * t2 + t
    h01, h11 = -2 * t3 + 3 * t2, t3 - t2
    return h00 * y[segment] + h10 * (x1 - x0) * tangent[segment] + h01 * y[segment + 1] + h11 * (x1 - x0) * tangent[segment + 1]


def evaluate_tone_curve(values, points):
    normalized = normalize_creative_controls({"tone_curve": points})["tone_curve"]
    return _monotone_curve(values, normalized)


def _gamut_map_oklch(light, chroma, hue):
    light = np.asarray(light, dtype=np.float64)
    chroma = np.maximum(np.asarray(chroma, dtype=np.float64), 0.0)
    radians = np.deg2rad(np.asarray(hue, dtype=np.float64))

    def rgb_for(candidate):
        return oklab_to_linear_srgb(np.stack([light, candidate * np.cos(radians), candidate * np.sin(radians)], axis=-1))

    rgb = rgb_for(chroma)
    good = np.all((rgb >= 0.0) & (rgb <= 1.0), axis=-1)
    if np.all(good):
        return np.clip(linear_to_srgb(rgb), 0.0, 1.0)
    low, high = np.zeros_like(chroma), chroma.copy()
    low[good], high[good] = chroma[good], chroma[good]
    for _ in range(10):
        middle = (low + high) * 0.5
        inside = np.all((rgb_for(middle) >= 0.0) & (rgb_for(middle) <= 1.0), axis=-1)
        low, high = np.where(inside, middle, low), np.where(inside, high, middle)
    return np.clip(linear_to_srgb(rgb_for(low)), 0.0, 1.0)


def apply_creative_rgb(rgb, settings=None):
    controls = normalize_creative_controls(settings)
    rgb = np.clip(np.asarray(rgb, dtype=np.float64), 0.0, 1.0)
    if creative_is_neutral(controls):
        return rgb.copy()

    lab = linear_srgb_to_oklab(srgb_to_linear(rgb))
    light = _monotone_curve(lab[..., 0], controls["tone_curve"])

    # Familiar recipe-style tone controls, expressed in perceptual lightness.
    # They deliberately preserve black, white and the middle-grey join. Negative
    # Highlight softens highlights; negative Shadow lifts/softens shadows.
    shadow_level = float(controls["recipe_shadow"])
    highlight_level = float(controls["recipe_highlight"])
    shadows = light < 0.5
    if shadow_level:
        shadow_gamma = 2.0 ** (shadow_level * 0.25)
        shadow_input = np.clip(light[shadows] / 0.5, 0.0, 1.0)
        light[shadows] = 0.5 * (shadow_input ** shadow_gamma)
    if highlight_level:
        highlight_gamma = 2.0 ** (-highlight_level * 0.25)
        highlight_input = np.clip((light[~shadows] - 0.5) / 0.5, 0.0, 1.0)
        light[~shadows] = 0.5 + 0.5 * (highlight_input ** highlight_gamma)

    aa, bb = lab[..., 1], lab[..., 2]
    chroma = np.sqrt(aa * aa + bb * bb)
    hue = (np.degrees(np.arctan2(bb, aa)) + 360.0) % 360.0
    chroma *= 2.0 ** (float(controls["recipe_color"]) * 0.12)

    weights = {name: _hue_gaussian(hue, center, 28.0) for name, center in AXIS_CENTERS.items()}
    weight_total = np.maximum(1.0, np.sum(np.stack(list(weights.values()), axis=0), axis=0))
    hue_delta = np.zeros_like(hue)
    chroma_gain = np.ones_like(chroma)
    light_delta = np.zeros_like(light)
    saturation_gate = smoothstep(0.015, 0.085, chroma)
    for name in AXIS_NAMES:
        axis = controls["color_axes"][name]
        weight = weights[name] / weight_total * saturation_gate
        hue_delta += weight * float(axis["hue"])
        chroma_gain += weight * (float(axis["saturation"]) / 100.0)
        light_delta += weight * (float(axis["luminance"]) / 400.0)
    hue = (hue + hue_delta) % 360.0
    chroma *= np.maximum(chroma_gain, 0.0)
    light += light_delta

    # Chrome effects must remain selective, but the earlier Manual Loader mask
    # required both very high perceptual chroma and a bright RGB peak. On real
    # Canon photographs that frequently selected no pixels at all. Use chroma
    # plus a broad tonal visibility mask instead: neutrals and near-black pixels
    # remain protected while ordinary saturated subjects respond clearly.
    sat_mask = smoothstep(0.020, 0.115, chroma)
    tone_mask = smoothstep(0.035, 0.22, light) * (1.0 - 0.28 * smoothstep(0.86, 1.0, light))
    chrome_level = {"Off": 0.0, "Weak": 0.50, "Strong": 1.0}[controls["color_chrome"]]
    if chrome_level:
        hue_weight = np.maximum.reduce([
            1.00 * _hue_gaussian(hue, 5.0, 34.0),
            0.92 * _hue_gaussian(hue, 42.0, 30.0),
            0.72 * _hue_gaussian(hue, 82.0, 30.0),
            0.78 * _hue_gaussian(hue, 132.0, 38.0),
            0.42 * _hue_gaussian(hue, 330.0, 30.0),
        ])
        effect = np.clip(sat_mask * tone_mask * hue_weight, 0.0, 1.0) * chrome_level
        light -= 0.060 * effect
        chroma *= 1.0 - 0.035 * effect

    blue_level = {"Off": 0.0, "Weak": 0.50, "Strong": 1.0}[controls["color_chrome_fx_blue"]]
    if blue_level:
        blue_weight = np.maximum(0.72 * _hue_gaussian(hue, 205.0, 38.0), 1.00 * _hue_gaussian(hue, 265.0, 42.0))
        effect = np.clip(sat_mask * tone_mask * blue_weight, 0.0, 1.0) * blue_level
        light -= 0.075 * effect
        chroma *= 1.0 + 0.040 * effect

    return _gamut_map_oklch(np.clip(light, 0.0, 1.0), chroma, hue)


def creative_cube(settings=None, size=65):
    controls = normalize_creative_controls(settings)
    size = int(size)
    if not 2 <= size <= 65:
        raise ValueError("Creative LUT size must be between 2 and 65")
    grid = np.indices((size, size, size), dtype=np.float64)
    rgb = np.stack([grid[2], grid[1], grid[0]], axis=-1).reshape(-1, 3) / float(size - 1)
    output = apply_creative_rgb(rgb, controls).astype(np.float32)
    encoded = json.dumps(controls, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256((encoded + f"|{size}|creative-v3").encode("utf-8")).hexdigest()
    return {
        "path": None,
        "title": "Creative Color",
        "size": size,
        "domain_min": [0.0, 0.0, 0.0],
        "domain_max": [1.0, 1.0, 1.0],
        "values": output.reshape(-1),
        "source": "generated_creative_controls",
        "fingerprint": "creative:" + fingerprint,
        "creativeControls": deepcopy(controls),
    }


def creative_lut_entry(settings=None, size=65):
    controls = normalize_creative_controls(settings)
    if creative_is_neutral(controls):
        return None
    return {"id": "creative-controls", "cube": creative_cube(controls, size), "enabled": True, "opacity": 1.0}
