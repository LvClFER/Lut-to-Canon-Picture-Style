from __future__ import annotations

import os
import sys
import tempfile
import traceback
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PIL import Image
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication

from canon_style_studio import CanonStyleStudioQt, ExportDialog, app_stylesheet
from camera_install.ui import CameraInstallDialog


RAW=Path(r"C:\Users\Filipe\Documents\canon rp\IMG_2748.CR3")
HERE=Path(__file__).resolve().parent


def structure_correlation(reference,candidate):
    a=np.asarray(reference.convert("L").resize((128,192),Image.Resampling.LANCZOS),dtype=np.float32)
    b=np.asarray(candidate.convert("L").resize((128,192),Image.Resampling.LANCZOS),dtype=np.float32)
    a=(a-a.mean()).ravel();b=(b-b.mean()).ravel()
    return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)))


def main():
    app=QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion");app.setStyleSheet(app_stylesheet())
    state={"code":1};window=CanonStyleStudioQt();window.show()

    def open_portrait():
        if not RAW.exists():
            state.update(code=0,skip="portrait sample unavailable");window.dirty=False;window.close();return
        window.references=[RAW];window.filmstrip.set_references(window.references,0);window.select_reference(0)

    def exercise():
        try:
            assert window.camera_btn.objectName()=="AccentButton"
            # The control sidebar used to be capped at 390 px, making several
            # rows overflow and creating a horizontal scrollbar. It must remain
            # user-resizable while the viewer receives the remaining width.
            window.content_splitter.setSizes([620,1060]);app.processEvents()
            assert window.sidebar.width()>=520,window.sidebar.width()
            assert window.sidebar_scroll.horizontalScrollBarPolicy()==Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            state["sidebar_expanded_width"]=window.sidebar.width()
            window.content_splitter.setSizes([430,1250]);app.processEvents()
            assert window.last_canon_base is not None,"Canon portrait render did not finish"
            assert window.last_canon_base.height>window.last_canon_base.width,window.last_canon_base.size
            assert "DPP4Lib" in str(window.raw_info.get("decoder","")),window.raw_info
            window.zoom_combo.setCurrentText("100%")
            window.viewer.setViewState(0.37,0.61,0.44,"100%")
            before=(tuple(window.viewer.center),window.viewer.split,window.viewer.zoom_mode)
            window.recipe_wb_red.setValue(4);window.recipe_wb_blue.setValue(-5)
            window.exposure.setValue(1.2);window.ab_shift.setValue(3);window.gm_shift.setValue(-2)
            # Programmatic slider changes do not emit sliderReleased; mirror the
            # real interaction so the native-detail render is scheduled.
            window.commit_history()
            state["before"]=before
            QTimer.singleShot(1200,verify_stable_view)
            QTimer.singleShot(6500,verify_safe_detail)
        except Exception:
            state["error"]=traceback.format_exc();finish()

    def verify_stable_view():
        try:
            after=(tuple(window.viewer.center),window.viewer.split,window.viewer.zoom_mode)
            assert after==state["before"],{"before":state["before"],"after":after}
            assert window.viewer.input_pil.size==window.viewer.result_pil.size
            assert abs(window.last_canon_settings["exposure"]-1.2)<1e-6,window.last_canon_settings
            assert window.last_canon_settings["wb_ab_shift"]==3.0,window.last_canon_settings
            assert window.last_canon_settings["wb_gm_shift"]==-2.0,window.last_canon_settings
            assert window.controls_dict()["recipe_wb"]=={"red":4,"blue":-5},window.controls_dict()
            assert "Fast preview" not in window.status.text(),window.status.text()
            state["working_view"]=after
        except Exception:
            state["error"]=traceback.format_exc();finish()

    def verify_safe_detail():
        try:
            after=(tuple(window.viewer.center),window.viewer.split,window.viewer.zoom_mode)
            assert after==state["before"],{"before":state["before"],"after":after}
            assert not window.last_canon_native,window.raw_info
            assert window.last_canon_resolution=="portrait-safe",window.raw_info
            assert window.source_native_size==(4020,6024),window.source_native_size
            assert window.viewer.logical_size==window.source_native_size
            assert window.viewer.input_pil.size==(1080,1618),window.viewer.input_pil.size
            score=structure_correlation(window.source_full,window.viewer.input_pil)
            assert score>0.55,score
            state["structure"]=score
            generation=window.render_generation
            window.request_zoom_resolution("100%")
            assert window.render_generation==generation,"portrait-safe detail was needlessly re-rendered"
            window.zoom_combo.setCurrentText("Fit")
            assert tuple(window.viewer.center)==(0.5,0.5),window.viewer.center
            window.base_combo.setCurrentText("Standard");app.processEvents()
            assert window.base_resolution and window.base_resolution.get("validated"),window.base_resolution
            assert window.project_document().edit.get("basePictureStyle")=="Standard"
            state["creative_reference"]=np.asarray(window.viewer.result_pil,dtype=np.int16).copy()
            window.color_chrome.setCurrentText("Strong")
            QTimer.singleShot(1000,verify_chrome_ui)
        except Exception:
            state["error"]=traceback.format_exc()
            finish()

    def verify_chrome_ui():
        try:
            current=np.asarray(window.viewer.result_pil,dtype=np.int16)
            delta=float(np.abs(current-state["creative_reference"]).mean())
            assert delta>0.05,delta
            state["chrome_delta"]=delta
            assert window.project_document().edit["creative"]["color_chrome"]=="Strong"
            window.color_chrome.setCurrentText("Off");window.color_chrome_blue.setCurrentText("Strong")
            QTimer.singleShot(1000,verify_blue_chrome_ui)
        except Exception:
            state["error"]=traceback.format_exc();finish()

    def verify_blue_chrome_ui():
        try:
            current=np.asarray(window.viewer.result_pil,dtype=np.int16)
            delta=float(np.abs(current-state.pop("creative_reference")).mean())
            assert delta>0.25,delta
            state["blue_chrome_delta"]=delta
            creative=window.project_document().edit.get("creative")
            assert creative["color_chrome"]=="Off" and creative["color_chrome_fx_blue"]=="Strong",creative
            window.recipe_highlight.setValue(-2);window.recipe_shadow.setValue(-1);window.recipe_color.setValue(1);app.processEvents()
            creative=window.project_document().edit.get("creative")
            assert (creative["recipe_highlight"],creative["recipe_shadow"],creative["recipe_color"])==(-2,-1,1),creative
            export_dialog=ExportDialog(window,window)
            QTimer.singleShot(50,export_dialog.close_button.click)
            dialog_result=export_dialog.exec()
            assert not export_dialog.isVisible(),"PF3 export dialog did not close"
            camera_ready=False
            asset_folder=(os.environ.get("CANON_STYLE_STUDIO_RP_ASSETS") or
                          window.settings.data.get("camera_assets_folder"))
            if asset_folder:
                window.settings.data["camera_assets_folder"]=asset_folder
                camera_dialog=CameraInstallDialog(window,window)
                app.processEvents()
                assert camera_dialog.assets is not None
                assert camera_dialog.prepare_button.isEnabled()
                camera_ready=True
                camera_dialog.close()
            rendered_portrait=window.last_canon_base.size;native_size=window.source_native_size
            identity=HERE/"example_luts"/"hald_identity_8.png"
            window.add_lut_paths([identity]);app.processEvents()
            assert len(window.luts)==1
            with tempfile.TemporaryDirectory() as td:
                portable=Path(td)/"ui portable.canonstyleproject"
                assert window.save_project_to(portable)
                assert zipfile.is_zipfile(portable)
                window.open_project(portable);app.processEvents()
                assert not window.references,window.references
                assert window.viewer.input_pil is None,"old reference image remained visible after portable project load"
                assert len(window.luts)==1 and Path(window.luts[0]["cube"]["path"]).is_file(),window.luts
                assert window.project_document().edit["creative"]["color_chrome_fx_blue"]=="Strong"
                assert (window.recipe_highlight.value(),window.recipe_shadow.value(),window.recipe_color.value())==(-2,-1,1)
                assert window.status.text().startswith("Portable project loaded"),window.status.text()
            state["portable_project_ui"]=True
            state.update(code=0,portrait=rendered_portrait,native=native_size,
                         structure=state["structure"],fit_center=tuple(window.viewer.center),status=window.status.text(),generation=window.render_generation,
                         base=window.base_resolution.get("style"),creative_controls=True,export_dialog_result=dialog_result,camera_dialog_ready=camera_ready)
        except Exception:
            state["error"]=traceback.format_exc()
        finish()

    def finish():
        window.dirty=False;window.close();app.quit()

    QTimer.singleShot(100,open_portrait)
    QTimer.singleShot(5000,exercise)
    QTimer.singleShot(30000,lambda:(state.setdefault("error","timeout"),finish()))
    app.exec();print(state)
    return int(state.get("code",1))


if __name__=="__main__":raise SystemExit(main())
