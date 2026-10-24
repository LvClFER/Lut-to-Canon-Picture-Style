"""Convert an explicitly selected NP3 to a portable, generated cube asset."""
import hashlib
import os
from pathlib import Path
import tempfile
from concurrent.futures import CancelledError
from nikon_np3 import MAX_BYTES
from nikon_conversion import compile_cube
from canon_engine import parse_cube


def convert_asset(source,profile_path,cache_dir,progress=None,cancel=None):
    with Path(source).open('rb') as stream:data=stream.read(MAX_BYTES+1)
    cube=compile_cube(data,profile_path,33,progress,cancel)
    if cancel is not None and cancel():raise CancelledError('NP3 conversion cancelled')
    cache=Path(cache_dir);cache.mkdir(parents=True,exist_ok=True)
    path=cache/(hashlib.sha256(data).hexdigest()+'.cube')
    title=cube['title'].replace('"',"'").replace('\n',' ').replace('\r',' ')
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='\n',dir=cache,suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(f'TITLE "{title}"\n# Experimental NP3 colour look; excludes Nikon RAW development and sharpening\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
            for i in range(0,len(cube['values']),3):
                stream.write(' '.join(f'{v:.10f}' for v in cube['values'][i:i+3])+'\n')
        parsed=parse_cube(temporary)
        if parsed['size']!=33 or len(parsed['values'])!=33**3*3:raise ValueError('Incomplete NP3 conversion')
        if cancel is not None and cancel():raise CancelledError('NP3 conversion cancelled')
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    parsed=parse_cube(path)
    metadata={'sourceFormat':'Nikon NP3','conversion':'Experimental sRGB colour look; excludes Nikon RAW development and sharpening'}
    return dict(cube=parsed,metadata=metadata,enabled=True,opacity=1.0)
