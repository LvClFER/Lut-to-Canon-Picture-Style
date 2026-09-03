"""Pure render/view geometry helpers, independent from the Qt application."""
from __future__ import annotations


def fit_size_within_box(size, max_width, max_height):
    """Return an aspect-preserving integer size inside a bounding box."""
    if not size or len(size) != 2:
        return int(max_width), int(max_height)
    sw, sh = int(size[0]), int(size[1])
    if sw <= 0 or sh <= 0:
        return int(max_width), int(max_height)
    scale = min(float(max_width) / float(sw), float(max_height) / float(sh))
    w = max(1, int(round(sw * scale)))
    h = max(1, int(round(sh * scale)))
    return min(int(max_width), w), min(int(max_height), h)


def oriented_native_size(preview_size, metadata=None):
    """Return full sensor-visible dimensions in the preview's orientation."""
    metadata = metadata or {}
    visible = metadata.get("visible_size")
    try:
        w, h = int(visible[0]), int(visible[1])
        pw, ph = int(preview_size[0]), int(preview_size[1])
        if w <= 0 or h <= 0 or pw <= 0 or ph <= 0:
            raise ValueError
        if (pw < ph) != (w < h):
            w, h = h, w
        return w, h
    except Exception:
        try:
            w, h = int(preview_size[0]), int(preview_size[1])
            return max(1, w), max(1, h)
        except Exception:
            return 1, 1
