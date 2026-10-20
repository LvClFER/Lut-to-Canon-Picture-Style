import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import Qt
import canon_style_studio as studio


class EditorialLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        for name in ('segoeui.ttf','segoeuib.ttf','georgia.ttf','consola.ttf'):
            path=Path('C:/Windows/Fonts')/name
            if path.is_file():QFontDatabase.addApplicationFont(str(path))
        cls.app.setStyle('Fusion');cls.app.setStyleSheet(studio.app_stylesheet())

    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.patches=[patch.dict(os.environ,{'CANON_STYLE_STUDIO_PORTABLE_ROOT':self.temporary.name}),
            patch.object(studio,'discover_pse',return_value=None),patch.object(studio,'find_dll',return_value=None),
            patch.object(studio.QTimer,'singleShot')]
        for item in self.patches:item.start();self.addCleanup(item.stop)
        self.window=studio.CanonStyleStudioQt();self.window.show();self.app.processEvents()
        self.addCleanup(self.close)

    def close(self):
        self.window.engine_pool.waitForDone(15000)
        self.window.dirty=False;self.window.close();self.window.deleteLater();self.app.processEvents()

    def test_photo_left_controls_right_at_both_supported_window_sizes(self):
        for width,height in ((1520,980),(1240,760)):
            with self.subTest(size=(width,height)):
                self.window.resize(width,height);self.app.processEvents()
                splitter=self.window.content_splitter
                self.assertEqual(splitter.indexOf(self.window.sidebar),1)
                self.assertTrue(splitter.widget(0).isAncestorOf(self.window.viewer))
                self.assertLess(self.window.viewer.mapTo(self.window.centralWidget(),self.window.viewer.rect().topLeft()).x(),
                    self.window.sidebar.mapTo(self.window.centralWidget(),self.window.sidebar.rect().topLeft()).x())
                self.assertEqual(self.window.sidebar_scroll.horizontalScrollBarPolicy(),Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                self.assertGreater(self.window.viewer.width(),500)
                self.assertGreater(self.window.viewer.height(),300)
        self.assertTrue(self.window.sidebar.isAncestorOf(self.window.project_name))
        self.assertEqual(self.window.compare_combo.currentText(),'Preview')
        self.assertFalse(self.window.raw_section.header.isChecked())
        self.assertFalse(self.window.brand_logo.pixmap().isNull())
        self.assertEqual(self.window.brand_logo.pixmap().width(),102)
        self.assertLess(self.window.brand_logo.pixmap().height(),25)

    def test_adjustment_cards_still_update_the_exported_editor_state(self):
        window=self.window
        window.contrast.setValue(3);window.saturation.setValue(-2)
        window.sharp_enable.setChecked(True);window.sharp_strength.setValue(4)
        controls=window.controls_dict()
        self.assertEqual((controls['contrast'],controls['saturation'],controls['sharp_strength']),(3,-2,4))
        self.assertTrue(controls['sharpness_override'])
        for card in (window.contrast,window.saturation,window.color_tone,
                     window.sharp_strength,window.fineness,window.threshold):
            self.assertEqual(card.objectName(),'AdjustmentCard')
        window.creative_section.header.click();self.app.processEvents()
        self.assertTrue(window.creative_section.body.isVisible())
        self.assertTrue(window.camera_btn.isVisible())
        self.assertTrue(window.export_btn.isVisible())
        # A populated gallery must not overlap the preview at the minimum window size.
        window.resize(1240,760);window.filmstrip.set_references([Path('example.cr3')],0)
        self.app.processEvents()
        parent=window.viewer.parentWidget()
        self.assertLess(window.viewer.mapTo(parent,window.viewer.rect().bottomLeft()).y(),
            window.samples_button.mapTo(parent,window.samples_button.rect().topLeft()).y())

    def test_samples_dialog_opens_only_on_request(self):
        self.assertFalse(hasattr(self.window,'samples_dialog'))
        with patch('sample_browser.SampleImagesDialog') as dialog:
            self.window.open_sample_images()
            dialog.assert_called_once_with(self.window)
            dialog.return_value.exec.assert_called_once()

    def test_open_style_preserves_loaded_raws_and_selection(self):
        window=self.window
        raws=[Path(self.temporary.name)/name for name in ('first.cr3','second.cr3')]
        saved=Path(self.temporary.name)/'saved.cr3'
        for path in [*raws,saved]:path.touch()
        for project_references in ([],[str(saved)]):
            with self.subTest(project_references=project_references):
                window.references=list(raws);window.current_reference=1
                doc=studio.ProjectDocument(name='Preset',edit={'contrast':2},references=project_references,current_reference=0)
                with patch.object(studio,'load_project',return_value=doc),patch.object(window,'select_reference') as select,patch.object(studio.QMessageBox,'critical') as error:
                    window.open_project(Path(self.temporary.name)/'preset.canonstyleproject')
                error.assert_not_called()
                self.assertEqual(window.references,raws)
                select.assert_called_once_with(1)
                self.assertEqual(window.contrast.value(),2)

    def test_open_project_restores_saved_references_when_none_are_loaded(self):
        window=self.window
        raw=Path(self.temporary.name)/'saved.cr3';raw.touch()
        window.references=[]
        doc=studio.ProjectDocument(name='Saved',edit={},references=[str(raw)])
        with patch.object(studio,'load_project',return_value=doc),patch.object(window,'select_reference') as select,patch.object(studio.QMessageBox,'critical') as error:
            window.open_project(Path(self.temporary.name)/'saved.canonstyleproject')
        error.assert_not_called()
        self.assertEqual(window.references,[raw])
        select.assert_called_once_with(0)


if __name__=='__main__':unittest.main()
