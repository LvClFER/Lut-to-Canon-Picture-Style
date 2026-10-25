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
    def test_double_click_resets_slider_and_commits(self):
        from PySide6.QtTest import QTest, QSignalSpy
        for minimum, initial, expected in ((-4, 0, 0), (1, 2, 2), (1, 4, 4)):
            slider=studio.ValueSlider('Test',minimum,5,initial)
            slider.setValue(5)
            committed=QSignalSpy(slider.committed)
            QTest.mouseDClick(slider.value_label,Qt.MouseButton.LeftButton)
            self.assertEqual(slider.value(),expected)
            self.assertEqual(committed.count(),1)
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
        self.assertTrue(self.window.raw_section.header.isChecked())
        sections=[self.window.side_layout.itemAt(i).widget() for i in range(self.window.side_layout.count())
            if isinstance(self.window.side_layout.itemAt(i).widget(),studio.CollapsibleSection)]
        self.assertIs(sections[0],self.window.raw_section)
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

    def test_related_color_controls_share_one_section_and_presets_have_their_own_entry(self):
        window=self.window
        sections=[window.side_layout.itemAt(i).widget() for i in range(window.side_layout.count())
            if isinstance(window.side_layout.itemAt(i).widget(),studio.CollapsibleSection)]
        self.assertEqual([section.header.text() for section in sections],
            ['RAW DEVELOPMENT','STYLES / PRESETS','CANON PICTURE STYLE','COLOR / TONE','LUT STACK'])
        self.assertEqual([window.color_tabs.tabText(i) for i in range(window.color_tabs.count())],
            ['Recipe','Tone curve','Color mixer','Grading'])
        for index,control in ((0,window.recipe_wb_red),(0,window.recipe_color),(1,window.tone_curve),
                (2,window.axis_hue),(3,window.grading_sliders['red_gamma'])):
            self.assertTrue(window.color_tabs.widget(index).isAncestorOf(control))
        self.assertTrue(window.lut_section.isAncestorOf(window.cube_export))
        self.assertTrue(window.presets_section.isAncestorOf(window.open_style_button))
        self.assertTrue(window.presets_section.isAncestorOf(window.import_np3_button))
        with patch.object(studio.QFileDialog,'getOpenFileNames',return_value=(['preset.np3'],'')) as picker, \
                patch.object(window,'import_np3_paths') as importer:
            window.import_np3_button.click()
            self.assertEqual(picker.call_args.args[1],'Import Nikon presets')
            importer.assert_called_once_with([Path('preset.np3')])

    def test_generator_controls_are_saved_and_restored_without_changing_raw_development(self):
        window=self.window;raw_before=window.raw_preview_dict()
        window.grading_sliders['red_gamma'].setValue(35)
        window.grading_sliders['temperature'].setValue(-25)
        state=window.edit_state_dict()
        self.assertEqual(state['creative']['grading']['red_gamma'],35)
        self.assertEqual(window.controls_dict()['creative']['grading']['temperature'],-25)
        window.reset_grading()
        self.assertFalse(any(window.creative_controls['grading'].values()))
        window.apply_edit_state(state)
        self.assertEqual(window.grading_sliders['red_gamma'].value(),35)
        self.assertEqual(window.raw_preview_dict(),raw_before)
        self.assertEqual(window.cube_size.currentText(),'33')

    def test_cube_export_uses_document_folder_and_does_not_need_a_photo(self):
        window=self.window;path=Path(self.temporary.name)/'New look.cube'
        window.grading_sliders['blue_gamma'].setValue(-15)
        with patch.object(studio,'style_export_path',return_value=path) as location,patch.object(studio.QFileDialog,'getSaveFileName',return_value=(str(path),'Cube LUT (*.cube)')),patch.object(window,'start_worker') as start:
            window.export_cube_dialog()
        self.assertEqual(location.call_args.args[1],'.cube')
        worker=start.call_args.args[0]
        self.assertEqual(worker.args[0],path)
        self.assertEqual(worker.args[2]['creative']['grading']['blue_gamma'],-15)
        self.assertIsNone(window.source_full)
        start.call_args.args[2](path)
        self.assertTrue(window.cube_export.isEnabled())

    def test_standard_default_and_saved_base_preserved(self):
        self.assertEqual(studio.ProjectDocument().edit['basePictureStyle'],'Standard')
        self.assertEqual(self.window.base_combo.currentText(),'Standard')
        self.assertFalse(self.window.windowIcon().isNull())
        for name in ('Neutral','Faithful'):
            self.window.apply_edit_state({'basePictureStyle':name})
            self.assertEqual(self.window.base_combo.currentText(),name)

    def test_lut_comparison_renders_individual_luts_without_changing_project(self):
        from PIL import Image
        window=self.window;window.source_full=Image.new('RGB',(40,80),(50,60,70))
        window.luts=[{'id':'a','cube':{'title':'First'},'enabled':False,'opacity':0.7},
                     {'id':'b','cube':{'title':'Second'},'enabled':True,'opacity':1.0}]
        original=[dict(entry) for entry in window.luts];dirty=window.dirty
        outputs=[Image.new('RGB',(40,80),'red'),Image.new('RGB',(40,80),'blue')]
        def worker(work,_pool,done,_error):done(work.fn(*work.args,**work.kwargs))
        def inspect(dialog):
            viewer=dialog.findChild(studio.CompareView)
            self.assertEqual(viewer.mode,'Split')
            self.assertEqual(viewer.input_pil.getpixel((0,0)),(255,0,0))
            self.assertEqual(viewer.result_pil.getpixel((0,0)),(0,0,255))
            self.assertEqual(viewer.input_pil.size,(40,80))
            dialog.reject()
        with patch.object(window,'start_worker',side_effect=worker),patch.object(studio.QDialog,'exec',inspect),patch.object(window.render_engine,'render',side_effect=[(window.source_full,image) for image in outputs]) as render:
            window.compare_luts()
        self.assertEqual([call.args[3][0]['id'] for call in render.call_args_list],['a','b'])
        self.assertTrue(all(call.args[3][0]['enabled'] for call in render.call_args_list))
        self.assertEqual(render.call_args_list[0].args[4],render.call_args_list[1].args[4])
        self.assertEqual(window.luts,original);self.assertEqual(window.dirty,dirty)

    def test_lut_comparison_requires_photo_and_two_luts(self):
        with patch.object(studio.QMessageBox,'information') as message:
            self.window.compare_luts()
        message.assert_called_once()

    def test_lut_comparison_reuses_developed_raw_without_reapplying_basic_controls(self):
        from PIL import Image
        window=self.window;window.source_full=Image.new('RGB',(40,80),(50,60,70))
        window.source_is_raw=True;window.current_source_path=Path(self.temporary.name)/'portrait.cr3'
        window.last_canon_source=str(window.current_source_path.resolve())
        window.last_canon_settings=window.dpp_settings_dict();window.last_canon_base=Image.new('RGB',(40,80),'green')
        window.luts=[{'id':str(i),'cube':{'title':str(i)},'opacity':1} for i in range(2)]
        def worker(work,_pool,done,_error):done(work.fn(*work.args,**work.kwargs))
        def inspect(dialog):dialog.reject()
        with patch.object(window,'start_worker',side_effect=worker),patch.object(studio.QDialog,'exec',inspect),patch.object(window.render_engine,'render_from_canon_base',return_value=(window.last_canon_base,window.last_canon_base)) as native,patch.object(window.render_engine,'render') as fallback:
            window.compare_luts()
        self.assertEqual(native.call_count,2);fallback.assert_not_called()
        for call in native.call_args_list:
            self.assertIs(call.args[0],window.last_canon_base)
            self.assertNotIn('contrast',call.args[2])

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
