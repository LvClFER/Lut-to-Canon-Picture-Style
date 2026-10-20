"""Optional DPReview originals; no network work is performed on import or startup."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from canon_runtime import cache_dir

EOS_R_GALLERY='https://www.dpreview.com/sample-galleries/0450281051/canon-eos-r-samples-gallery/'
MAX_RAW=512*1024*1024


def public_url(url, *, raw=False):
    if not isinstance(url,str):
        raise ValueError('The gallery address must be text.')
    parsed=urlsplit(url)
    if (parsed.scheme!='https' or parsed.hostname not in ('www.dpreview.com','dpreview.com')
            or parsed.port not in (None,443) or parsed.username or parsed.password
            or not parsed.path.startswith(('/sample-galleries/','/wp-content/uploads/sample_galleries/'))):
        raise ValueError('Only public DPReview sample gallery addresses are supported.')
    if raw and Path(parsed.path).suffix.lower() not in ('.cr2','.cr3','.crw'):
        raise ValueError('The selected file is not a Canon RAW original.')
    return url


class _GalleryParser(HTMLParser):
    def __init__(self):
        super().__init__();self.galleries=[]

    def handle_starttag(self,tag,attrs):
        value=dict(attrs).get('data-gallery-inline')
        if value:self.galleries.append(json.loads(value))


def parse_gallery(html):
    parser=_GalleryParser();parser.feed(html)
    samples=[];seen=set()
    for group in parser.galleries:
        if not isinstance(group,dict):continue
        for gallery in group.values():
            if not isinstance(gallery,dict):continue
            images=gallery.get('images',[])
            if not isinstance(images,list):continue
            for image in images:
                if not isinstance(image,dict):continue
                raw=image.get('rawFileUrl')
                if not raw:continue
                try:
                    public_url(raw,raw=True);page=public_url(image['permalink'])
                    thumbnail=public_url(image['thumbnailUrl'])
                except (ValueError,KeyError,TypeError):continue
                if raw in seen:continue
                seen.add(raw)
                photographer=image.get('photographer');camera=image.get('camera')
                samples.append(dict(raw=raw,page=page,thumbnail=thumbnail,
                    author=str((photographer.get('name') if isinstance(photographer,dict) else None) or 'Author not provided')[:200],
                    camera=str((camera.get('label') if isinstance(camera,dict) else None) or 'Canon')[:200],
                    title=str(image.get('legacyImagePublicId') or image.get('id') or 'RAW')[:100]))
    if not samples:raise ValueError('No Canon RAW originals were found on this gallery page.')
    return samples


def finish_download(sample,temporary):
    """Accept a completed browser download, never an HTML error or partial original."""
    url=public_url(sample['raw'],raw=True)
    temporary=Path(temporary)
    count=temporary.stat().st_size
    if count<64 or count>MAX_RAW:raise ValueError('RAW size is outside the supported range (64 bytes–512 MB).')
    with temporary.open('rb') as stream:header=stream.read(64)
    if not (header.startswith((b'II\x2a\x00',b'MM\x00\x2a',b'II\x1a\x00'))
            or (header[4:8]==b'ftyp' and b'crx ' in header[8:64])):
        raise ValueError('The server did not return a recognizable Canon RAW file.')
    root=cache_dir()/'dpreview';root.mkdir(parents=True,exist_ok=True)
    stem=hashlib.sha256(url.encode()).hexdigest()
    destination=root/(stem+Path(urlsplit(url).path).suffix.lower())
    metadata=dict(sample,source='DPReview')
    # Prepare the credit before replacing an existing cached original.
    with tempfile.NamedTemporaryFile(dir=root,suffix='.json.part',mode='w',encoding='utf-8',delete=False) as output:
        credit=Path(output.name)
        try:json.dump(metadata,output,ensure_ascii=False,indent=2)
        except Exception:
            output.close();credit.unlink(missing_ok=True);raise
    try:
        temporary.replace(destination)
        credit.replace(destination.with_suffix('.json'))
    finally:credit.unlink(missing_ok=True)
    return destination


def reference_credit(path):
    path=Path(path)
    if path.parent!=cache_dir()/'dpreview':return ''
    try:
        metadata=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        return 'DPReview · '+metadata['author']+' · '+public_url(metadata['page'])
    except (OSError,ValueError,KeyError,TypeError):return ''
