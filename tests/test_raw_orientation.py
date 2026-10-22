import io
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
import canon_engine as engine
import build_standalone


def box(kind,data):return struct.pack('>I4s',len(data)+8,kind)+data


def cr3_with_preview(orientation):
    exif=Image.Exif();exif[0x112]=orientation;exif[0x10f]='Canon';exif[0x110]='Canon EOS RP'
    metadata=box(b'CMT1',exif.tobytes()[6:])
    generator=np.random.default_rng(1)
    photo=Image.fromarray(generator.integers(0,256,(160,240,3),dtype=np.uint8))
    jpeg=io.BytesIO();photo.save(jpeg,format='JPEG',quality=98)
    primary=box(b'uuid',bytes.fromhex('85c0b687820f11e08111f4ce462b6a48')+metadata)
    return box(b'ftyp',b'crx '+bytes(12))+box(b'moov',primary)+box(b'mdat',jpeg.getvalue()),jpeg.getvalue()


class RawOrientationTests(unittest.TestCase):
    def test_original_cr3_orientation_wins_when_embedded_jpeg_omits_it(self):
        operations={1:None,2:Image.Transpose.FLIP_LEFT_RIGHT,3:Image.Transpose.ROTATE_180,
            4:Image.Transpose.FLIP_TOP_BOTTOM,5:Image.Transpose.TRANSPOSE,
            6:Image.Transpose.ROTATE_270,7:Image.Transpose.TRANSVERSE,8:Image.Transpose.ROTATE_90}
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'portrait.cr3'
            for orientation,operation in operations.items():
                with self.subTest(orientation=orientation):
                    content,jpeg=cr3_with_preview(orientation);source.write_bytes(content)
                    with patch.object(engine,'rawpy',None):
                        actual,info,is_raw,embedded=engine.load_reference_image(source)
                    expected=Image.open(io.BytesIO(jpeg)).convert('RGB')
                    if operation is not None:expected=expected.transpose(operation)
                    self.assertEqual(actual.size,expected.size)
                    self.assertTrue(np.array_equal(actual,expected))
                    self.assertEqual(info['exif_orientation'],orientation)
                    self.assertEqual(info['camera_model'],'Canon EOS RP')
                    self.assertTrue(is_raw and embedded)

    def test_malformed_container_sizes_are_rejected_without_reading_outside_box(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'broken.cr3'
            source.write_bytes(box(b'ftyp',b'crx '+bytes(12))+struct.pack('>I4s',999999,b'moov'))
            self.assertEqual(engine._cr3_primary_metadata(source),{})

    def test_build_requires_decoder_before_touching_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary);sentinel=output/'keep.txt';sentinel.write_text('keep')
            with patch.dict('sys.modules',{'rawpy':None}),self.assertRaisesRegex(RuntimeError,'rawpy/LibRaw'):
                build_standalone.build(output)
            self.assertEqual(sentinel.read_text(),'keep')

    def test_qt_snapshot_exception_requires_the_exact_installed_resource(self):
        from PySide6.QtCore import QLibraryInfo
        folders=(Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.DataPath))/'resources',
            Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.LibrariesPath))/'QtWebEngineCore.framework/Resources')
        sources=[path for folder in folders for path in folder.glob('v8_context_snapshot*.bin')
            if '.debug.' not in path.name]
        self.assertTrue(sources)
        for source in sources:
            with self.subTest(resource=source.name),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);target=root/source.name;content=source.read_bytes();target.write_bytes(content)
                self.assertEqual(build_standalone.audit(root),[])
                target.write_bytes(content[:-1]+bytes([content[-1]^1]))
                self.assertEqual(build_standalone.audit(root),[target.name])

    def test_mac_snapshot_names_still_require_exact_installed_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);installed=root/'installed';resources=installed/'resources';resources.mkdir(parents=True)
            for architecture in ('arm64','x86_64'):
                name=f'v8_context_snapshot.{architecture}.bin'
                (resources/name).write_bytes(architecture.encode())
                target=root/name;target.write_bytes(architecture.encode())
                with patch('PySide6.QtCore.QLibraryInfo.path',return_value=str(installed)):
                    self.assertTrue(build_standalone.qt_webengine_snapshot(target))
                    target.write_bytes(b'different')
                    self.assertFalse(build_standalone.qt_webengine_snapshot(target))


if __name__=='__main__':unittest.main()
