"""Sensor RAW development on Android; deliberately no embedded-JPEG fallback."""
import json
import math
from pathlib import Path
import tempfile

from PIL import Image


def decode(path, directory, *, wb_mode='As Shot', exposure=0):
    if wb_mode not in ('As Shot', 'Auto', 'Kelvin'):
        raise ValueError('Unsupported RAW white balance mode')
    if type(exposure) not in (int, float) or not math.isfinite(exposure) or not -5 <= exposure <= 5:
        raise ValueError('Invalid RAW exposure')
    from java import jclass
    native = jclass('org.canonstylestudio.mobile.NativeRaw')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='sensor-', dir=directory) as temporary:
        output = Path(temporary) / 'developed.ppm'
        metadata = json.loads(str(native.develop(str(path), str(output), ('As Shot', 'Auto', 'Kelvin').index(wb_mode), float(exposure))))
        if metadata.get('embedded_preview_used') is not False:
            raise ValueError('The RAW decoder did not confirm sensor development')
        if not output.is_file() or not 0 < output.stat().st_size <= 60 * 1024 * 1024:
            raise ValueError('Native RAW output is missing or oversized')
        with Image.open(output) as source:
            if source.format != 'PPM' or source.mode != 'RGB' or source.size != (metadata.get('width'), metadata.get('height')):
                raise ValueError('Native RAW output does not match its metadata')
            image = source.copy()
    return image, metadata
