"""Build a local macOS app on a Mac; never upload or access a camera."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile

from canon_runtime import BASIC_PF3_SHA256,BUILD_ID,PUBLIC_VERSION,basic_pf3_resource
from build_standalone import RESEARCH_ONLY_MODULES,audit,audit_modules,require_raw_decoder

HERE=Path(__file__).resolve().parent
APP_NAME='Canon Style Studio'
ARCHITECTURES=('arm64','x86_64','universal2')


def require_native_camera_api():
    """Inspect installed bridge metadata only; never instantiate a device browser."""
    try:
        import ImageCaptureCore as capture
        from importlib.metadata import version
        for cls,selector,index in (
                (capture.ICDevice,'requestOpenSessionWithOptions_completion_',3),
                (capture.ICDevice,'requestCloseSessionWithOptions_completion_',3),
                (capture.ICCameraDevice,'requestSendPTPCommand_outData_completion_',4)):
            method=getattr(cls,selector)
            if 'callable' not in method.__metadata__()['arguments'][index]:
                raise ValueError('Missing native completion metadata')
        return dict(bridgeVersion=version('pyobjc-framework-ImageCaptureCore'),
            completionApiAvailable=True,deviceAccess=False)
    except (ImportError,AttributeError,KeyError,IndexError,ValueError) as error:
        raise RuntimeError('A Mac build requires the ImageCaptureCore completion APIs and PyObjC metadata') from error


def commands(work,arch):
    if arch not in ARCHITECTURES:raise ValueError('Unsupported Mac architecture')
    work=Path(work)
    shared=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--target-arch',arch,
        '--workpath',str(work/'work'),'--specpath',str(work/'spec')]
    worker=shared+['--onefile','--console','--name','canon_dpp_worker',
        '--distpath',str(work/'worker'),str(HERE/'canon_dpp_worker.py')]
    app=shared+['--onedir','--windowed','--name',APP_NAME,'--osx-bundle-identifier',
        'org.canonstylestudio.app','--distpath',str(work/'app'),
        '--add-binary',str(work/'worker/canon_dpp_worker')+':.',
        '--add-data',str(HERE/'basic_pf3')+':basic_pf3',
        '--add-data',str(HERE/'assets/canon-logo.png')+':assets',
        '--add-data',str(HERE/'assets/app-icon.ico')+':assets',
        '--add-data',str(HERE/'assets/step-up.svg')+':assets',
        '--add-data',str(HERE/'assets/step-down.svg')+':assets',
        '--add-data',str(HERE/'assets/menu-down.svg')+':assets',
        '--add-data',str(HERE/'example_luts/hald_identity_8.png')+':example_luts',
        '--add-data',str(HERE/'example_luts/Lightroom_Hald_Template_512_64cube_sRGB_16bit.tif')+':example_luts',
        '--add-data',str(HERE/'camera_install/dynamic_camera_agent.js')+':camera_install',
        '--hidden-import','camera_install.macos_ptp',
        *[value for name in RESEARCH_ONLY_MODULES for value in ('--exclude-module',name)],
        str(HERE/'canon_style_studio.py')]
    return worker,app


def build(output,arch):
    if sys.platform!='darwin':raise RuntimeError('A macOS app must be built on macOS')
    if arch not in ARCHITECTURES:raise ValueError('Unsupported Mac architecture')
    decoder=require_raw_decoder()
    native_camera=require_native_camera_api()
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    destination=output/(f'CanonStyleStudio_{PUBLIC_VERSION}_macOS_{arch}')
    if destination.exists():raise FileExistsError('Candidate folder already exists')
    image=output/(destination.name+'.dmg')
    if image.exists():raise FileExistsError('Disk image already exists')
    for name in BASIC_PF3_SHA256:
        if basic_pf3_resource(name[:-4].replace('_',' ')) is None:raise FileNotFoundError(name)
    with tempfile.TemporaryDirectory(prefix='canon_mac_build_',dir=output) as temporary:
        work=Path(temporary)
        for command in commands(work,arch):subprocess.run(command,cwd=HERE,check=True)
        app=work/'app'/(APP_NAME+'.app')
        if not (app/'Contents/MacOS'/APP_NAME).is_file():raise RuntimeError('Missing app executable')
        plist=app/'Contents/Info.plist'
        with plist.open('rb') as stream:info=plistlib.load(stream)
        info.update(NSCameraUsageDescription='Connect to your Canon camera to install the style and slot you authorize.',
            NSDocumentsFolderUsageDescription='Save your editable Picture Style documents.',
            CFBundleShortVersionString=PUBLIC_VERSION.split('-')[0],CFBundleVersion='1')
        with plist.open('wb') as stream:plistlib.dump(info,stream)
        resources=app/'Contents/Resources/basic_pf3'
        for name,digest in BASIC_PF3_SHA256.items():
            if hashlib.sha256((resources/name).read_bytes()).hexdigest()!=digest:
                raise RuntimeError('Missing or damaged bundled base: '+name)
        problems=audit(app)
        if problems:raise RuntimeError('Unexpected bundled files: '+', '.join(problems))
        audit_modules(app/'Contents/MacOS'/APP_NAME)
        # Info.plist changed after PyInstaller's signing step.
        subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
        subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
        destination.mkdir()
        shutil.copytree(app,destination/app.name,symlinks=True)
    for name in ('README.md','CAMERA_COMPATIBILITY.md','MACOS_PORT_STATUS.md'):
        shutil.copy2(HERE/name,destination/name)
    manifest=dict(version=PUBLIC_VERSION,buildId=BUILD_ID,architecture=arch,
        distribution='local candidate; not notarized or approved for publication',
        basicPf3Sha256=BASIC_PF3_SHA256,canonRuntimeRequiredForPf3=False,
        macUsbPhysicallyValidated=False,published=False)
    manifest['independentRawDecoder']=decoder
    manifest['nativeCameraApi']=native_camera
    (destination/'BUILD_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    subprocess.run(['hdiutil','create','-volname',APP_NAME,'-srcfolder',str(destination),
        '-format','UDZO',str(image)],check=True)
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch',choices=ARCHITECTURES,default=platform.machine())
    parser.add_argument('--output',type=Path,default=HERE.parent/'LOCAL_MACOS_BUILDS')
    args=parser.parse_args()
    print(build(args.output,args.arch))


if __name__=='__main__':main()
