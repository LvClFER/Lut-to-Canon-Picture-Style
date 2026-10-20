import html
import json
import os
from pathlib import Path
import tempfile
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
import unittest
from unittest.mock import Mock,patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QObject,Signal,QUrl,QEventLoop,QTimer,QCoreApplication,Qt,QEvent
if QCoreApplication.instance() is None:
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest,QWebEngineScript
import sample_images as samples
from sample_browser import SampleImagesDialog,displayed_sample,SELECTED_SAMPLE_JS,GalleryPage
from test_sample_images import gallery,image,RAW,PAGE


class Download(QObject):
    receivedBytesChanged=Signal();totalBytesChanged=Signal();isFinishedChanged=Signal()
    def __init__(self,url=RAW):
        super().__init__();self.address=url;self.directory='';self.name='';self.accepted=False
        self.finished=False;self.received=0;self.total=112
        self.status=QWebEngineDownloadRequest.DownloadState.DownloadRequested
    def url(self):return QUrl(self.address)
    def isSavePageDownload(self):return False
    def totalBytes(self):return self.total
    def receivedBytes(self):return self.received
    def setDownloadDirectory(self,value):self.directory=value
    def setDownloadFileName(self,value):self.name=value
    def downloadDirectory(self):return self.directory
    def downloadFileName(self):return self.name
    def accept(self):self.accepted=True
    def cancel(self):
        self.status=QWebEngineDownloadRequest.DownloadState.DownloadCancelled
        self.finished=True;self.isFinishedChanged.emit()
    def isFinished(self):return self.finished
    def state(self):return self.status
    def interruptReasonString(self):return 'Cancelled'
    def complete(self,data):
        (Path(self.directory)/self.name).write_bytes(data)
        self.status=QWebEngineDownloadRequest.DownloadState.DownloadCompleted
        self.finished=True;self.isFinishedChanged.emit()


class SampleBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.patcher=patch.object(samples,'cache_dir',return_value=Path(self.temporary.name));self.patcher.start();self.addCleanup(self.patcher.stop)
        self.browser_cache=patch('sample_browser.cache_dir',return_value=Path(self.temporary.name));self.browser_cache.start();self.addCleanup(self.browser_cache.stop)
        self.main=QWidget();self.main.add_references=Mock()
        self.dialog=SampleImagesDialog(self.main)
        self.addCleanup(self.close)

    def close(self):
        self.dialog.reject();self.dialog.deleteLater();self.main.deleteLater();self.app.processEvents()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)

    def prepare_request(self):
        self.dialog.sample=samples.parse_gallery(gallery([image()]))[0]
        self.dialog.set_busy(True);request=Download()
        self.dialog.download_requested(request)
        self.assertTrue(request.accepted)
        return request

    def test_private_browser_starts_blank_and_unselected_download_is_rejected(self):
        self.assertTrue(self.dialog.profile.isOffTheRecord())
        self.assertTrue(self.dialog.view.url().isEmpty())
        self.assertFalse(self.dialog.download.isEnabled())
        request=Download();self.dialog.download_requested(request)
        self.assertFalse(request.accepted);self.assertTrue(request.isFinished())
        self.assertEqual(list(Path(self.temporary.name).iterdir()),[])
        self.main.add_references.assert_not_called()

    def test_completed_browser_download_opens_selected_raw_with_credit(self):
        request=self.prepare_request();data=b'\x00\x00\x00\x18ftypcrx '+bytes(100)
        request.complete(data)
        self.main.add_references.assert_called_once()
        path=self.main.add_references.call_args.args[0][0]
        self.assertEqual(path.read_bytes(),data)
        self.assertIn('Carey Rose',samples.reference_credit(path))
        self.assertEqual(list(path.parent.glob('.download-*')),[])

    def test_real_webengine_transfer_opens_download_and_preserves_credit(self):
        data=b'\x00\x00\x00\x18ftypcrx '+bytes(100)
        received=[]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append(self.path)
                self.send_response(200)
                self.send_header('Content-Type','application/octet-stream')
                self.send_header('Content-Length',str(len(data)))
                self.end_headers();self.wfile.write(data)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(lambda:(server.shutdown(),thread.join(timeout=2)))
        url=f'http://127.0.0.1:{server.server_port}/original.cr3'
        sample=dict(samples.parse_gallery(gallery([image()]))[0],raw=url)
        loop=QEventLoop();timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit)
        self.main.add_references.side_effect=lambda *args,**kwargs:loop.quit()
        self.dialog.sample=sample;self.dialog.set_busy(True)
        original=samples.public_url
        def local_fixture(value,**kwargs):
            return value if value==url else original(value,**kwargs)
        # Only this test admits its loopback fixture; production URL restrictions stay intact.
        with patch('sample_browser.public_url',side_effect=local_fixture),patch.object(samples,'public_url',side_effect=local_fixture):
            self.dialog.page.download(QUrl(url));timer.start(10000);loop.exec();timer.stop()
        self.assertEqual(received,['/original.cr3'])
        self.main.add_references.assert_called_once()
        path=self.main.add_references.call_args.args[0][0]
        self.assertEqual(path.read_bytes(),data)
        self.assertIn('Carey Rose',samples.reference_credit(path))
        self.assertEqual(self.dialog.progress.value(),100)
        self.assertEqual(list(path.parent.glob('.download-*')),[])

    def test_cancel_and_oversize_never_open_or_leave_partial_raw(self):
        request=self.prepare_request();folder=Path(request.directory)
        self.dialog.reject()
        self.assertTrue(request.isFinished());self.assertFalse(folder.exists())
        self.main.add_references.assert_not_called()
        self.dialog.closed=False;request=self.prepare_request();folder=Path(request.directory)
        request.received=samples.MAX_RAW+1;request.receivedBytesChanged.emit()
        self.assertFalse(folder.exists());self.main.add_references.assert_not_called()
        self.assertIn('512 MB',self.dialog.status.text())

    def test_error_page_does_not_open_as_raw(self):
        request=self.prepare_request();request.complete(b'<html>Access denied</html>'+bytes(100))
        self.main.add_references.assert_not_called()
        self.assertIn('recognizable Canon RAW',self.dialog.status.text())
        self.assertEqual(list(Path(self.temporary.name).rglob('*.cr3')),[])

    def test_missing_gallery_data_and_uncredited_links_are_rejected(self):
        for value in ('', '{}','null','[]',json.dumps({'raw':RAW,'html':gallery([dict(image(),rawFileUrl=RAW+'?other')])})):
            with self.subTest(value=value),self.assertRaises(ValueError):displayed_sample(value)

    def test_actual_webengine_reads_selected_photo_and_credit_from_local_fixture(self):
        fixture=gallery([image()]).replace('<div ','<div class="wayfinder-gallery-block" ',1)
        fixture=fixture.replace('</div>',f'<div class="sg-details"><a class="sg-details__download-link" href="{html.escape(RAW)}">RAW</a></div></div>',1)
        loop=QEventLoop();timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit)
        loaded=[]
        def done(ok):loaded.append(ok);loop.quit()
        self.dialog.page.loadFinished.connect(done)
        # Only the local test fixture needs data: navigation; production stays restricted.
        with patch.object(GalleryPage,'acceptNavigationRequest',return_value=True):
            self.dialog.page.setHtml(fixture,QUrl(PAGE));timer.start(10000);loop.exec();timer.stop()
        self.dialog.page.loadFinished.disconnect(done)
        self.assertEqual(loaded,[True])
        result=[]
        def selected(value):result.append(value);loop.quit()
        self.dialog.page.runJavaScript(SELECTED_SAMPLE_JS,QWebEngineScript.ScriptWorldId.ApplicationWorld,selected)
        timer.start(10000);loop.exec();timer.stop()
        self.assertTrue(result)
        selected=displayed_sample(result[0])
        self.assertEqual((selected['raw'],selected['author'],selected['page']),(RAW,'Carey Rose',PAGE))


if __name__=='__main__':unittest.main()
