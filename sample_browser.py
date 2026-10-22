"""User-operated DPReview gallery with downloads in the same private Qt session."""
import json
from pathlib import Path
import tempfile

from PySide6.QtCore import Qt,QTimer,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLineEdit,QPushButton,QLabel,QProgressBar
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineScript,QWebEngineDownloadRequest
from PySide6.QtWebEngineWidgets import QWebEngineView

from canon_runtime import cache_dir
from sample_images import EOS_R_GALLERY,MAX_RAW,public_url,parse_gallery,finish_download


# Read only the displayed gallery's DOM; the page supplies its original metadata.
SELECTED_SAMPLE_JS="""(() => {
    const panel=Array.from(document.querySelectorAll('.sg-details')).find(p=>p.getClientRects().length);
    if(!panel)return '';
    const raw=Array.from(panel.querySelectorAll('a.sg-details__download-link')).find(a=>a.textContent.trim()==='RAW');
    const gallery=panel.closest('.wayfinder-gallery-block');
    if(!raw || !gallery)return '';
    return JSON.stringify({raw:raw.href,html:gallery.outerHTML});
})()"""


def displayed_sample(value):
    if not isinstance(value,str) or len(value)>8*1024*1024:
        raise ValueError('Select a photograph with a RAW original in the gallery first.')
    try:data=json.loads(value)
    except ValueError:raise ValueError('Select a photograph with a RAW original in the gallery first.') from None
    if not isinstance(data,dict) or not isinstance(data.get('html'),str) or not isinstance(data.get('raw'),str):
        raise ValueError('The gallery did not provide a RAW original and its source metadata.')
    raw=public_url(data['raw'],raw=True)
    for sample in parse_gallery(data['html']):
        if sample['raw']==raw:return sample
    raise ValueError('The displayed RAW original has no matching gallery credit.')


class GalleryPage(QWebEnginePage):
    def acceptNavigationRequest(self,url,kind,isMainFrame):
        if not isMainFrame or url.toString()=='about:blank':return True
        try:public_url(url.toString());return True
        except ValueError:return False


class SampleImagesDialog(QDialog):
    def __init__(self,main):
        super().__init__(main);self.main=main;self.busy=False;self.closed=False
        self.request=None;self.sample=None;self.temporary=None;self.failure='';self.generation=0
        self.setWindowTitle('DPReview · RAW sample images');self.resize(1150,820)
        layout=QVBoxLayout(self)
        note=QLabel('Open a gallery, choose a photograph, then use Download RAW and open.\n'
            'The gallery uses a private browser session. Complete any site verification yourself.')
        note.setWordWrap(True);layout.addWidget(note)
        row=QHBoxLayout();self.address=QLineEdit(EOS_R_GALLERY);row.addWidget(self.address,1)
        self.load=QPushButton('Open gallery');self.load.clicked.connect(self.load_clicked);row.addWidget(self.load)
        self.browser=QPushButton('External browser');self.browser.clicked.connect(self.open_browser);row.addWidget(self.browser);layout.addLayout(row)
        self.view=QWebEngineView();layout.addWidget(self.view,1)
        self.profile=QWebEngineProfile(self)  # No storage name: cookies and cache stay in memory.
        self.page=GalleryPage(self.profile,self.view);self.view.setPage(self.page)
        self.page.setAudioMuted(True)
        self.page.permissionRequested.connect(lambda permission:permission.deny())
        self.page.certificateError.connect(lambda error:error.rejectCertificate())
        self.profile.downloadRequested.connect(self.download_requested)
        self.view.loadFinished.connect(self.loaded)
        self.credit=QLabel();self.credit.setTextFormat(Qt.TextFormat.PlainText);self.credit.setWordWrap(True);layout.addWidget(self.credit)
        self.status=QLabel('Ready · Open gallery starts the connection to DPReview.');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.progress=QProgressBar();layout.addWidget(self.progress)
        row=QHBoxLayout();self.close_button=QPushButton('Close');self.close_button.clicked.connect(self.reject);row.addWidget(self.close_button)
        row.addStretch();self.download=QPushButton('Download RAW and open');self.download.setObjectName('AccentButton')
        self.download.setEnabled(False);self.download.clicked.connect(self.download_clicked);row.addWidget(self.download);layout.addLayout(row)
        self.deadline=QTimer(self);self.deadline.setSingleShot(True);self.deadline.setInterval(120000);self.deadline.timeout.connect(self.timed_out)

    def showEvent(self,event):
        self.closed=False;super().showEvent(event)

    def set_busy(self,value):
        self.busy=value;self.load.setEnabled(not value);self.address.setEnabled(not value)
        self.view.setEnabled(not value);self.download.setEnabled(not value and bool(self.view.url().host()))
        self.close_button.setText('Cancel / Close' if value else 'Close')

    def load_clicked(self):
        if self.busy:return
        try:url=public_url(self.address.text().strip())
        except ValueError as error:self.status.setText(str(error));return
        self.generation+=1;self.credit.clear();self.download.setEnabled(False)
        self.status.setText('Loading gallery…');self.view.load(QUrl(url))

    def loaded(self,ok):
        if self.closed:return
        self.download.setEnabled(not self.busy and bool(self.view.url().host()))
        self.status.setText('Choose a photograph with RAW, then Download RAW and open. If a site verification is shown, complete it yourself.'
            if ok else 'The site could not finish loading. You can use External browser, then Open for a locally downloaded RAW.')

    def download_clicked(self):
        if self.busy:return
        self.generation+=1;generation=self.generation;self.set_busy(True);self.failure=''
        self.progress.setRange(0,100);self.progress.setValue(0);self.status.setText('Reading the displayed photograph…');self.deadline.start()
        def selected(value):
            if self.closed or generation!=self.generation:return
            try:
                public_url(self.view.url().toString())
                self.sample=displayed_sample(value)
                self.credit.setText(f"DPReview · {self.sample['author']}\n{self.sample['page']}")
                self.page.download(QUrl(self.sample['raw']))
            except (ValueError,KeyError,TypeError) as error:self.finish_error(str(error))
        self.page.runJavaScript(SELECTED_SAMPLE_JS,QWebEngineScript.ScriptWorldId.ApplicationWorld,selected)

    def download_requested(self,request):
        if (not self.busy or self.closed or self.request is not None or not self.sample
                or request.url().toString()!=self.sample['raw'] or request.isSavePageDownload()):
            request.cancel()
            if not self.busy:self.status.setText('Use Download RAW and open below the gallery to keep the source and photographer credit.')
            return
        try:
            public_url(request.url().toString(),raw=True)
            if request.totalBytes()>MAX_RAW:raise ValueError('RAW exceeds the 512 MB limit.')
            root=cache_dir()/'dpreview';root.mkdir(parents=True,exist_ok=True)
            self.temporary=tempfile.TemporaryDirectory(dir=root,prefix='.download-')
            request.setDownloadDirectory(self.temporary.name)
            request.setDownloadFileName('original'+Path(QUrl(self.sample['raw']).path()).suffix.lower())
            self.request=request
            request.receivedBytesChanged.connect(self.download_progress)
            request.totalBytesChanged.connect(self.download_progress)
            request.isFinishedChanged.connect(self.download_finished)
            self.status.setText('Downloading selected RAW…');request.accept()
        except (OSError,ValueError) as error:
            request.cancel();self.finish_error(str(error))

    def download_progress(self):
        request=self.request
        if request is None:return
        total=request.totalBytes();received=request.receivedBytes()
        if max(total,received)>MAX_RAW:
            self.failure='RAW exceeds the 512 MB limit.';request.cancel();return
        self.progress.setRange(0,100 if total>0 else 0)
        if total>0:self.progress.setValue(min(99,int(received*100/total)))

    def download_finished(self):
        request=self.request
        if request is None or not request.isFinished():return
        path=None;error=self.failure
        try:
            if request.state()!=QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                raise ValueError(error or request.interruptReasonString() or 'Download cancelled.')
            path=finish_download(self.sample,Path(request.downloadDirectory())/request.downloadFileName())
        except (OSError,ValueError) as problem:error=str(problem)
        self.request=None;request.deleteLater();self.cleanup()
        if self.closed:return
        if error:self.status.setText(error);return
        self.progress.setRange(0,100);self.progress.setValue(100)
        self.main.add_references([path],select_last=True);self.accept()

    def cleanup(self):
        self.deadline.stop();self.sample=None
        if self.temporary is not None:self.temporary.cleanup();self.temporary=None
        self.set_busy(False)

    def finish_error(self,message):
        self.cleanup()
        if not self.closed:self.status.setText(message)

    def timed_out(self):
        self.generation+=1;self.failure='RAW download exceeded two minutes.'
        if self.request is not None:self.request.cancel()
        else:self.finish_error(self.failure)

    def open_browser(self):
        try:url=public_url(self.address.text().strip())
        except ValueError as error:self.status.setText(str(error));return
        QDesktopServices.openUrl(QUrl(url))

    def reject(self):
        self.closed=True;self.generation+=1;self.view.stop()
        if self.request is not None:self.failure='Download cancelled.';self.request.cancel()
        else:self.cleanup()
        super().reject()
