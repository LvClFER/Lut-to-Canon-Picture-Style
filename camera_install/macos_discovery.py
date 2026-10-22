"""Explicit, bounded ImageCaptureCore discovery; never opens a camera session."""
import hashlib
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time


def summarize_device(device):
    identifier=device.UUIDString()
    if not isinstance(identifier,str) or not identifier or len(identifier)>4096:
        raise ValueError('ImageCaptureCore did not provide a bounded device UUID')
    vendor=device.usbVendorID();product=device.usbProductID()
    if any(type(value) is not int or not 0<=value<=0xffff for value in (vendor,product)):
        raise ValueError('Invalid USB vendor/product identifier')
    return dict(idFingerprint=hashlib.sha256(identifier.encode()).hexdigest()[:16],
        name=str(device.name() or 'Camera')[:200],usbVendorID=vendor,usbProductID=product,
        canonCandidate=vendor==0x04a9,transport='ImageCaptureCore',deviceOpenAttempted=False)


@contextmanager
def _discovered_cameras(*,timeout=3.0):
    """Retain native objects while the explicit scan's caller uses them.

    Call explicitly in an isolated discovery worker on its main thread.
    A partial scan is an error, not evidence that no camera is connected.
    """
    if sys.platform!='darwin':raise RuntimeError('ImageCaptureCore discovery requires macOS')
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('ImageCaptureCore discovery requires the worker main thread')
    if type(timeout) not in (int,float) or not 0<timeout<=10:
        raise ValueError('Require a discovery deadline of at most ten seconds')
    import objc
    import Foundation as foundation
    import ImageCaptureCore as capture
    # Reuse the Objective-C class across explicit scans in the same process.
    try:delegate_type=objc.lookUpClass('CanonStyleStudioDiscoveryDelegate')
    except objc.nosuchclass_error:
        class CanonStyleStudioDiscoveryDelegate(foundation.NSObject,
                protocols=[objc.protocolNamed('ICDeviceBrowserDelegate')]):
            def deviceBrowser_didAddDevice_moreComing_(self,browser,device,more):pass
            def deviceBrowser_didRemoveDevice_moreGoing_(self,browser,device,more):pass
            def deviceBrowserDidEnumerateLocalDevices_(self,browser):self.finished=True
        delegate_type=CanonStyleStudioDiscoveryDelegate
    delegate=delegate_type.alloc().init();delegate.finished=False
    browser=capture.ICDeviceBrowser.alloc().init()
    browser.setDelegate_(delegate)
    browser.setBrowsedDeviceTypeMask_(capture.ICDeviceTypeMaskCamera|capture.ICDeviceLocationTypeMaskLocal)
    deadline=time.monotonic()+timeout
    try:
        browser.start()
        while not delegate.finished:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('ImageCaptureCore discovery did not complete')
            foundation.NSRunLoop.currentRunLoop().runUntilDate_(
                foundation.NSDate.dateWithTimeIntervalSinceNow_(min(0.05,remaining)))
        yield tuple(browser.devices() or ())
    finally:
        browser.stop();browser.setDelegate_(None)


def enumerate_cameras(*,timeout=3.0):
    """Return summaries only; no native identifiers leave the worker."""
    with _discovered_cameras(timeout=timeout) as devices:
        result=[summarize_device(device) for device in devices]
        result=[item for item in result if item['canonCandidate']]
        fingerprints=[item['idFingerprint'] for item in result]
        if len(fingerprints)!=len(set(fingerprints)):
            raise RuntimeError('Ambiguous ImageCaptureCore device identifiers')
        return result


@contextmanager
def selected_camera(fingerprint):
    """Resolve exactly one selected Canon camera; never open its session here."""
    if (type(fingerprint) is not str or len(fingerprint)!=16
            or any(c not in '0123456789abcdef' for c in fingerprint)):
        raise ValueError('Require an explicit discovery fingerprint')
    with _discovered_cameras() as devices:
        matches=[]
        for device in devices:
            summary=summarize_device(device)
            if summary['canonCandidate'] and summary['idFingerprint']==fingerprint:matches.append(device)
        if len(matches)!=1:raise RuntimeError('Selected Canon camera is absent or ambiguous')
        yield matches[0]


def enumerate_isolated():
    """Run the native main-thread scan outside the editor, with no retries."""
    if sys.platform!='darwin':raise RuntimeError('ImageCaptureCore discovery requires macOS')
    with tempfile.TemporaryDirectory(prefix='canon_mac_discovery_') as temporary:
        output=Path(temporary)/'devices.json'
        command=[sys.executable]
        if not getattr(sys,'frozen',False):command+=['-m','camera_install.macos_discovery']
        command+=['--mac-discovery-worker','--output',str(output)]
        subprocess.run(command,cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            timeout=8,check=True)
        if output.stat().st_size>256*1024:raise ValueError('Oversized discovery report')
        result=json.loads(output.read_text(encoding='utf-8'))
        if not isinstance(result,list) or len(result)>256:raise ValueError('Invalid discovery report')
        for item in result:
            if (not isinstance(item,dict) or item.get('canonCandidate') is not True
                    or item.get('deviceOpenAttempted') is not False
                    or item.get('usbVendorID')!=0x04a9
                    or type(item.get('idFingerprint')) is not str
                    or len(item['idFingerprint'])!=16
                    or any(c not in '0123456789abcdef' for c in item['idFingerprint'])):
                raise ValueError('Invalid discovery identity')
        return result


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mac-discovery-worker',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    # Reserve a new report before starting discovery.
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(enumerate_cameras(),stream)


if __name__=='__main__':main()
