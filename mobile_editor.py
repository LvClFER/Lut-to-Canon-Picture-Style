"""Android-facing editor operations using the desktop engine and project format.

No Qt, Nikon/Canon runtime, network or camera discovery is imported here.
The Android activity serializes calls on its single background executor.
"""
import copy
import json
import math
import os
from pathlib import Path


class Editor:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        os.environ['CANON_STYLE_STUDIO_PORTABLE_ROOT'] = str(self.root)
        import canon_engine as engine
        from project_state import ProjectDocument
        self.engine = engine
        self.project = ProjectDocument()
        self.renderer = engine.CanonRenderEngine()
        self.history, self.future = [], []
        self.preview_before = self.preview_after = ''
        self.decoder = ''
        self._decoded_raw = None
        session = self.root / 'session.json'
        if session.is_file():
            if session.stat().st_size > 8 * 1024 * 1024:
                raise ValueError('Saved mobile session exceeds its size limit')
            candidate = ProjectDocument.from_dict(json.loads(session.read_text(encoding='utf-8')))
            self._luts(candidate)
            self.project = candidate

    def checkpoint(self):
        temporary = self.root / 'session.json.tmp'
        temporary.write_text(json.dumps(self.project.to_dict(), ensure_ascii=False), encoding='utf-8')
        temporary.replace(self.root / 'session.json')

    def _remember(self):
        self.history.append(copy.deepcopy(self.project.to_dict()))
        self.history = self.history[-30:]
        self.future.clear()

    def _base(self):
        edit = self.project.edit
        custom = edit.get('custom_pf3') or edit.get('base_path')
        if custom and Path(custom).is_file():
            return Path(custom)
        result = self.engine.resolve_independent_base_pf3(edit.get('basePictureStyle', 'Standard'))
        if result is None:
            raise ValueError('No bundled base Picture Style is available')
        return result['path']

    def _luts(self, project=None):
        entries = []
        for item in (project or self.project).edit.get('luts', []):
            path = item['path']
            entries.append(dict(cube=self.engine.parse_lut_file(path),
                                enabled=bool(item.get('enabled', True)),
                                opacity=float(item.get('opacity', 1))))
        return entries

    def open(self, path, kind='auto'):
        from project_state import load_project
        path = Path(path)
        if not path.is_file() or path.stat().st_size > 512 * 1024 * 1024:
            raise ValueError('Input is missing or exceeds 512 MiB')
        suffix = path.suffix.lower()
        if suffix in ('.canonstyleproject', '.json'):
            candidate = load_project(path, extraction_root=self.root / 'projects')
            self._luts(candidate)  # Validate before replacing current edits.
            if self.project.references:
                candidate.references = list(self.project.references)
                candidate.current_reference = self.project.current_reference
            self._remember()
            self.project = candidate
        elif suffix == '.pf3':
            info = self.engine.inspect_pf3(None, path)
            self._remember()
            self.project.edit.update(info['basic'])
            self.project.edit.update(basePictureStyle='Imported PF3', base_name='Imported PF3', custom_pf3=str(path))
            self.project.name = info['title']
        elif kind == 'lut' or suffix == '.cube':
            self.engine.parse_lut_file(path)
            self._remember()
            self.project.edit.setdefault('luts', []).append(dict(path=str(path), enabled=True, opacity=1.0))
        elif suffix == '.np3':
            raise ValueError('NP3 colour conversion is still under development; no approximate conversion is applied')
        else:
            self._source(path)
            self._remember()
            self.project.references.append(str(path))
            self.project.current_reference = len(self.project.references) - 1
        return self.state()

    def update(self, encoded):
        from creative_controls import normalize_creative_controls, normalize_recipe_wb
        changes = json.loads(encoded)
        if not isinstance(changes, dict):
            raise ValueError('Expected an edit object')
        edit = copy.deepcopy(self.project.edit)
        ranges = dict(contrast=(-4, 4), saturation=(-4, 4), color_tone=(-4, 4),
                      sharp_strength=(0, 7), fineness=(1, 5), threshold=(1, 5),
                      raw_exposure=(-5, 5), raw_kelvin=(2000, 15000),
                      wb_ab_shift=(-9, 9), wb_gm_shift=(-9, 9))
        for key, value in changes.items():
            if key in ranges:
                low, high = ranges[key]
                if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
                    raise ValueError('Invalid ' + key)
                if key != 'raw_exposure' and int(value) != value:
                    raise ValueError('Expected an integer for ' + key)
                edit[key] = value if key == 'raw_exposure' else int(value)
            elif key == 'basePictureStyle':
                if value not in self.engine.PICTURE_STYLE_IDS:
                    raise ValueError('Unsupported base Picture Style')
                edit.update(basePictureStyle=value, base_name=value, custom_pf3='', base_path='')
            elif key == 'creative':
                edit[key] = normalize_creative_controls(value)
            elif key == 'recipe_wb':
                edit[key] = normalize_recipe_wb(value)
            elif key == 'sharpness_override':
                if type(value) is not bool:
                    raise ValueError('Expected sharpness boolean')
                edit[key] = value
            elif key == 'raw_wb_mode':
                if value not in ('As Shot', 'Auto', 'Kelvin'):
                    raise ValueError('Unsupported white balance')
                edit[key] = value
            elif key == 'name':
                if not isinstance(value, str) or not 1 <= len(value.strip()) <= 128:
                    raise ValueError('Invalid project name')
            else:
                raise ValueError('Unsupported edit: ' + key)
        self._remember()
        self.project.edit = edit
        if 'name' in changes:
            self.project.name = changes['name'].strip()
        return self.state()

    def lut(self, index, opacity, enabled, remove=False):
        if type(index) is not int or not 0 <= index < len(self.project.edit['luts']):
            raise ValueError('Invalid LUT index')
        if type(opacity) not in (int, float) or not math.isfinite(opacity) or not 0 <= opacity <= 1 or type(enabled) is not bool:
            raise ValueError('Invalid LUT settings')
        self._remember()
        if remove:
            del self.project.edit['luts'][index]
        else:
            self.project.edit['luts'][index].update(opacity=opacity, enabled=enabled)
        return self.state()

    def undo(self, redo=False):
        from project_state import ProjectDocument
        source, target = (self.future, self.history) if redo else (self.history, self.future)
        if source:
            target.append(copy.deepcopy(self.project.to_dict()))
            self.project = ProjectDocument.from_dict(source.pop())
        return self.state()

    def snapshot(self, name, restore=False):
        if name not in ('A', 'B', 'C'):
            raise ValueError('Invalid snapshot')
        value = self.project.snapshots.get(name)
        if restore and value is None:
            raise ValueError('Snapshot is empty')
        self._remember()
        if restore:
            self.project.edit = copy.deepcopy(value)
        else:
            self.project.snapshots[name] = copy.deepcopy(self.project.edit)
        return self.state()

    def select_reference(self, index):
        if type(index) is not int or not 0 <= index < len(self.project.references):
            raise ValueError('Invalid reference image')
        self.project.current_reference = index
        return self.state()

    def render(self):
        if not self.project.references:
            self.preview_before = self.preview_after = self.decoder = ''
            return self.state()
        edit = self.project.edit
        path = self.project.references[self.project.current_reference]
        source, metadata = self._source(path)
        self.decoder = metadata.get('decoder', 'Image')
        if metadata.get('canon_base_render_verified') is False:
            self.decoder += ' · Canon base look not calibrated'
        raw = dict(exposure=0 if metadata.get('sensor_exposure_applied') is True else edit.get('raw_exposure', 0),
                   kelvin=edit.get('raw_kelvin') if edit.get('raw_wb_mode') == 'Kelvin' else None,
                   ab_shift=edit.get('wb_ab_shift', 0), gm_shift=edit.get('wb_gm_shift', 0))
        before, after = self.renderer.render(source, None, self._base(), self._luts(), edit, max_side=1400, raw_preview=raw)
        for name, image in (('before', before), ('after', after)):
            output = self.root / (name + '.png')
            image.save(output)
            setattr(self, 'preview_' + name, str(output))
        return self.state()

    def _source(self, path):
        if Path(path).suffix.lower() in self.engine.CANON_STRONG_RAW_EXTENSIONS:
            from android_raw import decode
            mode = self.project.edit.get('raw_wb_mode', 'As Shot')
            exposure = self.project.edit.get('raw_exposure', 0)
            key = (self.engine.file_fingerprint(Path(path)), mode, exposure)
            if self._decoded_raw is None or self._decoded_raw[0] != key:
                self._decoded_raw = (key, decode(path, self.root / 'raw-cache', wb_mode=mode, exposure=exposure))
            return self._decoded_raw[1]
        source, metadata, _raw, embedded = self.engine.load_reference_image(path)
        if embedded:
            raise ValueError('Embedded RAW previews cannot be used for style evaluation')
        return source, metadata

    def export(self, output, project=True):
        path = Path(output)
        if path.exists():
            raise ValueError('Refusing to overwrite an existing private export')
        controls = self.project.edit
        if project:
            self.engine.export_style_project(None, self._base(), path, self._luts(), controls, self.project.name, self.project)
        else:
            self.engine.export_pf3(None, self._base(), path, self._luts(), controls, self.project.name)
        return str(path)

    def state(self):
        return json.dumps(dict(name=self.project.name, edit=self.project.edit,
                              references=self.project.references, current_reference=self.project.current_reference,
                              before=self.preview_before, after=self.preview_after, decoder=self.decoder,
                              canUndo=bool(self.history), canRedo=bool(self.future)), ensure_ascii=False)
