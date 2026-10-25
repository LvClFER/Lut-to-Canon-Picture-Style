"""Stage the existing Python engine for a local Android build; no upload."""
import hashlib
import json
from pathlib import Path
import shutil


def stage(root=None):
    root = Path(root or Path(__file__).resolve().parent)
    destination = root / 'android/app/src/main/python'
    destination.mkdir(parents=True, exist_ok=True)
    sources = [root / name for name in ('mobile_editor.py', 'mobile_camera.py', 'android_raw.py', 'canon_engine.py', 'canon_runtime.py',
                                        'creative_controls.py', 'project_state.py', 'nikon_np3.py',
                                        'nikon_import.py', 'nikon_profile_data.py')]
    sources += sorted((root / 'nikon_conversion').glob('*.py'))
    sources += sorted((root / 'camera_install').glob('*.py'))
    sources += sorted((root / 'basic_pf3').glob('*.pf3'))
    assert len(list((root / 'basic_pf3').glob('*.pf3'))) == 6, 'Missing bundled bases'
    manifest = {}
    for source in sources:
        relative = source.relative_to(root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        manifest[relative.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    (destination / 'source_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Staged {len(sources)} engine resources; no Canon/Nikon DLLs or private photos')
    return destination


if __name__ == '__main__':
    stage()
