import html
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sample_images as samples

RAW='https://www.dpreview.com/wp-content/uploads/sample_galleries/L-0450281051/4145753913.cr3'
PAGE='https://www.dpreview.com/sample-galleries/0450281051/616126'
THUMB='https://www.dpreview.com/wp-content/uploads/sample_galleries/L-0450281051/6528439977.jpg?resize=200,200'


def gallery(images):
    return '<div data-gallery-inline="'+html.escape(json.dumps({'387099':{'images':images}}),quote=True)+'"></div>'


def image(**kwargs):
    return dict(rawFileUrl=RAW,permalink=PAGE,thumbnailUrl=THUMB,
        photographer={'name':'Carey Rose'},camera={'label':'Canon EOS R'},legacyImagePublicId='6528439977',**kwargs)


class SampleImagesTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        patcher=patch.object(samples,'cache_dir',return_value=Path(self.temporary.name));patcher.start();self.addCleanup(patcher.stop)

    def test_current_inline_gallery_schema_preserves_original_and_author(self):
        data=image();bad=dict(data,rawFileUrl='https://unrelated.example/a.cr3')
        result=samples.parse_gallery(gallery([data,data,bad,dict(data,rawFileUrl='')]))
        self.assertEqual(len(result),1)
        self.assertEqual((result[0]['raw'],result[0]['author'],result[0]['page']),(RAW,'Carey Rose',PAGE))
        with self.assertRaises(ValueError):samples.parse_gallery('<h1>Access denied</h1>')

    def test_only_public_https_gallery_urls_and_canon_raw_are_accepted(self):
        for url in ('http://www.dpreview.com/sample-galleries/1','https://www.dpreview.com.evil/sample-galleries/1',
                    'https://user:pass@www.dpreview.com/sample-galleries/1','https://127.0.0.1/sample-galleries/1',
                    'https://www.dpreview.com:9999/sample-galleries/1','https://www.dpreview.com/account/'):
            with self.subTest(url=url),self.assertRaises(ValueError):samples.public_url(url)
        with self.assertRaises(ValueError):samples.public_url(THUMB,raw=True)

    def test_malformed_gallery_shapes_fail_cleanly_or_preserve_valid_photos(self):
        for data in (None,[],{'a':None},{'a':{'images':None}},{'a':{'images':[None,[],{'rawFileUrl':42}]}}):
            markup='<div data-gallery-inline="'+html.escape(json.dumps(data),quote=True)+'"></div>'
            with self.subTest(data=data),self.assertRaises(ValueError):samples.parse_gallery(markup)
        result=samples.parse_gallery(gallery([None,dict(image(),photographer='unknown',camera=[])]))
        self.assertEqual((result[0]['author'],result[0]['camera']),('Author not provided','Canon'))
        for value in (None,42,[],b'https://www.dpreview.com/sample-galleries/1'):
            with self.subTest(value=value),self.assertRaises(ValueError):samples.public_url(value)

    def test_completed_browser_download_preserves_source_and_author(self):
        sample=samples.parse_gallery(gallery([image()]))[0]
        data=b'\x00\x00\x00\x18ftypcrx '+bytes(100)
        incoming=Path(self.temporary.name)/'incoming.cr3';incoming.write_bytes(data)
        path=samples.finish_download(sample,incoming)
        self.assertEqual(path.read_bytes(),data)
        self.assertIn('Carey Rose',samples.reference_credit(path))
        self.assertFalse(incoming.exists())
        self.assertEqual(list(path.parent.glob('*.part')),[])
        # An error page cannot replace an already cached original.
        incoming.write_bytes(b'<html>Access denied</html>'+bytes(100))
        with self.assertRaises(ValueError):samples.finish_download(sample,incoming)
        self.assertEqual(path.read_bytes(),data)

    def test_credit_failure_does_not_replace_existing_original(self):
        sample=samples.parse_gallery(gallery([image()]))[0]
        incoming=Path(self.temporary.name)/'incoming.cr3'
        original=b'\x00\x00\x00\x18ftypcrx '+bytes(100);incoming.write_bytes(original)
        path=samples.finish_download(sample,incoming)
        incoming.write_bytes(b'\x00\x00\x00\x18ftypcrx '+bytes(110))
        with patch.object(samples.json,'dump',side_effect=OSError('disk full')),self.assertRaises(OSError):
            samples.finish_download(sample,incoming)
        self.assertEqual(path.read_bytes(),original)
        self.assertEqual(list(path.parent.glob('*.part')),[])


if __name__=='__main__':unittest.main()
