"""Build/audit the session diagnostic only; never enumerate or open devices."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from canon_runtime import BASIC_PF3_SHA256


def audit_bundle(root):
    # Packaging dependency only; never imported by the diagnostic executable.
    from PyInstaller.archive.readers import CArchiveReader
    root = Path(root).resolve()
    executable = root / 'CanonIndependentDiagnostic.exe'
    archive = CArchiveReader(str(executable))
    modules = archive.open_embedded_archive('PYZ.pyz').toc
    forbidden = ('frida', 'PySide6', 'rawpy', 'imageio', 'tifffile',
                 'camera_install.compiler_regression',
                 'camera_install.virtual_compatibility')
    unexpected = [name for name in modules
                  if any(name == prefix or name.startswith(prefix + '.') for prefix in forbidden)]
    if unexpected:
        raise RuntimeError(f'Unexpected runtime modules: {unexpected}')
    required = {'numpy', 'PIL', 'canon_engine', 'project_state',
                'camera_install.rp_preflight_reference',
                'camera_install.family_registration_reference',
                'camera_install.camera_families_reference',
                'camera_install.independent_registration_reference',
                'camera_install.registration_sequence_reference'}
    if not required.issubset(modules):
        raise RuntimeError(f'Missing preflight modules: {sorted(required.difference(modules))}')
    hashes = {}
    dlls = []
    # NumPy's wheel ships BLAS/runtime DLLs; accept their exact installed bytes,
    # not arbitrary libraries whose filenames merely resemble them.
    import numpy
    numpy_libraries = Path(numpy.__file__).resolve().parent.parent / 'numpy.libs'
    numerical_dlls = {path.name.lower(): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in numpy_libraries.glob('*.dll')}
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        suffix = path.suffix.lower()
        approved=(path.parent.name=='basic_pf3' and path.name in BASIC_PF3_SHA256
            and hashlib.sha256(path.read_bytes()).hexdigest()==BASIC_PF3_SHA256[path.name])
        if suffix in ('.pf3', '.pf2', '.bin', '.icc', '.icm', '.cr3', '.cr2') and not approved:
            raise RuntimeError(f'Unexpected research/resource file: {relative}')
        if suffix == '.dll':
            name = path.name.lower()
            if not (name.startswith('api-ms-win-') or name in (
                    'python312.dll', 'vcruntime140.dll', 'vcruntime140_1.dll',
                    'ucrtbase.dll', 'libcrypto-3-x64.dll', 'libssl-3-x64.dll', 'libffi-8.dll')
                    or numerical_dlls.get(name) == hashlib.sha256(path.read_bytes()).hexdigest()):
                raise RuntimeError(f'Unexpected native library: {relative}')
            dlls.append(relative)
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    environment.pop('PYTHONHOME', None)
    system_root = os.environ.get('SystemRoot')
    if not system_root:
        raise RuntimeError('Windows SystemRoot is unavailable')
    # os.environ is case-insensitive on Windows, but its dict copy is not.
    environment = {key: value for key, value in environment.items()
                   if key.upper() not in ('PATH', 'PYTHONPATH', 'PYTHONHOME')}
    environment['PATH'] = str(Path(system_root) / 'System32')
    result = subprocess.run([str(executable), '--help'], cwd=root, env=environment,
                            capture_output=True, text=True, timeout=20)
    if (result.returncode or '--allow-temporary-session' not in result.stdout
            or '--preflight-style' not in result.stdout
            or '--experimental-register' not in result.stdout):
        raise RuntimeError('Isolated executable help smoke test failed')
    return dict(format='CanonStyleStudio.IndependentDiagnosticBuildAudit', version=1,
                isolatedHelpPassed=True, bundledModuleCount=len(modules),
                cameraAccessAttempted=False, registrationImplemented=True,
                registrationEnabledByDefault=False, physicalRegistrationValidated=False,
                pythonInstallationRequired=False, canonRuntimeBundled=False,
                bundledLibraries=dlls, fileSha256=hashes,
                limitation='Startup/package audit only; this executable has not registered a style.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--build', type=Path, help='New output directory; must not exist')
    choice.add_argument('--audit-existing', type=Path, help='Existing diagnostic bundle directory')
    args = parser.parse_args()
    if args.build is not None:
        destination = args.build.resolve()
        destination.mkdir(parents=True, exist_ok=False)
        with tempfile.TemporaryDirectory(prefix='diagnostic_build_', dir=destination) as work:
            subprocess.run([sys.executable, '-m', 'PyInstaller', '--onedir', '--console',
                            '--add-data',str(Path(__file__).parent/'basic_pf3')+os.pathsep+'basic_pf3',
                            '--name', 'CanonIndependentDiagnostic', '--distpath', str(destination),
                            '--workpath', work, '--specpath', work,
                            '--exclude-module', 'frida', '--exclude-module', 'PySide6',
                            '--exclude-module', 'rawpy', '--exclude-module', 'imageio',
                            '--exclude-module', 'tifffile', '--exclude-module', 'matplotlib',
                            '--exclude-module', 'pytest',
                            '--exclude-module', 'camera_install.compiler_regression',
                            '--exclude-module', 'camera_install.virtual_compatibility',
                            str(Path(__file__).with_name('independent_camera_diagnostic.py'))],
                           check=True)
        bundle = destination / 'CanonIndependentDiagnostic'
    else:
        bundle = args.audit_existing.resolve()
    report = audit_bundle(bundle)
    with (bundle / 'INDEPENDENT_DIAGNOSTIC_AUDIT.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print('PASS: isolated startup and package audit; no camera accessed')


if __name__ == '__main__':
    main()
