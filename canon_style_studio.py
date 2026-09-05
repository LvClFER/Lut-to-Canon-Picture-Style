from __future__ import annotations

import os
import sys
import json
import uuid
import shutil
import traceback
from datetime import datetime
from collections import OrderedDict
from pathlib import Path


# PyInstaller's one-directory layout keeps the Qt and Shiboken native DLLs in
# sibling folders under ``sys._MEIPASS``.  Register them before the first
# PySide6 import so the standalone build does not depend on a system Python or
# on DLL search paths left behind by another Qt installation.
_FROZEN_DLL_DIRECTORY_HANDLES = []
if os.name == "nt" and getattr(sys, "frozen", False):
    _frozen_runtime = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    for _dll_dir in (_frozen_runtime / "PySide6", _frozen_runtime / "shiboken6", _frozen_runtime):
        if _dll_dir.is_dir():
            _FROZEN_DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(_dll_dir)))

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from PySide6.QtCore import Qt, Signal, QObject, QRunnable, QThreadPool, QTimer, QSize, QPoint, QPointF, QRectF, QMimeData
from PySide6.QtGui import QAction, QKeySequence, QColor, QPainter, QPen, QBrush, QPixmap, QImage, QIcon, QFont, QDrag
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QToolButton, QComboBox, QSlider, QCheckBox, QFileDialog, QMessageBox,
    QFrame, QScrollArea, QSizePolicy, QSplitter, QLineEdit, QMenu, QDialog,
    QDialogButtonBox, QFormLayout, QProgressBar, QTextEdit, QSpinBox, QDoubleSpinBox,
    QListWidget, QListWidgetItem, QAbstractItemView, QStackedLayout, QButtonGroup
)

from canon_engine import (
    CanonRenderEngine, parse_lut_file, inspect_pf3, export_pf3, load_reference_image,
    sample_custom_wb, normalize_rgb_gains,
    find_dll, ensure_runtime_base_pf3, resolve_validated_base_pf3, load_lut_metadata,
    file_fingerprint, CANON_STRONG_RAW_EXTENSIONS, NORMAL_IMAGE_EXTENSIONS,
    HALD_IMAGE_EXTENSIONS,
)
from project_state import SettingsStore, ProjectDocument, save_project, load_project, HistoryManager, app_config_dir
from dpp_client import DppBackendClient, DppBackendError
from render_geometry import fit_size_within_box, oriented_native_size
from canon_runtime import (
    PUBLIC_NAME, PUBLIC_VERSION, BUILD_ID, discover_pse, ensure_runtime_input_profile,
    runtime_environment, sanitize_path, system_summary, reports_dir, logs_dir, sha256_file,
    exported_styles_dir,
)
from test_report import create_test_report_zip
from camera_install.ui import CameraInstallDialog
from camera_install.rp_assets import discover_rp_assets
from creative_controls import (
    AXIS_NAMES, DEFAULT_CREATIVE_CONTROLS, DEFAULT_RECIPE_WB, IDENTITY_TONE_CURVE,
    evaluate_tone_curve, normalize_creative_controls, normalize_recipe_wb,
)

HERE = Path(__file__).resolve().parent
APP_VERSION = PUBLIC_VERSION
CANON_PORTRAIT_SAFE_BOX = (1080, 1620)

BASES = {
    "Neutral": None,
    "Faithful": None,
    "Standard": None,
    "Portrait": None,
    "Landscape": None,
    "Fine Detail": None,
}
HALD_TEMPLATE = HERE / "example_luts" / "Lightroom_Hald_Template_512_64cube_sRGB_16bit.tif"


def dpp_worker_program():
    return HERE/("canon_dpp_worker.exe" if getattr(sys,"frozen",False) else "canon_dpp_worker.py")


ACCENT = "#73A7FF"
BG = "#181A1D"
PANEL = "#202327"
PANEL_2 = "#262A2F"
VIEW_BG = "#111315"
TEXT = "#E8EAF0"
MUTED = "#9AA1AB"
BORDER = "#343940"
DANGER = "#FF6B6B"


def app_stylesheet():
    return f"""
    QMainWindow, QWidget {{ background: {BG}; color: {TEXT}; font-family: 'Segoe UI'; font-size: 10pt; }}
    QFrame#TopBar {{ background: {PANEL}; border-bottom: 1px solid {BORDER}; }}
    QFrame#SideBar {{ background: {PANEL}; border-right: 1px solid {BORDER}; }}
    QFrame#BottomBar {{ background: {PANEL}; border-top: 1px solid {BORDER}; }}
    QLabel#Muted {{ color: {MUTED}; }}
    QLabel#SectionTitle {{ font-weight: 600; font-size: 10pt; }}
    QLabel#AppTitle {{ font-weight: 700; font-size: 12pt; }}
    QPushButton, QToolButton {{
        background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px;
        padding: 6px 10px; color: {TEXT};
    }}
    QPushButton:hover, QToolButton:hover {{ border-color: #505762; background: #2B3036; }}
    QPushButton:pressed, QToolButton:pressed {{ background: #303640; }}
    QPushButton#AccentButton {{ background: {ACCENT}; border-color: {ACCENT}; color: #101318; font-weight: 700; }}
    QPushButton#AccentButton:hover {{ background: #8AB6FF; }}
    QPushButton#AccentButton:disabled {{ background: #3A414B; border-color: #454D58; color: #8A929E; }}
    QPushButton[eyedropperActive="true"] {{ background: {ACCENT}; border-color: {ACCENT}; color: #101318; font-weight: 700; }}
    QPushButton[eyedropperActive="true"]:hover {{ background: #8AB6FF; }}
    QToolButton#FlatButton {{ background: transparent; border: 0; padding: 5px 7px; }}
    QToolButton#FlatButton:hover {{ background: #2A2E33; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background: #17191C; border: 1px solid {BORDER}; border-radius: 6px; padding: 5px 7px;
        selection-background-color: {ACCENT};
    }}
    QComboBox::drop-down {{ border: 0; width: 24px; }}
    QSlider::groove:horizontal {{ height: 4px; background: #3A3F46; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ width: 13px; margin: -5px 0; background: #DDE7FF; border: 1px solid {ACCENT}; border-radius: 7px; }}
    QScrollArea {{ border: 0; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: #464C55; border-radius: 4px; min-height: 30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QListWidget#LutList {{ background: transparent; border: 0; outline: 0; }}
    QListWidget#LutList::item {{ background: transparent; border: 0; margin: 2px 0; }}
    QListWidget#LutList::item:selected {{ background: transparent; }}
    QFrame#LutCard {{ background: #24282D; border: 1px solid {BORDER}; border-radius: 8px; }}
    QFrame#LutCard:hover {{ border-color: #4B535D; }}
    QLabel#Badge {{ background: #30353C; color: #B9C0CA; border-radius: 4px; padding: 2px 5px; font-size: 8pt; }}
    QFrame#SectionBody {{ background: transparent; }}
    QToolButton#SectionHeader {{ background: transparent; border: 0; padding: 8px 3px; text-align: left; font-weight: 700; }}
    QToolButton#SectionHeader:hover {{ background: #25292E; }}
    QProgressBar {{ border: 1px solid {BORDER}; border-radius: 5px; background: #17191C; text-align:center; }}
    QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}
    QTextEdit {{ background: #111315; border: 1px solid {BORDER}; border-radius: 6px; font-family: Consolas; }}
    """


def pil_to_qimage(im: Image.Image) -> QImage:
    rgb=im if im.mode=="RGB" else im.convert("RGB")
    arr = np.asarray(rgb, dtype=np.uint8)
    h, w = arr.shape[:2]
    return QImage(arr.data, w, h, w * 3, QImage.Format.Format_RGB888).copy()


def pil_to_qpixmap(im: Image.Image) -> QPixmap:
    return QPixmap.fromImage(pil_to_qimage(im))


def make_clipped_display(im: Image.Image) -> Image.Image:
    arr = np.asarray(im.convert("RGB"), dtype=np.uint8).copy()
    hi = np.max(arr, axis=2) >= 253
    lo = np.max(arr, axis=2) <= 3
    out = arr.astype(np.float32)
    out[hi] = out[hi] * 0.35 + np.array([255, 55, 55], dtype=np.float32) * 0.65
    out[lo] = out[lo] * 0.35 + np.array([55, 100, 255], dtype=np.float32) * 0.65
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str, str)
    progress = Signal(float)
    message = Signal(str)
    finished = Signal()


class FunctionWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e), traceback.format_exc())
        finally:
            # Important: lets the main window release its strong Python
            # reference only after queued result/error signals have been emitted.
            self.signals.finished.emit()


class CollapsibleSection(QWidget):
    def __init__(self, title, parent=None, expanded=True):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
        self.header = QToolButton(text=title, checkable=True, checked=expanded)
        self.header.setObjectName("SectionHeader")
        self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.header.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        lay.addWidget(self.header)
        self.body = QFrame(); self.body.setObjectName("SectionBody")
        self.body_layout = QVBoxLayout(self.body); self.body_layout.setContentsMargins(4, 2, 4, 10); self.body_layout.setSpacing(7)
        self.body.setVisible(expanded); lay.addWidget(self.body)
        self.header.toggled.connect(self._toggle)

    def _toggle(self, on):
        self.body.setVisible(on)
        self.header.setArrowType(Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow)


class ValueSlider(QWidget):
    changed = Signal(float)
    committed = Signal()
    interaction = Signal()

    def __init__(self, label, minimum, maximum, value, scale=1.0, suffix="", parent=None):
        super().__init__(parent)
        self.scale = float(scale); self.suffix = suffix
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(3)
        top = QHBoxLayout(); top.setContentsMargins(0,0,0,0)
        self.name = QLabel(label); self.value_label = QLabel(); self.value_label.setObjectName("Muted")
        top.addWidget(self.name); top.addStretch(); top.addWidget(self.value_label); lay.addLayout(top)
        self.slider = QSlider(Qt.Orientation.Horizontal); self.slider.setRange(int(minimum), int(maximum)); self.slider.setValue(int(round(value / self.scale)))
        lay.addWidget(self.slider)
        self.slider.valueChanged.connect(self._changed)
        self.slider.sliderMoved.connect(lambda _v: self.interaction.emit())
        self.slider.sliderReleased.connect(self.committed.emit)
        self._refresh()

    def _refresh(self):
        v = self.value()
        if self.scale != 1.0:
            txt = f"{v:+.1f}{self.suffix}" if v != 0 else f"0.0{self.suffix}"
        else:
            txt = f"{int(v):+d}{self.suffix}" if v != 0 else f"0{self.suffix}"
        self.value_label.setText(txt)

    def _changed(self, _v):
        self._refresh(); self.changed.emit(self.value())

    def value(self): return self.slider.value() * self.scale
    def setValue(self, value): self.slider.setValue(int(round(float(value) / self.scale)))


class ToneCurveWidget(QWidget):
    pointsChanged = Signal(object)
    committed = Signal()

    def __init__(self,parent=None):
        super().__init__(parent);self._points=list(IDENTITY_TONE_CURVE);self._active=None
        self.setMinimumHeight(150);self.setMaximumHeight(190);self.setCursor(Qt.CursorShape.CrossCursor)
        self.setToolTip("Drag one of the five fixed-input points. Double-click to reset the curve.")

    def points(self):return list(self._points)

    def setPoints(self,points):
        normalized=normalize_creative_controls({"tone_curve":points})["tone_curve"]
        self._points=list(normalized);self.update()

    def _plot_rect(self):return QRectF(12,8,max(10,self.width()-24),max(10,self.height()-20))

    def _point_position(self,index):
        rect=self._plot_rect();x=index/(len(self._points)-1)
        return QPointF(rect.left()+x*rect.width(),rect.bottom()-self._points[index]*rect.height())

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        rect=self._plot_rect();painter.fillRect(rect,QColor("#111315"));painter.setPen(QPen(QColor("#343940"),1))
        for index in range(5):
            fraction=index/4.0
            painter.drawLine(QPointF(rect.left()+fraction*rect.width(),rect.top()),QPointF(rect.left()+fraction*rect.width(),rect.bottom()))
            painter.drawLine(QPointF(rect.left(),rect.top()+fraction*rect.height()),QPointF(rect.right(),rect.top()+fraction*rect.height()))
        painter.setPen(QPen(QColor("#59616C"),1,Qt.PenStyle.DashLine));painter.drawLine(rect.bottomLeft(),rect.topRight())
        painter.setPen(QPen(QColor(ACCENT),2));previous=self._point_position(0)
        samples=96;curve=evaluate_tone_curve(np.linspace(0.0,1.0,samples+1),self._points)
        for sample in range(1,samples+1):
            y=float(curve[sample])
            current=QPointF(rect.left()+sample/samples*rect.width(),rect.bottom()-y*rect.height())
            painter.drawLine(previous,current);previous=current
        for index in range(len(self._points)):
            point=self._point_position(index);painter.setBrush(QBrush(QColor("#DDE7FF") if index!=self._active else QColor(ACCENT)));painter.setPen(QPen(QColor(ACCENT),1));painter.drawEllipse(point,5,5)

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        self._active=min(range(len(self._points)),key=lambda index:abs(self._point_position(index).x()-event.position().x()))
        self._move(event.position());event.accept()

    def mouseMoveEvent(self,event):
        if self._active is not None and event.buttons()&Qt.MouseButton.LeftButton:self._move(event.position());event.accept()

    def mouseReleaseEvent(self,event):
        if self._active is not None:self._move(event.position());self._active=None;self.update();self.committed.emit();event.accept()

    def mouseDoubleClickEvent(self,event):
        self.setPoints(IDENTITY_TONE_CURVE);self.pointsChanged.emit(self.points());self.committed.emit();event.accept()

    def _move(self,position):
        if self._active is None:return
        rect=self._plot_rect();value=max(0.0,min(1.0,(rect.bottom()-position.y())/max(1.0,rect.height())))
        if self._active>0:value=max(value,self._points[self._active-1])
        if self._active<len(self._points)-1:value=min(value,self._points[self._active+1])
        if abs(value-self._points[self._active])<1e-6:return
        self._points[self._active]=round(value,6);self.update();self.pointsChanged.emit(self.points())


class DragHandle(QLabel):
    def __init__(self, entry_id, parent=None):
        super().__init__("≡", parent); self.entry_id=entry_id; self._press=None; self.setCursor(Qt.CursorShape.OpenHandCursor); self.setToolTip("Drag to reorder")
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self._press=event.position().toPoint(); self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if self._press is None or not (event.buttons() & Qt.MouseButton.LeftButton): return
        if (event.position().toPoint()-self._press).manhattanLength() < QApplication.startDragDistance(): return
        drag=QDrag(self); mime=QMimeData(); mime.setData("application/x-canonstyle-lut-id",self.entry_id.encode("utf-8")); drag.setMimeData(mime); drag.exec(Qt.DropAction.MoveAction); self._press=None; self.setCursor(Qt.CursorShape.OpenHandCursor)
    def mouseReleaseEvent(self,event): self._press=None; self.setCursor(Qt.CursorShape.OpenHandCursor); super().mouseReleaseEvent(event)


class LutCard(QFrame):
    changed = Signal(); committed = Signal(); removeRequested = Signal(str)

    def __init__(self, entry, parent=None):
        super().__init__(parent); self.entry = entry; self.setObjectName("LutCard")
        self.setMinimumHeight(94)
        lay = QVBoxLayout(self); lay.setContentsMargins(9, 7, 9, 7); lay.setSpacing(5)
        row = QHBoxLayout(); row.setSpacing(6)
        self.handle = DragHandle(entry["id"]); self.handle.setObjectName("Muted")
        self.enabled = QCheckBox(); self.enabled.setChecked(bool(entry.get("enabled", True)))
        self.title = QLabel(entry["cube"]["title"]); self.title.setStyleSheet("font-weight:600;")
        meta = entry["cube"]
        if meta.get("source") == "hald":
            cs = meta.get("color_space", "")
            if len(cs) > 18: cs = cs[:18] + "…"
            badge = f"HALD {meta['size']}³ · {meta.get('bit_depth','?')}b"
            if cs and cs != "Unspecified": badge += f" · {cs}"
        else:
            badge = f"CUBE {meta['size']}³"
        lut_metadata=entry.get("metadata") or {}
        preferred=lut_metadata.get("preferredBaseStyle")
        if preferred:badge+=f" · {preferred} base"
        self.badge = QLabel(badge); self.badge.setObjectName("Badge")
        if lut_metadata:
            details=[f"{key}: {value}" for key,value in lut_metadata.items() if value not in (None,"")]
            self.badge.setToolTip("\n".join(details))
        self.more = QToolButton(text="⋯"); self.more.setObjectName("FlatButton")
        row.addWidget(self.handle); row.addWidget(self.enabled); row.addWidget(self.title, 1); row.addWidget(self.badge); row.addWidget(self.more)
        lay.addLayout(row)
        row2 = QHBoxLayout(); row2.setSpacing(6)
        self.opacity = QSlider(Qt.Orientation.Horizontal); self.opacity.setRange(0,100); self.opacity.setValue(round(float(entry.get("opacity",1.0))*100))
        self.oplabel = QLabel(f"{self.opacity.value()}%"); self.oplabel.setObjectName("Muted"); self.oplabel.setMinimumWidth(38)
        row2.addSpacing(27); row2.addWidget(self.opacity, 1); row2.addWidget(self.oplabel); lay.addLayout(row2)
        self.enabled.toggled.connect(self._on_enabled)
        self.opacity.valueChanged.connect(self._on_opacity)
        self.opacity.sliderReleased.connect(self.committed.emit)
        self.more.clicked.connect(self._menu)

    def _on_enabled(self, on):
        self.entry["enabled"] = bool(on); self.changed.emit(); self.committed.emit()
    def _on_opacity(self, v):
        self.entry["opacity"] = v / 100.0; self.oplabel.setText(f"{v}%"); self.changed.emit()
    def _menu(self):
        menu = QMenu(self)
        rm = menu.addAction("Remove")
        reveal = menu.addAction("Open containing folder")
        act = menu.exec(self.more.mapToGlobal(self.more.rect().bottomLeft()))
        if act == rm: self.removeRequested.emit(self.entry["id"])
        elif act == reveal:
            p = Path(self.entry["cube"]["path"])
            try:
                os.startfile(str(p.parent))
            except Exception: pass


class LutList(QListWidget):
    orderChanged = Signal()
    filesDropped = Signal(list)
    reorderRequested = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("LutList")
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAcceptDrops(True); self.setDropIndicatorShown(True); self.setSpacing(3)

    def dragEnterEvent(self, event):
        md=event.mimeData()
        if md.hasUrls() or md.hasFormat("application/x-canonstyle-lut-id"): event.acceptProposedAction(); return
        super().dragEnterEvent(event)
    def dragMoveEvent(self, event):
        md=event.mimeData()
        if md.hasUrls() or md.hasFormat("application/x-canonstyle-lut-id"): event.acceptProposedAction(); return
        super().dragMoveEvent(event)
    def dropEvent(self, event):
        md=event.mimeData()
        if md.hasUrls():
            paths=[u.toLocalFile() for u in md.urls() if u.toLocalFile()]
            self.filesDropped.emit(paths); event.acceptProposedAction(); return
        if md.hasFormat("application/x-canonstyle-lut-id"):
            eid=bytes(md.data("application/x-canonstyle-lut-id")).decode("utf-8",errors="ignore")
            pos=event.position().toPoint(); idx=self.indexAt(pos); target=self.count()
            if idx.isValid():
                target=idx.row(); rect=self.visualItemRect(self.item(target))
                if pos.y()>rect.center().y(): target+=1
            self.reorderRequested.emit(eid,target); event.acceptProposedAction(); return
        super().dropEvent(event)


class CompareView(QWidget):
    pixelInfo = Signal(object, object)
    pixelClicked = Signal(object)
    viewChanged = Signal(float, float, float, str)

    def __init__(self, parent=None):
        super().__init__(parent); self.setMouseTracking(True); self.setAcceptDrops(False)
        self.input_pil = None; self.result_pil = None; self.input_q = None; self.result_q = None; self.clipped_q = None
        # The displayed frame can be a fast Canon working render while its logical
        # geometry remains the full oriented RAW.  Fixed zoom percentages are based
        # on this native geometry, so replacing a 1620 px frame with a native frame
        # never changes zoom, crop or pan.
        self.logical_size = None
        self.mode = "Side by side"; self.zoom_mode = "Fit"; self.center = [0.5,0.5]; self.split = 0.5
        self.dragging=False; self.split_drag=False; self.last_pos=QPoint(); self.rendering=False; self.show_clipping=False; self.eyedropper=False
        self.eyedropper_sample=None
        self.setMinimumSize(500, 400); self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)

    def setImages(self, input_im, result_im, logical_size=None):
        self.input_pil=input_im if input_im.mode=="RGB" else input_im.convert("RGB")
        self.result_pil=result_im if result_im.mode=="RGB" else result_im.convert("RGB")
        self.input_q=pil_to_qimage(self.input_pil); self.result_q=pil_to_qimage(self.result_pil)
        try:
            lw,lh=(int(logical_size[0]),int(logical_size[1])) if logical_size else self.input_pil.size
            self.logical_size=(lw,lh) if lw>0 and lh>0 else self.input_pil.size
        except Exception:
            self.logical_size=self.input_pil.size
        self.clipped_q=pil_to_qimage(make_clipped_display(self.result_pil)) if self.show_clipping else None
        self.update()
    def clearImages(self):
        self.input_pil=None;self.result_pil=None;self.input_q=None;self.result_q=None;self.clipped_q=None;self.logical_size=None
        self.rendering=False;self.eyedropper_sample=None;self.update()
    def setMode(self, mode): self.mode=mode; self.update()
    def setZoomMode(self, mode):
        self.zoom_mode=mode
        if mode=="Fit":self.center=[0.5,0.5]
        self.update();self._emit_view()
    def setClipping(self,on):
        self.show_clipping=bool(on)
        if self.show_clipping and self.result_pil is not None and self.clipped_q is None:
            self.clipped_q=pil_to_qimage(make_clipped_display(self.result_pil))
        self.update()
    def setRendering(self,on): self.rendering=bool(on); self.update()
    def setEyedropper(self,on):
        self.eyedropper=bool(on)
        if self.eyedropper:self.setCursor(Qt.CursorShape.CrossCursor)
        else:self.unsetCursor()
        self.update()
    def setEyedropperSample(self,point):
        if point is None or not self.input_q:self.eyedropper_sample=None
        else:self.eyedropper_sample=(float(point[0])/max(1,self.input_q.width()),float(point[1])/max(1,self.input_q.height()))
        self.update()
    def clearEyedropperSample(self):self.eyedropper_sample=None;self.update()
    def setViewState(self,cx,cy,split=None,zoom_mode=None):
        if zoom_mode is not None:self.zoom_mode=str(zoom_mode)
        self.center=[0.5,0.5] if self.zoom_mode=="Fit" else [float(cx),float(cy)]
        if split is not None:self.split=float(split)
        self.update()
    def _emit_view(self): self.viewChanged.emit(self.center[0],self.center[1],self.split,self.zoom_mode)

    def _pane_rects(self):
        r=QRectF(self.rect())
        if self.mode=="Side by side":
            mid=r.width()/2.0
            return QRectF(0,0,mid-2,r.height()), QRectF(mid+2,0,r.width()-mid-2,r.height())
        return r,r

    def _logical_dimensions(self):
        if self.logical_size:
            return float(self.logical_size[0]),float(self.logical_size[1])
        if self.input_q:
            return float(self.input_q.width()),float(self.input_q.height())
        return 1.0,1.0

    def _scale_for(self,pane):
        if not self.input_q: return 1.0
        lw,lh=self._logical_dimensions()
        if self.zoom_mode=="Fit":
            return min(pane.width()/lw, pane.height()/lh)
        try: return max(0.05,float(self.zoom_mode.rstrip('%'))/100.0)
        except Exception:return 1.0

    def _draw_image(self,painter,qimg,pane,clip=None):
        if not qimg:return
        s=self._scale_for(pane);lw,lh=self._logical_dimensions();iw=lw*s;ih=lh*s
        x=pane.center().x()-self.center[0]*iw; y=pane.center().y()-self.center[1]*ih
        dest=QRectF(x,y,iw,ih)
        painter.save()
        painter.setClipRect(clip if clip is not None else pane)
        # Use high-quality resampling only when source and destination geometries
        # differ. At native 100% leave pixels unfiltered for real detail inspection.
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,
                              abs(iw-qimg.width())>0.01 or abs(ih-qimg.height())>0.01)
        painter.drawImage(dest,qimg,QRectF(0,0,qimg.width(),qimg.height()))
        painter.restore()

    def paintEvent(self,event):
        p=QPainter(self); p.fillRect(self.rect(),QColor(VIEW_BG)); left,right=self._pane_rects()
        rq=self.clipped_q if self.show_clipping else self.result_q
        if self.mode=="Side by side":
            self._draw_image(p,self.input_q,left); self._draw_image(p,rq,right)
            p.setPen(QPen(QColor(BORDER),1)); p.drawLine(int(left.right()+2),0,int(left.right()+2),self.height())
            p.setPen(QColor(MUTED)); p.drawText(left.adjusted(12,10,-12,-10),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop,"ORIGINAL")
            p.drawText(right.adjusted(12,10,-12,-10),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop,"PREVIEW")
        elif self.mode=="Split":
            self._draw_image(p,self.input_q,left)
            sx=self.width()*self.split
            self._draw_image(p,rq,right,QRectF(sx,0,self.width()-sx,self.height()))
            p.setPen(QPen(QColor(ACCENT),2)); p.drawLine(int(sx),0,int(sx),self.height())
            p.setBrush(QColor(ACCENT)); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(sx,self.height()/2),5,18)
        elif self.mode=="Original": self._draw_image(p,self.input_q,left)
        else: self._draw_image(p,rq,right)
        if self.eyedropper:
            width=min(430,max(270,self.width()-32)); box=QRectF((self.width()-width)/2.0,14,width,36)
            p.setPen(QPen(QColor(ACCENT),2));p.setBrush(QColor(24,29,36,235));p.drawRoundedRect(box,8,8)
            p.setPen(QColor("#DDE7FF"));p.drawText(box,Qt.AlignmentFlag.AlignCenter,"WB EYEDROPPER ON · CLICK A NEUTRAL AREA")
        if self.eyedropper_sample and self.input_q:
            fx,fy=self.eyedropper_sample
            pane=left
            if self.mode=="Side by side":pane=left
            s=self._scale_for(pane);lw,lh=self._logical_dimensions();iw=lw*s;ih=lh*s
            x0=pane.center().x()-self.center[0]*iw;y0=pane.center().y()-self.center[1]*ih
            px=x0+fx*iw;py=y0+fy*ih
            p.setPen(QPen(QColor("#FFFFFF"),2));p.setBrush(Qt.BrushStyle.NoBrush);p.drawEllipse(QPointF(px,py),10,10)
            p.setPen(QPen(QColor(ACCENT),2));p.drawLine(QPointF(px-15,py),QPointF(px+15,py));p.drawLine(QPointF(px,py-15),QPointF(px,py+15))
        if self.rendering:
            box=QRectF(self.width()-132,14,116,30); p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(30,33,37,220)); p.drawRoundedRect(box,7,7)
            p.setPen(QColor(TEXT)); p.drawText(box,Qt.AlignmentFlag.AlignCenter,"Rendering…")

    def _image_coord(self,pos):
        if not self.input_q:return None
        left,right=self._pane_rects(); pane=left
        if self.mode=="Side by side": pane=left if pos.x()<self.width()/2 else right
        s=self._scale_for(pane);lw,lh=self._logical_dimensions();iw=lw*s;ih=lh*s
        x0=pane.center().x()-self.center[0]*iw; y0=pane.center().y()-self.center[1]*ih
        lx=(pos.x()-x0)/s;ly=(pos.y()-y0)/s
        if 0<=lx<lw and 0<=ly<lh:
            ix=min(self.input_q.width()-1,max(0,int(lx*self.input_q.width()/lw)))
            iy=min(self.input_q.height()-1,max(0,int(ly*self.input_q.height()/lh)))
            return ix,iy,pane,s
        return None

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            if self.eyedropper:
                c=self._image_coord(event.position())
                if c and self.input_pil:
                    ix,iy,_,_=c;self.setEyedropperSample((ix,iy));self.pixelClicked.emit({"point":(ix,iy),"rgb":self.input_pil.getpixel((ix,iy))})
                event.accept();return
            if self.mode=="Split" and abs(event.position().x()-self.width()*self.split)<12:
                self.split_drag=True
            elif self.zoom_mode!="Fit":
                self.dragging=True; self.last_pos=event.position().toPoint()
            c=self._image_coord(event.position())
            if c and self.input_pil:
                ix,iy,_,_=c; self.pixelClicked.emit({"point":(ix,iy),"rgb":self.input_pil.getpixel((ix,iy))})
    def mouseMoveEvent(self,event):
        c=self._image_coord(event.position())
        if c and self.input_pil and self.result_pil:
            ix,iy,_,_=c; self.pixelInfo.emit(self.input_pil.getpixel((ix,iy)),self.result_pil.getpixel((ix,iy)))
        if self.split_drag:
            self.split=max(0.02,min(0.98,event.position().x()/max(1,self.width()))); self.update(); self._emit_view(); return
        if self.dragging and self.input_q:
            pos=event.position().toPoint(); dx=pos.x()-self.last_pos.x(); dy=pos.y()-self.last_pos.y(); self.last_pos=pos
            pane=self._pane_rects()[0];s=self._scale_for(pane);lw,lh=self._logical_dimensions()
            self.center[0]=max(0,min(1,self.center[0]-dx/max(1,lw*s)))
            self.center[1]=max(0,min(1,self.center[1]-dy/max(1,lh*s)))
            self.update(); self._emit_view()
    def mouseReleaseEvent(self,event): self.dragging=False; self.split_drag=False
    def wheelEvent(self,event):
        levels=["Fit","25%","50%","100%","200%","400%"]
        cur=self.zoom_mode if self.zoom_mode in levels else "Fit"; idx=levels.index(cur)
        if event.angleDelta().y()>0: idx=min(len(levels)-1,idx+1 if idx else 3)
        else: idx=max(0,idx-1)
        self.setZoomMode(levels[idx]);event.accept()


class ScopeWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.image=None; self.mode="Histogram"; self.setMinimumHeight(150)
    def setImage(self,im): self.image=im.copy() if im else None; self.update()
    def setMode(self,mode): self.mode=mode; self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.fillRect(self.rect(),QColor("#101214"))
        if self.image is None:return
        arr=np.asarray(self.image.convert("RGB"),dtype=np.uint8)
        step=max(1,int(np.sqrt(arr.shape[0]*arr.shape[1]/30000))); arr=arr[::step,::step]
        w,h=self.width(),self.height(); p.setRenderHint(QPainter.RenderHint.Antialiasing,False)
        if self.mode=="Histogram":
            colors=[QColor(255,90,90),QColor(90,220,120),QColor(100,140,255)]
            for c,col in enumerate(colors):
                hist=np.bincount(arr[...,c].ravel(),minlength=256).astype(float); hist=np.log1p(hist); hist/=max(hist.max(),1)
                p.setPen(QPen(col,1)); last=None
                for i,v in enumerate(hist):
                    pt=QPointF(i*(w-1)/255.0,h-5-v*(h-12))
                    if last is not None:p.drawLine(last,pt)
                    last=pt
        elif self.mode=="RGB Parade":
            panel=w/3.0; colors=[QColor(255,90,90,90),QColor(90,220,120,90),QColor(100,140,255,90)]
            xs=np.linspace(0,panel-1,arr.shape[1])
            for c,col in enumerate(colors):
                p.setPen(QPen(col,1)); xoff=c*panel
                for yy in range(0,arr.shape[0],max(1,arr.shape[0]//70)):
                    vals=arr[yy,:,c]
                    for x0,v in zip(xs[::2],vals[::2]): p.drawPoint(QPointF(xoff+x0,h-1-(v/255.0)*(h-4)))
        else:
            rgb=arr.reshape(-1,3).astype(np.float32)/255.0; rgb=rgb[::max(1,len(rgb)//12000)]
            y=0.299*rgb[:,0]+0.587*rgb[:,1]+0.114*rgb[:,2]
            u=(rgb[:,2]-y)*0.565; v=(rgb[:,0]-y)*0.713
            cx,cy=w/2,h/2; radius=min(w,h)*0.44
            p.setPen(QPen(QColor(80,85,92),1)); p.drawEllipse(QPointF(cx,cy),radius,radius)
            p.setPen(QPen(QColor(180,190,205,70),1))
            for uu,vv in zip(u,v): p.drawPoint(QPointF(cx+uu*radius*1.8,cy-vv*radius*1.8))


class ReferenceStrip(QScrollArea):
    selected = Signal(int)
    def __init__(self,parent=None):
        super().__init__(parent); self.setWidgetResizable(True); self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded); self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.host=QWidget(); self.lay=QHBoxLayout(self.host); self.lay.setContentsMargins(8,5,8,5); self.lay.setSpacing(6); self.lay.addStretch()
        self.setWidget(self.host); self.setFixedHeight(92); self.buttons=[]
    def clear_refs(self):
        for b in self.buttons: b.deleteLater()
        self.buttons=[]
    def set_references(self,paths,current=0):
        self.clear_refs()
        for i,p in enumerate(paths):
            b=QToolButton(); b.setText(Path(p).name); b.setCheckable(True); b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon); b.setIconSize(QSize(56,42)); b.setFixedSize(118,72); b.clicked.connect(lambda _=False,i=i:self.selected.emit(i)); self.lay.insertWidget(self.lay.count()-1,b); self.buttons.append(b)
        self.set_current(current)
    def set_current(self,i):
        for n,b in enumerate(self.buttons): b.setChecked(n==i)
    def set_thumbnail(self,i,im):
        if 0<=i<len(self.buttons) and im:
            thumb=ImageOps.contain(im,(80,48),Image.Resampling.LANCZOS);self.buttons[i].setIcon(QIcon(pil_to_qpixmap(thumb)))


class SnapshotButton(QToolButton):
    saveRequested = Signal(str); loadRequested = Signal(str); clearRequested = Signal(str)
    def __init__(self,name,parent=None):
        super().__init__(parent); self.name=name; self.setText(name); self.setFixedWidth(34); self.setToolTip(f"Left click: load {name} · Right click: save/clear")
        self.clicked.connect(lambda:self.loadRequested.emit(self.name)); self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.customContextMenuRequested.connect(self._menu)
    def _menu(self,pos):
        m=QMenu(self); save=m.addAction(f"Save current to {self.name}"); clear=m.addAction(f"Clear {self.name}"); a=m.exec(self.mapToGlobal(pos))
        if a==save:self.saveRequested.emit(self.name)
        elif a==clear:self.clearRequested.emit(self.name)
    def setStored(self,on): self.setStyleSheet(f"background:{ACCENT};color:#111;" if on else "")


class ExportDialog(QDialog):
    def __init__(self,main,parent=None):
        super().__init__(parent); self.main=main; self.setWindowTitle("Export Canon PF3"); self.resize(560,430); self.worker=None
        lay=QVBoxLayout(self); title=QLabel("Canon PF3"); title.setStyleSheet("font-size:18pt;font-weight:700;"); lay.addWidget(title)
        self.summary=QLabel(); self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); self.summary.setStyleSheet("line-height:150%;"); lay.addWidget(self.summary)
        self.valid=QLabel("✓ Valid configuration"); self.valid.setStyleSheet(f"color:{ACCENT};font-weight:700;"); lay.addWidget(self.valid)
        row=QHBoxLayout(); self.path=QLineEdit(); browse=QPushButton("Choose…"); browse.clicked.connect(self.choose); row.addWidget(self.path,1); row.addWidget(browse); lay.addLayout(row)
        self.progress=QProgressBar(); self.progress.setRange(0,100); lay.addWidget(self.progress)
        self.log=QTextEdit(); self.log.setReadOnly(True); self.log.setFixedHeight(110); lay.addWidget(self.log)
        row2=QHBoxLayout(); self.close_button=QPushButton("Close"); self.close_button.clicked.connect(self.reject); row2.addWidget(self.close_button); self.open_folder=QPushButton("Open folder"); self.open_folder.setEnabled(False); self.open_folder.clicked.connect(self.open_output_folder); row2.addWidget(self.open_folder); row2.addStretch(); self.export=QPushButton("Export PF3"); self.export.setObjectName("AccentButton"); self.export.clicked.connect(self.start_export); row2.addWidget(self.export); lay.addLayout(row2)
        self.refresh()

    def closeEvent(self,event):
        # Export runs in the serialized engine pool. Closing this modal must
        # always return control to the editor; the in-flight atomic export may
        # finish safely in the background and never blocks the window close.
        event.accept()
    def refresh(self):
        s=self.main.edit_state_dict(); active=[x for x in self.main.luts if x.get("enabled") and x.get("opacity",0)>0]
        validity="validated local template" if s.get("baseTemplateValidated") else "EXPERIMENTAL generated template"
        recipe_wb=normalize_recipe_wb(s.get("recipe_wb"));recipe_wb_text=f"R{recipe_wb['red']:+d} / B{recipe_wb['blue']:+d}" if any(recipe_wb.values()) else "neutral"
        creative=s.get("creative") or {};axes=creative.get("color_axes") or {};active_axes=sum(1 for value in axes.values() if any(value.values()))
        recipe_active=any(int(creative.get(key,0) or 0) for key in ("recipe_highlight","recipe_shadow","recipe_color"))
        creative_active=recipe_active or active_axes or creative.get("color_chrome")!="Off" or creative.get("color_chrome_fx_blue")!="Off" or creative.get("tone_curve")!=IDENTITY_TONE_CURVE
        self.summary.setText(f"Base: <b>{s['base_name']}</b> · {validity}<br>Recipe WB: <b>{recipe_wb_text}</b> · LUT-baked / approximate<br>LUT stack: <b>{len(active)} layers</b> · Creative Color: <b>{'active' if creative_active else 'neutral'}</b><br>Canon table: <b>33³ / 12-bit</b><br>Contrast: <b>{s['contrast']:+d}</b> · Saturation: <b>{s['saturation']:+d}</b> · Color Tone: <b>{s['color_tone']:+d}</b>")
        default=self.main.settings.get_folder("last_export_folder",exported_styles_dir())/(self.main.project_name.text().strip() or "CanonStyle")
        self.path.setText(str(default.with_suffix('.pf3')))
    def choose(self):
        p,_=QFileDialog.getSaveFileName(self,"Export Canon PF3",self.path.text(),"Canon Picture Style (*.pf3)")
        if p:self.path.setText(p);self.main.settings.remember_file("last_export_folder",p)
    def start_export(self):
        p=Path(self.path.text().strip())
        if not p.name:return
        if p.suffix.lower()!=".pf3":
            p=p.with_suffix(".pf3");self.path.setText(str(p))
        self.export.setEnabled(False);self.progress.setValue(0);self.log.clear();self.main.settings.remember_file("last_export_folder",p)
        # Capture every UI value before entering the background worker. No Qt
        # widget or mutable UI state is accessed from the engine thread.
        dll=self.main.dll_path();base=self.main.current_base_path();luts=list(self.main.luts);controls=dict(self.main.controls_dict());title=p.stem
        state=self.main.edit_state_dict();project=self.main.project_document().to_dict();base_info=dict(self.main.base_resolution or {})
        manifest_luts=[{"name":Path(item["cube"]["path"]).name,"enabled":bool(item.get("enabled",True)),"opacity":float(item.get("opacity",1.0)),**(item.get("metadata") or {})} for item in luts]
        self.export_context={"state":state,"project":project,"base":base_info,"output":p,"luts":manifest_luts}
        def work():
            return export_pf3(dll,base,p,luts,controls,title,log=lambda m:self.worker.signals.message.emit(m),progress=lambda v:self.worker.signals.progress.emit(v))
        self.worker=FunctionWorker(work); self.worker.signals.message.connect(self.log.append); self.worker.signals.progress.connect(lambda v:self.progress.setValue(round(v*100))); self.worker.signals.result.connect(self.export_succeeded); self.worker.signals.error.connect(self.failed); self.main.engine_pool.start(self.worker)
    def export_succeeded(self,result):
        size,sha=result; self.progress.setValue(100); self.log.append(f"✓ Generated · {size:,} bytes · validation passed"); self.log.append(f"SHA-256: {sha}"); self.open_folder.setEnabled(True); self.export.setEnabled(True)
        try:
            context=self.export_context;output=Path(context["output"]);state=context["state"];base=context["base"]
            sidecar=output.with_suffix('.canonstyle.json');sidecar.write_text(json.dumps(context["project"],indent=2,ensure_ascii=False),encoding='utf-8')
            manifest={"format":"CanonStyleStudio.PF3Manifest","version":1,"pf3":output.name,"pf3Size":size,"pf3Sha256":sha,
                      "basePictureStyle":state.get("basePictureStyle") or state.get("base_name"),"baseTemplateSource":base.get("source"),
                      "baseTemplateValidated":bool(base.get("validated")),"basePf3Sha256":base.get("sha256"),
                      "canonTable":{"size":33,"bitDepth":12,"properties":["0x40001070","0x40001071"]},
                      "recipeWhiteBalance":{"method":"fuji-xt1-provia-rb-lut-v2","accuracy":"empirically-calibrated-approximation","order":"before-user-lut-stack",**normalize_recipe_wb(state.get("recipe_wb"))},
                      "luts":context["luts"],"creativeControls":state.get("creative") or {}}
            output.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
        except Exception:pass
    def failed(self,msg,tb): self.log.append("ERROR: "+msg);self.log.append(tb);self.export.setEnabled(True)
    def open_output_folder(self):
        try:os.startfile(str(Path(self.path.text()).parent))
        except Exception:pass


class CanonStyleStudioQt(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(f"{PUBLIC_NAME} {APP_VERSION}"); self.resize(1680,980); self.setMinimumSize(1240,760); self.setAcceptDrops(True)
        self.settings=SettingsStore(); self.render_engine=CanonRenderEngine()
        self.recent_internal_logs=[]
        self.canon_install=discover_pse(self.settings.data.get("manual_pse_path"))
        self.runtime_profile=None
        if self.canon_install:
            try:self.runtime_profile=ensure_runtime_input_profile(self.canon_install)
            except Exception:pass
        self.dpp_client=DppBackendClient(dpp_worker_program(), app_config_dir()/"dpp_cache",runtime_environment(self.canon_install,self.runtime_profile))
        self.dpp_backend_state="not tested" if self.canon_install else "pse missing"
        # Keep decode and Canon/render work in separate serialized pools. A slow
        # render must never block opening a new PNG/RAW, while EdsCFParse/render
        # operations remain serialized for safety.
        self.decode_pool=QThreadPool(self); self.decode_pool.setMaxThreadCount(1)
        # Interactive Pillow/LUT previews must never queue behind a slow Canon
        # develop. They have their own single worker and only the latest result wins.
        self.preview_pool=QThreadPool(self); self.preview_pool.setMaxThreadCount(1)
        self.engine_pool=QThreadPool(self); self.engine_pool.setMaxThreadCount(1)
        self._active_workers=set()
        self.references=[]; self.current_reference=-1; self.source_full=None; self.source_native_size=None; self.source_is_raw=False; self.source_embedded=False; self.raw_info={}; self.luts=[]; self.custom_base_path=None; self.current_source_path=None;self.base_resolution=None
        self.creative_controls=normalize_creative_controls(DEFAULT_CREATIVE_CONTROLS)
        self.recipe_wb_controls=normalize_recipe_wb(DEFAULT_RECIPE_WB)
        self.project_path=None; self.snapshots={"A":None,"B":None,"C":None}; self.history=HistoryManager(); self.reference_cache=OrderedDict(); self.applying_state=True; self.render_running=False; self.render_pending=None; self.preview_running=False; self.preview_pending=None; self.render_generation=0; self.load_generation=0; self.eyedropper_active=False; self.custom_wb_mult=None; self.dirty=False; self.last_canon_base=None; self.last_canon_settings=None; self.last_canon_source=None; self.last_canon_native=False; self.last_canon_resolution=None; self.dpp_failure_cache={};self.closing=False
        self.full_render_timer=QTimer(self);self.full_render_timer.setSingleShot(True);self.full_render_timer.timeout.connect(self.start_final_render)
        self.canon_render_timer=QTimer(self);self.canon_render_timer.setSingleShot(True);self.canon_render_timer.timeout.connect(self.start_pending_canon_render)

        # UI widgets such as QComboBox can emit currentTextChanged while items are
        # inserted. During construction those callbacks must not read sibling
        # controls that do not exist yet.
        self.build_ui()
        self.install_shortcuts()
        self.update_snapshot_buttons()
        self.kelvin.setEnabled(False)
        self.applying_state=False

        # Do not synchronously decode/render while the top-level window itself is
        # still being constructed. Start the initial sample on the event loop.
        QTimer.singleShot(0, self.load_initial_sample)
        QTimer.singleShot(400, self.reset_history)
        QTimer.singleShot(50, self.update_canon_install_status)
        QTimer.singleShot(80, self.update_base_source_status)

    def start_worker(self, worker, pool, on_result=None, on_error=None):
        """Start a QRunnable while keeping its Python wrapper/signals alive.

        Release happens only AFTER the result/error callback has run on the UI
        side. This avoids deleting WorkerSignals while its queued result is
        still waiting in the event loop.
        """
        self._active_workers.add(worker)

        def deliver_result(result, w=worker):
            try:
                if on_result is not None:
                    on_result(result)
            finally:
                self._release_worker(w)

        def deliver_error(message, tb, w=worker):
            try:
                self.record_internal("ERROR: "+str(message)+"\n"+str(tb))
                if on_error is not None:
                    on_error(message, tb)
            finally:
                self._release_worker(w)

        worker.signals.result.connect(deliver_result)
        worker.signals.error.connect(deliver_error)
        pool.start(worker)

    def record_internal(self,message):
        self.recent_internal_logs.append(str(message))
        if len(self.recent_internal_logs)>200:self.recent_internal_logs=self.recent_internal_logs[-200:]

    def _release_worker(self, worker):
        self._active_workers.discard(worker)

    # ---------- UI ----------
    def build_ui(self):
        root=QWidget(); self.setCentralWidget(root); main=QVBoxLayout(root); main.setContentsMargins(0,0,0,0); main.setSpacing(0)
        top=QFrame(); top.setObjectName("TopBar"); top.setFixedHeight(58); tl=QHBoxLayout(top); tl.setContentsMargins(14,8,14,8); tl.setSpacing(7)
        app=QLabel("Canon Style Studio"); app.setObjectName("AppTitle"); tl.addWidget(app); ver=QLabel(f"PUBLIC ALPHA · {APP_VERSION}");ver.setObjectName("Muted");tl.addWidget(ver);tl.addSpacing(12)
        self.open_btn=QPushButton("Open");self.open_btn.clicked.connect(self.open_dialog);tl.addWidget(self.open_btn)
        self.save_btn=QPushButton("Save Project");self.save_btn.clicked.connect(self.save_project_action);tl.addWidget(self.save_btn)
        self.project_name=QLineEdit("Untitled");self.project_name.setMaximumWidth(250);self.project_name.setPlaceholderText("Project name");self.project_name.editingFinished.connect(self.mark_dirty);tl.addWidget(self.project_name);tl.addStretch()
        self.undo_btn=QToolButton(text="↶");self.undo_btn.setToolTip("Undo · Ctrl+Z");self.undo_btn.clicked.connect(self.undo);tl.addWidget(self.undo_btn)
        self.redo_btn=QToolButton(text="↷");self.redo_btn.setToolTip("Redo · Ctrl+Y");self.redo_btn.clicked.connect(self.redo);tl.addWidget(self.redo_btn)
        self.report_btn=QPushButton("Create Test Report");self.report_btn.clicked.connect(self.create_test_report);tl.addWidget(self.report_btn)
        self.about_btn=QToolButton(text="About / Alpha");self.about_btn.clicked.connect(self.show_about);tl.addWidget(self.about_btn)
        self.camera_btn=QPushButton("SEND TO CAMERA");self.camera_btn.setToolTip("Dynamic Canon camera-family workflow; EOS RP physically validated, other bodies experimental");self.camera_btn.clicked.connect(self.open_camera_install);tl.addWidget(self.camera_btn)
        self.export_btn=QPushButton("EXPORT PF3");self.export_btn.setObjectName("AccentButton");self.export_btn.clicked.connect(self.open_export);tl.addWidget(self.export_btn);main.addWidget(top)

        content=QSplitter(Qt.Orientation.Horizontal); content.setChildrenCollapsible(False); main.addWidget(content,1);self.content_splitter=content
        sidebar=QFrame();sidebar.setObjectName("SideBar");sidebar.setMinimumWidth(400);sidebar.setMaximumWidth(720);sidebar.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Expanding);self.sidebar=sidebar;sl=QVBoxLayout(sidebar);sl.setContentsMargins(8,8,8,8);sl.setSpacing(0)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.sidebar_scroll=scroll
        sw=QWidget();sw.setMinimumWidth(0);sw.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);self.sidebar_widget=sw;self.side_layout=QVBoxLayout(sw);self.side_layout.setContentsMargins(4,2,4,4);self.side_layout.setSpacing(2);scroll.setWidget(sw);sl.addWidget(scroll);content.addWidget(sidebar)
        self.build_raw_section();self.build_canon_section();self.build_creative_section();self.build_lut_section();self.side_layout.addStretch()

        center=QWidget();cl=QVBoxLayout(center);cl.setContentsMargins(0,0,0,0);cl.setSpacing(0);content.addWidget(center);content.setStretchFactor(0,0);content.setStretchFactor(1,1);content.setSizes([430,1250])
        viewbar=QFrame();vbl=QHBoxLayout(viewbar);vbl.setContentsMargins(10,7,10,7);vbl.setSpacing(6)
        self.compare_combo=QComboBox();self.compare_combo.addItems(["Side by side","Split","Original","Preview"]);self.compare_combo.currentTextChanged.connect(self.compare_mode_changed);vbl.addWidget(self.compare_combo)
        self.render_mode=QComboBox();self.render_mode.addItems(["Working Preview","Canon 33³ LUT Preview"]);self.render_mode.currentTextChanged.connect(lambda _x:self.commit_and_render());vbl.addWidget(self.render_mode)
        self.zoom_combo=QComboBox();self.zoom_combo.addItems(["Fit","25%","50%","100%","200%","400%"]);self.zoom_combo.currentTextChanged.connect(self.zoom_changed);vbl.addWidget(self.zoom_combo)
        vbl.addSpacing(8);self.clip_btn=QToolButton(text="△");self.clip_btn.setCheckable(True);self.clip_btn.setToolTip("Highlight / shadow clipping overlay");self.clip_btn.toggled.connect(self.viewer_clipping);vbl.addWidget(self.clip_btn)
        self.scope_btn=QToolButton(text="Scopes");self.scope_btn.setCheckable(True);self.scope_btn.toggled.connect(self.toggle_scopes);vbl.addWidget(self.scope_btn);vbl.addStretch();vbl.addWidget(QLabel("Snapshots"))
        self.snapshot_buttons={}
        for name in "ABC":
            b=SnapshotButton(name);b.saveRequested.connect(self.save_snapshot);b.loadRequested.connect(self.load_snapshot);b.clearRequested.connect(self.clear_snapshot);vbl.addWidget(b);self.snapshot_buttons[name]=b
        cl.addWidget(viewbar)
        self.viewer=CompareView();self.viewer.pixelInfo.connect(self.pixel_info);self.viewer.pixelClicked.connect(self.pixel_clicked);self.viewer.viewChanged.connect(self.view_state_changed);cl.addWidget(self.viewer,1)
        self.scope_frame=QFrame();sfl=QVBoxLayout(self.scope_frame);sfl.setContentsMargins(8,4,8,6);sr=QHBoxLayout();sr.addWidget(QLabel("Scope"));self.scope_combo=QComboBox();self.scope_combo.addItems(["Histogram","RGB Parade","Vectorscope"]);self.scope_combo.currentTextChanged.connect(lambda x:self.scope.setMode(x));sr.addWidget(self.scope_combo);sr.addStretch();sfl.addLayout(sr);self.scope=ScopeWidget();sfl.addWidget(self.scope);self.scope_frame.setVisible(False);cl.addWidget(self.scope_frame)
        self.filmstrip=ReferenceStrip();self.filmstrip.selected.connect(self.select_reference);cl.addWidget(self.filmstrip)
        bottom=QFrame();bottom.setObjectName("BottomBar");bl=QHBoxLayout(bottom);bl.setContentsMargins(10,5,10,5);self.status=QLabel("Ready");self.status.setObjectName("Muted");bl.addWidget(self.status);bl.addStretch();self.rgb_label=QLabel("RGB —");self.rgb_label.setObjectName("Muted");bl.addWidget(self.rgb_label);cl.addWidget(bottom)

    def build_raw_section(self):
        sec=CollapsibleSection("RAW · CANON DPP4LIB",expanded=True);self.side_layout.addWidget(sec)
        row=QHBoxLayout();row.addWidget(QLabel("RAW engine"));self.raw_engine_label=QLabel("Canon DPP4Lib · standalone");self.raw_engine_label.setObjectName("Badge");row.addWidget(self.raw_engine_label,1);self.raw_engine_test=QToolButton(text="Test");self.raw_engine_test.clicked.connect(self.test_dpp_backend);row.addWidget(self.raw_engine_test);self.locate_pse_btn=QToolButton(text="Locate PSE…");self.locate_pse_btn.clicked.connect(self.locate_pse_folder);row.addWidget(self.locate_pse_btn);sec.body_layout.addLayout(row)
        self.camera_label=QLabel("Camera: no file loaded");self.camera_label.setObjectName("Muted");self.camera_label.setWordWrap(True);sec.body_layout.addWidget(self.camera_label)
        self.exposure=ValueSlider("Exposure",-50,50,0,scale=0.1,suffix=" EV");sec.body_layout.addWidget(self.exposure)
        self.exposure.changed.connect(self.schedule_canon_render);self.exposure.committed.connect(self.commit_history)
        row=QHBoxLayout();row.addWidget(QLabel("White Balance"));self.wb_combo=QComboBox();self.wb_combo.addItems(["As Shot","Auto — Ambience","Auto — White","Daylight","Shade","Cloudy","Tungsten","White Fluorescent","Flash","Kelvin"]);self.wb_combo.currentTextChanged.connect(self.wb_changed);row.addWidget(self.wb_combo,1);sec.body_layout.addLayout(row)
        row=QHBoxLayout();row.addWidget(QLabel("Kelvin"));self.kelvin=QSpinBox();self.kelvin.setRange(2500,10000);self.kelvin.setSingleStep(100);self.kelvin.setValue(5200);self.kelvin.valueChanged.connect(self.schedule_canon_render);self.kelvin.editingFinished.connect(self.commit_history);row.addWidget(self.kelvin);sec.body_layout.addLayout(row)
        row=QHBoxLayout();row.addWidget(QLabel("RAW image/shot"));self.shot_index=QSpinBox();self.shot_index.setRange(0,999);self.shot_index.setValue(0);self.shot_index.setEnabled(False);self.shot_index.setToolTip("DPP4Lib opens the primary RAW image. Multi-shot selection remains available only through the LibRaw fallback.");row.addWidget(self.shot_index);sec.body_layout.addLayout(row)
        self.ab_shift=ValueSlider("WB Shift  B ↔ A",-9,9,0);self.gm_shift=ValueSlider("WB Shift  G ↔ M",-9,9,0);sec.body_layout.addWidget(self.ab_shift);sec.body_layout.addWidget(self.gm_shift)
        for s in (self.ab_shift,self.gm_shift):s.changed.connect(self.schedule_canon_render);s.changed.connect(self._update_recipe_wb_status);s.committed.connect(self.commit_history)
        row=QHBoxLayout();self.eyedrop=QPushButton("Eyedropper WB");self.eyedrop.setCheckable(True);self.eyedrop.toggled.connect(self.toggle_eyedropper);row.addWidget(self.eyedrop);clear=QPushButton("Clear custom WB");clear.clicked.connect(self.clear_custom_wb);row.addWidget(clear);sec.body_layout.addLayout(row)
        note=QLabel("Requires Canon Picture Style Editor to be installed; Digital Photo Professional is not required. CR3/CR2 preview uses PSE's local DPP4Lib without opening PSE. Exposure, fixed/Kelvin WB and both WB Shift axes are Canon-native. Eyedropper WB is a post-Canon experimental adjustment.");note.setObjectName("Muted");note.setWordWrap(True);sec.body_layout.addWidget(note)

    def build_canon_section(self):
        sec=CollapsibleSection("CANON STYLE",expanded=True);self.side_layout.addWidget(sec)
        row=QHBoxLayout();self.base_combo=QComboBox();self.base_combo.addItems(list(BASES.keys()));self.base_combo.currentTextChanged.connect(self.base_changed);row.addWidget(self.base_combo,1);pf=QPushButton("Open PF3…");pf.clicked.connect(self.open_pf3_dialog);row.addWidget(pf);bases=QToolButton(text="Bases…");bases.setToolTip("Locate a local folder containing validated Canon base PF3 templates");bases.clicked.connect(self.choose_base_pf3_folder);row.addWidget(bases);sec.body_layout.addLayout(row)
        self.base_source_label=QLabel("Export base: checking…");self.base_source_label.setObjectName("Muted");self.base_source_label.setWordWrap(True);sec.body_layout.addWidget(self.base_source_label)
        self.contrast=ValueSlider("Contrast",-4,4,0);self.saturation=ValueSlider("Saturation",-4,4,0);self.color_tone=ValueSlider("Color Tone",-4,4,0)
        for s in (self.contrast,self.saturation,self.color_tone):sec.body_layout.addWidget(s);s.changed.connect(self.schedule_canon_render);s.committed.connect(self.commit_history)
        native=QLabel("RAW preview: Contrast, Saturation and Color Tone are rendered by Canon DPP4Lib itself.");native.setObjectName("Muted");native.setWordWrap(True);sec.body_layout.addWidget(native)
        self.sharp_enable=QCheckBox("Override Sharpness · PF3 native / preview approximate");self.sharp_enable.toggled.connect(lambda _x:self.commit_and_render());sec.body_layout.addWidget(self.sharp_enable)
        self.sharp_strength=ValueSlider("Strength",0,7,0);self.fineness=ValueSlider("Fineness",1,5,2);self.threshold=ValueSlider("Threshold",1,5,4)
        for s in (self.sharp_strength,self.fineness,self.threshold):sec.body_layout.addWidget(s);s.changed.connect(lambda _v:self.schedule_render(True));s.committed.connect(self.commit_history)
        note=QLabel("PF3 export writes Canon-native Basic/Sharpness fields. Sharpness Preview: Approximate. Imported PF3 Preview: Approximate. These experimental previews do not block PF3 export.");note.setObjectName("Muted");note.setWordWrap(True);sec.body_layout.addWidget(note)

    def build_lut_section(self):
        sec=CollapsibleSection("LUT STACK",expanded=True);self.side_layout.addWidget(sec)
        self.lut_list=LutList();self.lut_list.setMinimumHeight(190);self.lut_list.setMaximumHeight(420);self.lut_list.orderChanged.connect(self.lut_order_changed);self.lut_list.reorderRequested.connect(self.reorder_lut);self.lut_list.filesDropped.connect(self.files_dropped);sec.body_layout.addWidget(self.lut_list)
        row=QHBoxLayout();add=QPushButton("+ LUT / Hald");add.clicked.connect(self.add_lut_dialog);row.addWidget(add,1);hald=QPushButton("Lightroom Hald…");hald.clicked.connect(self.hald_menu);row.addWidget(hald);sec.body_layout.addLayout(row)
        note=QLabel("Drag LUT cards to reorder. Drop .cube/Hald files here or anywhere in the app.");note.setObjectName("Muted");note.setWordWrap(True);sec.body_layout.addWidget(note)

    def build_creative_section(self):
        sec=CollapsibleSection("RECIPE · TONE CURVE · COLOR AXES",expanded=False);self.side_layout.addWidget(sec);self.creative_section=sec
        recipe=QLabel("Recipe-style · LUT-baked");recipe.setObjectName("Muted");sec.body_layout.addWidget(recipe)
        recipe_wb=QLabel("Fuji-style Recipe WB · baked before LUT stack");recipe_wb.setObjectName("Muted");sec.body_layout.addWidget(recipe_wb)
        self.recipe_wb_red=ValueSlider("WB Shift Red (R)",-9,9,self.recipe_wb_controls["red"])
        self.recipe_wb_blue=ValueSlider("WB Shift Blue (B)",-9,9,self.recipe_wb_controls["blue"])
        for slider in (self.recipe_wb_red,self.recipe_wb_blue):
            sec.body_layout.addWidget(slider);slider.changed.connect(self._recipe_wb_changed);slider.committed.connect(self.commit_history)
        self.recipe_wb_status=QLabel();self.recipe_wb_status.setObjectName("Muted");self.recipe_wb_status.setWordWrap(True);sec.body_layout.addWidget(self.recipe_wb_status)
        reset_wb=QPushButton("Reset Recipe WB");reset_wb.clicked.connect(self.reset_recipe_wb);sec.body_layout.addWidget(reset_wb)
        self.recipe_highlight=ValueSlider("Highlight",-2,4,self.creative_controls["recipe_highlight"])
        self.recipe_shadow=ValueSlider("Shadow",-2,4,self.creative_controls["recipe_shadow"])
        self.recipe_color=ValueSlider("Color",-4,4,self.creative_controls["recipe_color"])
        for slider in (self.recipe_highlight,self.recipe_shadow,self.recipe_color):
            sec.body_layout.addWidget(slider);slider.changed.connect(self._recipe_control_changed);slider.committed.connect(self.commit_history)
        self.tone_curve=ToneCurveWidget();self.tone_curve.setPoints(self.creative_controls["tone_curve"]);self.tone_curve.pointsChanged.connect(self._tone_curve_changed);self.tone_curve.committed.connect(self.commit_history);sec.body_layout.addWidget(self.tone_curve)
        row=QHBoxLayout();reset_curve=QPushButton("Reset Curve");reset_curve.clicked.connect(self.reset_tone_curve);row.addStretch();row.addWidget(reset_curve);sec.body_layout.addLayout(row)
        row=QHBoxLayout();row.addWidget(QLabel("Six Color-Axes"));self.axis_combo=QComboBox();self.axis_combo.addItems(list(AXIS_NAMES));row.addWidget(self.axis_combo,1);sec.body_layout.addLayout(row)
        self.axis_hue=ValueSlider("Hue",-30,30,0,suffix="°");self.axis_saturation=ValueSlider("Saturation",-50,50,0,suffix="%");self.axis_luminance=ValueSlider("Luminance",-50,50,0,suffix="%")
        for slider in (self.axis_hue,self.axis_saturation,self.axis_luminance):
            sec.body_layout.addWidget(slider);slider.changed.connect(self._axis_control_changed);slider.committed.connect(self.commit_history)
        self.axis_combo.currentTextChanged.connect(self._axis_selected)
        row=QHBoxLayout();row.addWidget(QLabel("Color Chrome-style"));self.color_chrome=QComboBox();self.color_chrome.addItems(["Off","Weak","Strong"]);row.addWidget(self.color_chrome,1);sec.body_layout.addLayout(row)
        row=QHBoxLayout();row.addWidget(QLabel("Blue Chrome-style"));self.color_chrome_blue=QComboBox();self.color_chrome_blue.addItems(["Off","Weak","Strong"]);row.addWidget(self.color_chrome_blue,1);sec.body_layout.addLayout(row)
        self.color_chrome.currentTextChanged.connect(self._chrome_changed);self.color_chrome_blue.currentTextChanged.connect(self._chrome_changed)
        reset_all=QPushButton("Reset Creative Color");reset_all.clicked.connect(self.reset_creative_controls);sec.body_layout.addWidget(reset_all)
        note=QLabel("Fuji-style Recipe WB is an APPROXIMATE R/B grid cast, LUT-baked before user LUTs and included in PF3 export. It is independent from Canon-native WB Shift; using both combines both effects. Other Recipe and Creative Color controls are baked after the LUT stack. Canon 33³ Preview shows the final combined 33³/12-bit transform.");note.setObjectName("Muted");note.setWordWrap(True);sec.body_layout.addWidget(note)
        self._axis_selected(self.axis_combo.currentText())
        self._update_recipe_wb_status()

    def _recipe_wb_changed(self,_value=None):
        if self.applying_state:return
        self.recipe_wb_controls=normalize_recipe_wb({"red":self.recipe_wb_red.value(),"blue":self.recipe_wb_blue.value()})
        self._update_recipe_wb_status()
        self.schedule_render(True)

    def _update_recipe_wb_status(self,_value=None):
        if not hasattr(self,"recipe_wb_status"):return
        controls=normalize_recipe_wb(getattr(self,"recipe_wb_controls",None))
        active=bool(controls["red"] or controls["blue"])
        canon_active=hasattr(self,"ab_shift") and bool(self.ab_shift.value() or self.gm_shift.value())
        if active and canon_active:
            self.recipe_wb_status.setText(f"R{controls['red']:+d} / B{controls['blue']:+d} · ⚠ Canon WB Shift is also active; both effects are combined.")
            self.recipe_wb_status.setStyleSheet("color:#FFB45C;")
        elif active:
            self.recipe_wb_status.setText(f"R{controls['red']:+d} / B{controls['blue']:+d} · LUT-baked / APPROXIMATE")
            self.recipe_wb_status.setStyleSheet("")
        else:
            self.recipe_wb_status.setText("R+0 / B+0 · neutral")
            self.recipe_wb_status.setStyleSheet("")

    def set_recipe_wb_controls(self,settings):
        self.recipe_wb_controls=normalize_recipe_wb(settings)
        for slider,key in ((self.recipe_wb_red,"red"),(self.recipe_wb_blue,"blue")):
            slider.blockSignals(True);slider.setValue(self.recipe_wb_controls[key]);slider.blockSignals(False)
        self._update_recipe_wb_status()

    def reset_recipe_wb(self):
        self.set_recipe_wb_controls(DEFAULT_RECIPE_WB);self.commit_and_render()

    def _recipe_control_changed(self,_value=None):
        if self.applying_state:return
        self.creative_controls["recipe_highlight"]=int(self.recipe_highlight.value())
        self.creative_controls["recipe_shadow"]=int(self.recipe_shadow.value())
        self.creative_controls["recipe_color"]=int(self.recipe_color.value())
        self.schedule_render(True)

    def _tone_curve_changed(self,points):
        if self.applying_state:return
        self.creative_controls["tone_curve"]=list(points);self.schedule_render(True)

    def reset_tone_curve(self):
        self.tone_curve.setPoints(IDENTITY_TONE_CURVE);self.creative_controls["tone_curve"]=list(IDENTITY_TONE_CURVE);self.commit_and_render()

    def _axis_selected(self,name):
        values=self.creative_controls["color_axes"].get(name,{"hue":0,"saturation":0,"luminance":0})
        for slider,key in ((self.axis_hue,"hue"),(self.axis_saturation,"saturation"),(self.axis_luminance,"luminance")):
            slider.blockSignals(True);slider.setValue(values.get(key,0));slider.blockSignals(False)

    def _axis_control_changed(self,_value=None):
        if self.applying_state:return
        name=self.axis_combo.currentText()
        self.creative_controls["color_axes"][name]={"hue":int(self.axis_hue.value()),"saturation":int(self.axis_saturation.value()),"luminance":int(self.axis_luminance.value())}
        self.schedule_render(True)

    def _chrome_changed(self,_value=None):
        if self.applying_state:return
        self.creative_controls["color_chrome"]=self.color_chrome.currentText();self.creative_controls["color_chrome_fx_blue"]=self.color_chrome_blue.currentText();self.commit_and_render()

    def set_creative_controls(self,settings):
        self.creative_controls=normalize_creative_controls(settings)
        for slider,key in ((self.recipe_highlight,"recipe_highlight"),(self.recipe_shadow,"recipe_shadow"),(self.recipe_color,"recipe_color")):
            slider.blockSignals(True);slider.setValue(self.creative_controls[key]);slider.blockSignals(False)
        self.tone_curve.setPoints(self.creative_controls["tone_curve"])
        self.color_chrome.blockSignals(True);self.color_chrome_blue.blockSignals(True)
        self.color_chrome.setCurrentText(self.creative_controls["color_chrome"]);self.color_chrome_blue.setCurrentText(self.creative_controls["color_chrome_fx_blue"])
        self.color_chrome.blockSignals(False);self.color_chrome_blue.blockSignals(False)
        self._axis_selected(self.axis_combo.currentText())

    def reset_creative_controls(self):
        self.set_creative_controls(DEFAULT_CREATIVE_CONTROLS);self.commit_and_render()

    def install_shortcuts(self):
        a=QAction(self);a.setShortcut(QKeySequence.StandardKey.Undo);a.triggered.connect(self.undo);self.addAction(a)
        r=QAction(self);r.setShortcut(QKeySequence.StandardKey.Redo);r.triggered.connect(self.redo);self.addAction(r)
        s=QAction(self);s.setShortcut(QKeySequence.StandardKey.Save);s.triggered.connect(self.save_project_action);self.addAction(s)
        o=QAction(self);o.setShortcut(QKeySequence.StandardKey.Open);o.triggered.connect(self.open_dialog);self.addAction(o)

    def update_canon_install_status(self):
        if self.canon_install:
            version=self.canon_install.pse_version or "version unknown"
            self.raw_engine_label.setText("Canon DPP4Lib · READY TO TEST")
            self.raw_engine_label.setToolTip(f"Picture Style Editor {version}\n{self.canon_install.pse_dir}")
        else:
            self.raw_engine_label.setText("PSE REQUIRED · LibRaw fallback")
            self.raw_engine_label.setToolTip("Canon Picture Style Editor is required for Canon RAW rendering")
            self.status.setText("Canon Picture Style Editor is required for Canon RAW rendering · use Locate PSE…")

    def _configure_canon_install(self,install,manual=True):
        try:self.dpp_client.close(force=True)
        except Exception:pass
        self.canon_install=install;self.runtime_profile=None
        if install:
            self.runtime_profile=ensure_runtime_input_profile(install)
            if manual:
                self.settings.data["manual_pse_path"]=str(install.pse_dir);self.settings.save()
        self.dpp_client=DppBackendClient(dpp_worker_program(),app_config_dir()/"dpp_cache",runtime_environment(install,self.runtime_profile))
        self.dpp_backend_state="not tested" if install else "pse missing"
        self.render_engine.clear();self.base_resolution=None;self.update_canon_install_status();self.update_base_source_status()

    def locate_pse_folder(self):
        start=self.canon_install.pse_dir if self.canon_install else Path(os.environ.get("ProgramFiles",r"C:\Program Files"))/"Canon"
        selected=QFileDialog.getExistingDirectory(self,"Locate Canon Picture Style Editor",str(start))
        if not selected:return
        install=discover_pse(selected)
        if not install:
            QMessageBox.warning(self,"Picture Style Editor not found","Select the Picture Style Editor folder containing PSEditor.exe and DPP4Lib\\DppCore.dll.")
            return
        try:
            self._configure_canon_install(install,manual=True);self.status.setText(f"Picture Style Editor found · {install.pse_version or 'version unknown'}");self.test_dpp_backend()
        except Exception as exc:
            QMessageBox.critical(self,"Picture Style Editor",str(exc))

    def show_about(self):
        QMessageBox.information(self,"Canon Style Studio Public Alpha",
            f"{PUBLIC_NAME}\n{APP_VERSION}\nBuild {BUILD_ID}\n\n"
            "Requires Canon Picture Style Editor to be installed.\n"
            "Digital Photo Professional is not required.\n\n"
            "Experimental:\n"
            "• Generated PF3 base fallback when no validated local template is selected\n"
            "• White Balance fidelity across untested cameras\n"
            "• Imported PF3 native preview (current preview is approximate)\n"
            "• Sharpness preview (approximate)\n"
            "• Tone Curve, Six Color-Axes and Chrome-style controls (LUT-baked)\n"
            "• Compatibility with untested Canon bodies\n\n"
            "Canon software and libraries are not distributed with Canon Style Studio.\n"
            "Send to Camera dynamically uses the connected Canon camera ID, descriptor and native carrier. EOS RP is physically validated; other bodies remain experimental until tested.\n"
            "External hash-validated support fixtures are required and are not distributed with this build.\n"
            "Canon Style Studio is independent experimental software and is not affiliated with or endorsed by Canon.")

    def test_report_payload(self):
        source=Path(self.current_source_path) if self.current_source_path else None
        native=tuple(int(x) for x in (self.source_native_size or (self.source_full.size if self.source_full else (0,0))))
        install=self.canon_install
        ready=self.dpp_client.ready_info or {}
        lut_metadata=[]
        for entry in self.luts:
            cube=entry.get("cube") or {};path=Path(cube.get("path")) if cube.get("path") else None
            lut_metadata.append({
                "name":path.name if path else cube.get("title"),"title":cube.get("title"),
                "type":cube.get("source"),"size":cube.get("size"),"bit_depth":cube.get("bit_depth"),
                "enabled":bool(entry.get("enabled",True)),"opacity":float(entry.get("opacity",1.0)),
                "sha256":sha256_file(path) if path and path.is_file() else None,**(entry.get("metadata") or {}),
            })
        fallback=bool(self.raw_info.get("fallback_reason") or "fallback" in str(self.raw_info.get("decoder","")).lower())
        camera_assets=discover_rp_assets(self.settings.data.get("camera_assets_folder"))
        report={
            "application":{"name":PUBLIC_NAME,"version":APP_VERSION,"build_id":BUILD_ID},
            "system":system_summary(),
            "camera":{"make":self.raw_info.get("camera_make"),"model":self.raw_info.get("camera_model") or "Unknown Canon model"},
            "source":{"extension":source.suffix.lower() if source else None,"pixel_dimensions":native,
                      "orientation":"portrait" if len(native)==2 and native[1]>native[0] else "landscape",
                      "file_name":source.name if source else None},
            "canon_runtime":{
                "pse_path":str(install.pse_dir) if install else None,"pse_version":install.pse_version if install else None,
                "dpp4lib_path":str(install.dpp4lib_dir) if install else ready.get("dpp4lib"),
                "dppcore_path":str(install.dppcore_dll) if install else ready.get("dppcore"),
                "dppcore_version":install.dppcore_version if install else ready.get("dppcore_version"),
                "dppcore_sha256":(sha256_file(install.dppcore_dll) if install else ready.get("dppcore_sha256")),"backend_status":self.dpp_backend_state,
                "decoder":self.raw_info.get("decoder"),"fallback_active":fallback,
                "fallback_reason":self.raw_info.get("fallback_reason"),
            },
            "camera_install":{
                "integrated":True,"method":"dynamic Canon camera family","physically_validated_bodies":["EOS RP"],
                "other_bodies":"experimental until physical validation","raw_compatibility_is_camera_compatibility":False,
                "support_assets_validated":bool(camera_assets),"support_fixture_hashes":dict(camera_assets.hashes) if camera_assets else None,
                "live_inputs":["0x01000001","0x01000210","0x01000203"],
                "patch_property":"0x01000203","property_0x00000115":"observation only / never patched",
            },
            "settings":{
                "picture_style":self.base_combo.currentText(),"white_balance":self.wb_combo.currentText(),
                "basePictureStyle":self.base_combo.currentText(),"baseTemplateSource":(self.base_resolution or {}).get("source"),"baseTemplateValidated":bool((self.base_resolution or {}).get("validated")),
                "kelvin":self.kelvin.value(),"exposure":self.exposure.value(),"contrast":self.contrast.value(),
                "saturation":self.saturation.value(),"color_tone":self.color_tone.value(),
                "wb_shift_ab":self.ab_shift.value(),"wb_shift_gm":self.gm_shift.value(),
                "sharpness":{"override":self.sharp_enable.isChecked(),"strength":self.sharp_strength.value(),
                             "fineness":self.fineness.value(),"threshold":self.threshold.value(),"preview":"Approximate"},
                "creative":normalize_creative_controls(self.creative_controls),
                "imported_pf3_preview":"Approximate" if self.base_combo.currentText()=="Imported PF3" else None,
                "canon33_enabled":self.render_mode.currentText().startswith("Canon"),"luts":lut_metadata,
            },
            "recent_errors":[line for line in self.recent_internal_logs if "ERROR" in line.upper()][-20:],
        }
        return report

    def create_test_report(self):
        dialog=QDialog(self);dialog.setWindowTitle("Create Test Report");dialog.resize(560,240)
        layout=QVBoxLayout(dialog)
        title=QLabel("Create a sanitized test report");title.setStyleSheet("font-size:16pt;font-weight:700;");layout.addWidget(title)
        text=QLabel("The report includes system, Canon backend, camera and current settings metadata plus sanitized logs. Personal paths and usernames are replaced. The source RAW is not included by default.");text.setWordWrap(True);layout.addWidget(text)
        include_raw=QCheckBox("Include source RAW in test report (OFF by default)");include_raw.setChecked(False);layout.addWidget(include_raw)
        warning=QLabel("If enabled, the complete original RAW will be copied into the ZIP and may contain personal metadata.");warning.setObjectName("Muted");warning.setWordWrap(True);layout.addWidget(warning)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        source=Path(self.current_source_path) if self.current_source_path and Path(self.current_source_path).suffix.lower() in CANON_STRONG_RAW_EXTENSIONS else None
        include=bool(include_raw.isChecked() and source)
        if include:
            answer=QMessageBox.warning(self,"Include source RAW","The original RAW will be included in the report ZIP. Continue?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:return
        default=reports_dir()/f"CanonStyleStudio_TestReport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        path,_=QFileDialog.getSaveFileName(self,"Save Test Report",str(default),"ZIP archive (*.zip)")
        if not path:return
        try:
            output=create_test_report_zip(Path(path),self.test_report_payload(),self.edit_state_dict(),self.recent_internal_logs,
                                          self.dpp_client._log_path(),logs_dir()/"startup.log",source,include)
            self.status.setText(f"Test report created · {output.name}");QMessageBox.information(self,"Test Report",f"Sanitized report created:\n{output}")
        except Exception as exc:
            self.record_internal("ERROR creating test report: "+str(exc));QMessageBox.critical(self,"Test Report",str(exc))

    def test_dpp_backend(self):
        if not self.canon_install:
            self.update_canon_install_status();QMessageBox.information(self,"Canon RAW rendering","Canon Picture Style Editor is required for Canon RAW rendering.\n\nDigital Photo Professional is not required.\n\nUse Locate PSE… to select the installation folder.");return
        self.raw_engine_label.setText("Testing Canon DPP4Lib…")
        w=FunctionWorker(self.dpp_client.probe)
        def done(info):
            self.dpp_backend_state="ready";self.raw_engine_label.setText("Canon DPP4Lib · READY");self.status.setText(f"Canon RAW engine ready · {Path(info.get('dpp4lib','')).name or 'DPP4Lib'}")
        def fail(msg,tb):
            self.dpp_backend_state="fallback";self.raw_engine_label.setText("DPP4Lib unavailable · LibRaw fallback");QMessageBox.warning(self,"Canon RAW engine",msg+"\n\nThe app will keep working with LibRaw fallback where available. Picture Style Editor can be located manually with Locate PSE…")
        self.start_worker(w,self.decode_pool,done,fail)

    def dpp_settings_dict(self):
        style=self.base_combo.currentText()
        if style=="Imported PF3":style="Neutral"
        return {
            "style":style,
            "wb":self.wb_combo.currentText(),
            "kelvin":self.kelvin.value(),
            "exposure":self.exposure.value(),
            "wb_ab_shift":float(self.ab_shift.value()),
            "wb_gm_shift":float(self.gm_shift.value()),
            "contrast":int(self.contrast.value()),
            "saturation":int(self.saturation.value()),
            "color_tone":int(self.color_tone.value()),
        }

    def render_raw_integrated(self,path,luts,controls,preview_mode,quality,dpp_settings,post_wb,base_name,base_path,dll_path,fallback_decode,shot_index,fallback_source=None,requested_size=None,native_size=None,detail_requested=False):
        source_size=tuple(int(x) for x in fallback_source.size) if fallback_source is not None else (3,2)
        # Fit mode uses an exact Canon-developed working frame. Landscape fixed
        # zoom can request complete sensor geometry. Portrait stays inside the
        # validated standalone DPP canvas because larger streams are corrupt even
        # though DPP reports success.
        if requested_size:
            width,height=int(requested_size[0]),int(requested_size[1])
        elif source_size[1] > source_size[0]:
            width,height=fit_size_within_box(source_size,*CANON_PORTRAIT_SAFE_BOX)
        else:
            width,height=fit_size_within_box(source_size,1620,1080)
        logical_size=tuple(int(x) for x in (native_size or source_size))
        failure_key=(file_fingerprint(Path(path)),int(width),int(height))
        try:
            if failure_key in self.dpp_failure_cache:
                raise RuntimeError(self.dpp_failure_cache[failure_key])
            canon_base,info=self.dpp_client.render(path,dpp_settings,width,height)
            if base_name=="Imported PF3":
                # Imported arbitrary PF3 cannot yet be injected into DPP standalone; use the
                # existing table preview on top of a neutral Canon render, before the LUT stack.
                base=self.render_engine.load_base(dll_path,base_path)
                canon_base=canon_base.filter(base["lut"])
                info["warning"]="Imported PF3 preview uses table approximation on top of Canon Neutral."
            canon_post_wb={"custom_wb_mult":post_wb.get("custom_wb_mult")}
            inp,out=self.render_engine.render_from_canon_base(canon_base,luts,controls,preview_mode,canon_post_wb,max_side=max(width,height))
            is_native=tuple(inp.size)==logical_size
            portrait_safe=bool(detail_requested and logical_size[1]>logical_size[0] and not is_native)
            resolution="native" if is_native else ("portrait-safe" if portrait_safe else "working")
            return inp,out,{"decoder":"Canon DPP4Lib standalone","dpp4lib":info.get("dpp4lib"),"render_size":inp.size,"native_size":logical_size,"resolution":resolution,"_canon_base":canon_base,"_canon_settings":dict(dpp_settings),"_canon_source":str(Path(path).resolve()),"_canon_native":is_native,"_canon_resolution":resolution,**({"warning":info["warning"]} if info.get("warning") else {})}
        except Exception as dpp_error:
            if self.closing or "Canon render cancelled" in str(dpp_error):raise
            # Robust fallback: the integrated app must remain usable even if Canon changes
            # DPP4Lib ABI in a future install.
            if "DppOutputImageToStream failed: 0x00000060" in str(dpp_error):
                self.dpp_failure_cache[failure_key]=str(dpp_error)
            if fallback_source is not None:
                im=fallback_source.copy();rawinfo={"decoder":"cached RAW fallback"};israw=True;embedded=False
            else:
                im,rawinfo,israw,embedded=load_reference_image(path,fallback_decode,shot_index)
            wb=dpp_settings.get("wb","As Shot");kelvin=None
            fallback_map={"Daylight":5200,"Shade":7000,"Cloudy":6000,"Tungsten":3200,"White Fluorescent":4000,"Flash":6000}
            if wb=="Kelvin":kelvin=dpp_settings.get("kelvin",5200)
            elif wb in fallback_map:kelvin=fallback_map[wb]
            rawp={"exposure":dpp_settings.get("exposure",0.0),"kelvin":kelvin,"ab_shift":post_wb.get("ab_shift",0),"gm_shift":post_wb.get("gm_shift",0),"custom_wb_mult":post_wb.get("custom_wb_mult")}
            target_max=max(width,height) if requested_size else (1050 if quality=="interactive" else 1800)
            inp,out=self.render_engine.render(im,dll_path,base_path,luts,controls,preview_mode,rawp,target_max)
            rawinfo=dict(rawinfo);rawinfo["fallback_reason"]=str(dpp_error);rawinfo["decoder"]="LibRaw/embedded fallback"
            rawinfo["native_size"]=logical_size;rawinfo["resolution"]="fallback"
            return inp,out,rawinfo

    def render_raw_fast_preview(self,source,luts,controls,preview_mode,raw_preview,base_path,dll_path,desired_settings,source_path):
        """Compose only post-Canon edits from the last exact Canon-developed frame."""
        current=str(Path(source_path).resolve()) if source_path else None
        if self.last_canon_base is not None and self.last_canon_source==current:
            im=self.last_canon_base
            # Exposure, WB, WB Shift and Canon basic controls are deliberately not
            # approximated here. Those controls now use a debounced real DPP render,
            # eliminating the large colour/tone jump when the final frame arrives.
            post={"custom_wb_mult":raw_preview.get("custom_wb_mult")}
            sharp={"sharpness_override":controls.get("sharpness_override",False),"sharp_strength":controls.get("sharp_strength",0),"recipe_wb":controls.get("recipe_wb"),"creative":controls.get("creative")}
            inp,out=self.render_engine.render_from_canon_base(im,luts,sharp,preview_mode,post,max_side=max(im.size))
            resolution=self.last_canon_resolution or ("native" if self.last_canon_native else "working")
            return inp,out,{"decoder":"Cached Canon composition","render_size":inp.size,"native_size":self.source_native_size or inp.size,"resolution":resolution}
        raise RuntimeError("Canon base is not ready for post-processing preview.")

    def dll_path(self,optional=False):
        saved=self.settings.data.get("dll_path")
        if saved and Path(saved).exists():return Path(saved)
        p=self.canon_install.edscfparse_dll if self.canon_install else find_dll()
        if p:return Path(p)
        if optional:return None
        raise RuntimeError("Canon Picture Style Editor is required for PF3 read/export. Digital Photo Professional is not required.")
    def choose_dll(self):
        start=self.settings.get_folder("last_dll_folder",Path(os.environ.get("ProgramFiles",r"C:\Program Files")))
        p,_=QFileDialog.getOpenFileName(self,"Select Canon EdsCFParse.dll",str(start),"Canon EdsCFParse (EdsCFParse.dll);;DLL (*.dll)")
        if p:
            self.settings.data["dll_path"]=str(Path(p));self.settings.remember_file("last_dll_folder",p);self.settings.save();self.render_engine.clear();self.status.setText(f"Canon DLL: {Path(p).name}");self.schedule_render(False)

    def choose_base_pf3_folder(self):
        start=self.settings.get_folder("base_pf3_folder",HERE)
        selected=QFileDialog.getExistingDirectory(self,"Locate validated Canon base PF3 folder",str(start))
        if not selected:return
        dll=self.dll_path(optional=True)
        if not dll:
            QMessageBox.warning(self,"Canon base PF3","Picture Style Editor is required to validate Canon PF3 bases.");return
        found=[]
        for style in BASES:
            result=resolve_validated_base_pf3(dll,style,[selected])
            if result and result.get("validated"):found.append(style)
        if not found:
            QMessageBox.warning(self,"Canon base PF3","No hash-validated Canon base templates were found in that folder or its SOURCE/bases subfolder.");return
        self.settings.data["base_pf3_folder"]=str(Path(selected).resolve());self.settings.save();self.render_engine.clear();self.base_resolution=None
        self.update_base_source_status();self.status.setText("Validated local bases: "+", ".join(found));self.schedule_render(False)

    def resolve_current_base(self,optional=False):
        if self.base_combo.currentText()=="Imported PF3" and self.custom_base_path:
            path=Path(self.custom_base_path);return {"path":path,"style":"Imported PF3","source":"imported PF3","validated":True,"sha256":sha256_file(path) if path.is_file() else None}
        dll=self.dll_path(optional=optional)
        if dll is None:return None
        style=self.base_combo.currentText()
        search=[self.settings.data.get("base_pf3_folder"),HERE/"bases"]
        portable_assets=discover_rp_assets(self.settings.data.get("camera_assets_folder"))
        if portable_assets:
            search.insert(0,portable_assets.root)
        result=resolve_validated_base_pf3(dll,style,search)
        if result:return result
        try:
            path=ensure_runtime_base_pf3(dll,style)
            return {"path":path,"style":style,"source":"runtime-generated experimental base","validated":False,"sha256":sha256_file(path)}
        except Exception:
            if optional:return None
            raise

    def update_base_source_status(self):
        try:self.base_resolution=self.resolve_current_base(optional=True)
        except Exception:self.base_resolution=None
        if not hasattr(self,"base_source_label"):return
        if not self.base_resolution:self.base_source_label.setText("Export base: unavailable · install/locate PSE")
        elif self.base_resolution.get("validated"):
            self.base_source_label.setText(f"Export base: {self.base_resolution['style']} · validated local template")
        else:self.base_source_label.setText(f"Export base: {self.base_resolution['style']} · EXPERIMENTAL generated template · use Bases… for exact validated export")

    def current_base_path(self,optional=False):
        self.base_resolution=self.resolve_current_base(optional=optional)
        return Path(self.base_resolution["path"]) if self.base_resolution else None
    def controls_dict(self):
        return {"contrast":int(self.contrast.value()),"saturation":int(self.saturation.value()),"color_tone":int(self.color_tone.value()),"sharpness_override":self.sharp_enable.isChecked(),"sharp_strength":int(self.sharp_strength.value()),"fineness":int(self.fineness.value()),"threshold":int(self.threshold.value()),"recipe_wb":normalize_recipe_wb(self.recipe_wb_controls),"creative":normalize_creative_controls(self.creative_controls)}
    def edit_state_dict(self):
        base=self.current_base_path(optional=True)
        base_style=self.base_combo.currentText()
        return {"base_name":base_style,"basePictureStyle":base_style,"baseTemplateSource":(self.base_resolution or {}).get("source"),"baseTemplateValidated":bool((self.base_resolution or {}).get("validated")),"base_path":str(base or ""),"custom_pf3":str(self.custom_base_path or ""),**self.controls_dict(),"raw_wb_mode":self.wb_combo.currentText(),"raw_kelvin":self.kelvin.value(),"raw_exposure":self.exposure.value(),"raw_shot_index":self.shot_index.value(),"wb_ab_shift":int(self.ab_shift.value()),"wb_gm_shift":int(self.gm_shift.value()),"custom_wb_mult":self.custom_wb_mult,"preview_quality_mode":"canon33" if self.render_mode.currentText().startswith("Canon") else "working","luts":[{"id":e["id"],"path":str(e["cube"]["path"]),"enabled":bool(e.get("enabled",True)),"opacity":float(e.get("opacity",1.0)),"metadata":e.get("metadata") or {}} for e in self.luts]}
    def project_document(self):
        zoom=0.0 if self.viewer.zoom_mode=="Fit" else float(self.viewer.zoom_mode.rstrip("%"))/100.0
        return ProjectDocument(name=self.project_name.text().strip().rstrip("*") or "Untitled",edit=self.edit_state_dict(),references=[str(x) for x in self.references],current_reference=max(0,self.current_reference),compare_mode=self.compare_combo.currentText(),zoom=zoom,pan_x=self.viewer.center[0],pan_y=self.viewer.center[1],split=self.viewer.split,snapshots=self.snapshots.copy())
    def reset_history(self):self.history.reset(self.edit_state_dict());self.update_undo_buttons()
    def commit_history(self,fast_first=False):
        if self.applying_state:return
        self.history.push(self.edit_state_dict());self.mark_dirty();self.update_undo_buttons()
        if fast_first:self.schedule_render(True)
        # Allow the exact working render to settle, then populate native detail
        # when a fixed zoom level needs it.
        self.full_render_timer.start(300)
    def commit_and_render(self):self.commit_history(True)
    def update_undo_buttons(self):self.undo_btn.setEnabled(self.history.can_undo());self.redo_btn.setEnabled(self.history.can_redo())
    def undo(self):
        s=self.history.undo()
        if s:self.apply_edit_state(s,load_luts=True);self.update_undo_buttons();self.mark_dirty()
    def redo(self):
        s=self.history.redo()
        if s:self.apply_edit_state(s,load_luts=True);self.update_undo_buttons();self.mark_dirty()
    def mark_dirty(self):
        self.dirty=True;name=self.project_name.text().rstrip('*');self.project_name.setText(name+'*')
    def mark_clean(self):self.dirty=False;self.project_name.setText(self.project_name.text().rstrip('*'))

    def apply_edit_state(self,s,load_luts=True):
        self.applying_state=True
        try:
            custom=s.get("custom_pf3") or "";self.custom_base_path=Path(custom) if custom else None
            vals=list(BASES.keys())+(["Imported PF3"] if self.custom_base_path else [])
            self.base_combo.blockSignals(True);self.base_combo.clear();self.base_combo.addItems(vals);self.base_combo.setCurrentText(s.get("basePictureStyle") or s.get("base_name","Neutral"));self.base_combo.blockSignals(False)
            self.contrast.setValue(s.get("contrast",0));self.saturation.setValue(s.get("saturation",0));self.color_tone.setValue(s.get("color_tone",0));self.sharp_enable.setChecked(s.get("sharpness_override",False));self.sharp_strength.setValue(s.get("sharp_strength",0));self.fineness.setValue(s.get("fineness",2));self.threshold.setValue(s.get("threshold",4));self.set_recipe_wb_controls(s.get("recipe_wb"));self.set_creative_controls(s.get("creative"))
            wb=s.get("raw_wb_mode","As Shot");wb="Auto — Ambience" if wb=="Auto Calculated" else wb;self.wb_combo.setCurrentText(wb);self.kelvin.setEnabled(wb=="Kelvin");self.kelvin.setValue(s.get("raw_kelvin",5200));self.shot_index.setValue(s.get("raw_shot_index",0));self.exposure.setValue(s.get("raw_exposure",0));self.ab_shift.setValue(s.get("wb_ab_shift",0));self.gm_shift.setValue(s.get("wb_gm_shift",0));self.custom_wb_mult=s.get("custom_wb_mult")
            self.render_mode.setCurrentText("Canon 33³" if s.get("preview_quality_mode")=="canon33" else "Working Preview")
            if load_luts:
                loaded=[]
                for ld in s.get("luts",[]):
                    p=Path(ld.get("path",""))
                    if not p.exists():continue
                    try:
                        cube=parse_lut_file(p);metadata=load_lut_metadata(p,cube);metadata.update(ld.get("metadata") or {});loaded.append({"id":ld.get("id") or uuid.uuid4().hex,"cube":cube,"metadata":metadata,"enabled":bool(ld.get("enabled",True)),"opacity":float(ld.get("opacity",1.0))})
                    except Exception:pass
                self.luts=loaded;self.refresh_lut_list()
        finally:self.applying_state=False
        self.base_resolution=None;self.update_base_source_status()
        self.schedule_render(False)

    # ---------- File/project ----------
    def open_dialog(self):
        start=self.settings.get_folder("last_image_folder",HERE)
        filt="Supported (*.canonstyleproject *.pf3 *.cr3 *.cr2 *.crw *.cip *.crn *.jpg *.jpeg *.png *.tif *.tiff *.webp *.cube);;All files (*.*)"
        p,_=QFileDialog.getOpenFileName(self,"Open",str(start),filt)
        if p:self.open_path(Path(p))
    def open_path(self,p):
        ext=p.suffix.lower()
        if ext==".canonstyleproject":self.open_project(p)
        elif ext==".pf3":self.open_pf3(p)
        elif ext==".cube":self.add_lut_paths([p])
        elif ext in HALD_IMAGE_EXTENSIONS and self._looks_like_hald(p):self.add_lut_paths([p])
        else:self.add_references([p],select_last=True)
    def _looks_like_hald(self,p):
        try:parse_lut_file(p);return True
        except Exception:return False
    def save_project_action(self):
        if self.project_path:
            suggested=Path(self.project_path)
        else:
            folder=self.settings.get_folder("last_project_folder",HERE)
            suggested=folder/((self.project_name.text().rstrip('*') or "Untitled")+".canonstyleproject")
        p,_=QFileDialog.getSaveFileName(self,"Save Portable Canon Style Project",str(suggested),"Canon Style Project (*.canonstyleproject)")
        if p:
            target=Path(p)
            if target.suffix.lower()!=".canonstyleproject":target=target.with_suffix(".canonstyleproject")
            return self.save_project_to(target)
        return False
    def save_project_to(self,p):
        try:
            save_project(p,self.project_document())
        except Exception as e:
            QMessageBox.critical(self,"Project save error",str(e));return False
        self.project_path=Path(p);self.settings.remember_file("last_project_folder",p);self.mark_clean();self.status.setText(f"Portable project saved · settings + LUTs · {Path(p).name}");return True
    def open_project(self,p):
        try:
            doc=load_project(p);self.project_path=Path(p);self.settings.remember_file("last_project_folder",p)
            self.full_render_timer.stop();self.canon_render_timer.stop();self.render_generation+=1;self.load_generation+=1
            self.render_pending=None;self.preview_pending=None;self.dpp_client.cancel_active_render()
            self.references=[];self.current_reference=-1;self.current_source_path=None;self.source_full=None;self.source_native_size=None;self.source_is_raw=False;self.source_embedded=False;self.raw_info={}
            self.last_canon_base=None;self.last_canon_settings=None;self.last_canon_source=None;self.last_canon_native=False;self.last_canon_resolution=None
            self.viewer.clearImages()
            self.project_name.setText(doc.name);self.snapshots=doc.snapshots or {"A":None,"B":None,"C":None};self.apply_edit_state(doc.edit,True);self.references=[Path(x) for x in doc.references if Path(x).exists()];self.filmstrip.set_references(self.references,min(doc.current_reference,max(0,len(self.references)-1)));self.compare_combo.setCurrentText(doc.compare_mode)
            zoom_mode="Fit"
            if int(getattr(doc,"version",1))>=2 and float(doc.zoom)>0:
                candidate=f"{int(round(float(doc.zoom)*100))}%"
                if candidate in {"25%","50%","100%","200%","400%"}:zoom_mode=candidate
            self.zoom_combo.blockSignals(True);self.zoom_combo.setCurrentText(zoom_mode);self.zoom_combo.blockSignals(False);self.viewer.setViewState(doc.pan_x,doc.pan_y,doc.split,zoom_mode);self.update_snapshot_buttons();self.mark_clean();self.reset_history()
            if self.references:self.select_reference(min(doc.current_reference,len(self.references)-1))
            elif getattr(doc,"referenceHints",None):
                names=", ".join(str(item.get("name") or "reference") for item in doc.referenceHints[:3] if isinstance(item,dict))
                suffix="…" if len(doc.referenceHints)>3 else ""
                self.status.setText(f"Portable project loaded · settings and LUTs restored · add reference photo ({names}{suffix})")
            else:self.status.setText(f"Project loaded · {Path(p).name}")
            if getattr(doc,"portableWarnings",None):
                QMessageBox.warning(self,"Portable project notice","\n".join(str(item) for item in doc.portableWarnings))
        except Exception as e:QMessageBox.critical(self,"Project error",str(e))
    def open_pf3_dialog(self):
        start=self.settings.get_folder("last_pf3_folder",HERE);p,_=QFileDialog.getOpenFileName(self,"Open Canon PF3",str(start),"Canon Picture Style (*.pf3)")
        if p:self.open_pf3(Path(p))
    def open_pf3(self,p):
        try:
            info=inspect_pf3(self.dll_path(),p);self.settings.remember_file("last_pf3_folder",p);self.custom_base_path=Path(p);vals=list(BASES.keys())+["Imported PF3"];self.base_combo.blockSignals(True);self.base_combo.clear();self.base_combo.addItems(vals);self.base_combo.setCurrentText("Imported PF3");self.base_combo.blockSignals(False);b=info["basic"];self.contrast.setValue(max(-4,min(4,b["contrast"])));self.saturation.setValue(max(-4,min(4,b["saturation"])));self.color_tone.setValue(max(-4,min(4,b["color_tone"])));self.sharp_strength.setValue(max(0,min(7,b["sharp_strength"])));self.fineness.setValue(max(1,min(5,b["fineness"] or 1)));self.threshold.setValue(max(1,min(5,b["threshold"] or 1)));self.render_engine.clear();self.project_name.setText(info["title"]);self.commit_history(False);self.schedule_canon_render(immediate=True);self.status.setText(f"PF3 opened · {p.name}")
        except Exception as e:QMessageBox.critical(self,"PF3 error",str(e))

    # ---------- LUTs ----------
    def add_lut_dialog(self):
        start=self.settings.get_folder("last_lut_folder",HERE/"example_luts");paths,_=QFileDialog.getOpenFileNames(self,"Add LUT / Hald",str(start),"LUT / Hald (*.cube *.png *.jpg *.jpeg *.tif *.tiff *.webp);;All files (*.*)")
        if paths:self.add_lut_paths([Path(p) for p in paths])
    def add_lut_paths(self,paths):
        added=0;errors=[];preferred=[]
        for p in paths:
            try:
                cube=parse_lut_file(p);metadata=load_lut_metadata(p,cube);self.luts.append({"id":uuid.uuid4().hex,"cube":cube,"metadata":metadata,"enabled":True,"opacity":1.0});self.settings.remember_file("last_lut_folder",p);added+=1
                if metadata.get("preferredBaseStyle") and metadata["preferredBaseStyle"]!=self.base_combo.currentText():preferred.append((Path(p).name,metadata["preferredBaseStyle"]))
                if cube.get("source")=="hald" and cube.get("color_space") not in ("Unspecified", "sRGB built-in") and "srgb" not in str(cube.get("color_space","")).lower(): errors.append(f"{Path(p).name}: Hald ICC is {cube.get('color_space')}. For exact current workflow, export the Hald as sRGB.")
                if cube.get("lossy"): errors.append(f"{Path(p).name}: JPEG Hald is lossy; TIFF/PNG is recommended.")
            except Exception as e:errors.append(f"{Path(p).name}: {e}")
        if added:self.refresh_lut_list();self.commit_history(True);self.status.setText(f"Added {added} LUT"+("s" if added!=1 else ""))
        if preferred:
            name,wanted=preferred[0];current=self.base_combo.currentText()
            answer=QMessageBox.question(self,"Preferred Canon base",f"{name} was calibrated for Canon {wanted}.\n\nCurrent base: {current}.\n\nSwitch to {wanted}?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.Yes)
            if answer==QMessageBox.StandardButton.Yes:self.base_combo.setCurrentText(wanted)
        if errors:QMessageBox.warning(self,"LUT import","\n\n".join(errors))
    def refresh_lut_list(self):
        self.lut_list.blockSignals(True);self.lut_list.clear()
        for e in self.luts:
            item=QListWidgetItem();card=LutCard(e);item.setSizeHint(QSize(100,100));self.lut_list.addItem(item);self.lut_list.setItemWidget(item,card);card.changed.connect(lambda:self.schedule_render(True));card.committed.connect(self.commit_history);card.removeRequested.connect(self.remove_lut_id)
        self.lut_list.blockSignals(False)
    def remove_lut_id(self,eid):self.luts=[e for e in self.luts if e["id"]!=eid];self.refresh_lut_list();self.commit_history(True)
    def reorder_lut(self,eid,target):
        old=next((i for i,e in enumerate(self.luts) if e["id"]==eid),None)
        if old is None:return
        entry=self.luts.pop(old)
        if old < target: target-=1
        target=max(0,min(len(self.luts),target));self.luts.insert(target,entry);self.refresh_lut_list();self.commit_history(True);self.status.setText(f"LUT moved to position {target+1}")

    def lut_order_changed(self):
        ordered=[]
        for i in range(self.lut_list.count()):
            card=self.lut_list.itemWidget(self.lut_list.item(i))
            if card:ordered.append(card.entry)
        if len(ordered)==len(self.luts):self.luts=ordered;self.commit_history(True)
    def hald_menu(self):
        m=QMenu(self);save=m.addAction("Save 16-bit TIFF template…");imp=m.addAction("Import edited Hald…");folder=m.addAction("Open template folder");a=m.exec(self.cursor().pos())
        if a==save:
            start=self.settings.get_folder("last_lut_folder",HERE);p,_=QFileDialog.getSaveFileName(self,"Save Lightroom Hald Template",str(start/"Lightroom_Hald_512_64cube_16bit.tif"),"TIFF (*.tif *.tiff)")
            if p:shutil.copy2(HALD_TEMPLATE,p);self.settings.remember_file("last_lut_folder",p)
        elif a==imp:self.add_lut_dialog()
        elif a==folder:
            try:os.startfile(str(HALD_TEMPLATE.parent))
            except Exception:pass

    # ---------- References / RAW ----------
    def load_initial_sample(self):
        p=HERE/"samples"/"color_reference.png"
        if p.exists():self.references=[p];self.filmstrip.set_references(self.references,0);self.select_reference(0)
    def add_references(self,paths,select_last=False):
        good=[]
        for p in paths:
            p=Path(p)
            if p.exists():self.references.append(p);good.append(p);self.settings.remember_file("last_image_folder",p)
        self.filmstrip.set_references(self.references,len(self.references)-1 if select_last else max(0,self.current_reference))
        if good:self.select_reference(len(self.references)-1 if select_last else max(0,self.current_reference))
    def select_reference(self,index):
        if not (0<=index<len(self.references)):return
        self.full_render_timer.stop();self.canon_render_timer.stop();self.render_generation+=1;self.render_pending=None;self.preview_pending=None
        self.dpp_client.cancel_active_render();self.viewer.clearEyedropperSample()
        self.last_canon_base=None;self.last_canon_settings=None;self.last_canon_source=None;self.last_canon_native=False;self.last_canon_resolution=None
        self.current_reference=index;self.filmstrip.set_current(index);p=self.references[index];self.current_source_path=p
        ext=p.suffix.lower();self.source_is_raw=ext in CANON_STRONG_RAW_EXTENSIONS;self.source_embedded=False;self.source_native_size=None
        self.load_generation+=1;gen=self.load_generation;self.viewer.setRendering(True)
        key=(file_fingerprint(p),"image",0)
        if self.source_is_raw:
            # Even though the final RAW render comes from Canon DPP4Lib, we still need an
            # oriented source preview/thumbnail first. Its dimensions tell us whether the
            # file is portrait or landscape, so we can request the correct fitted DPP size
            # instead of a forced 1620x1080 landscape canvas.
            self.source_full=Image.new("RGB",(2,2),(24,24,24));self.raw_info={"decoder":"Canon DPP4Lib pending"};self.status.setText(f"Preparing Canon RAW {p.name}…")
            if key in self.reference_cache:
                result=self.reference_cache.pop(key);self.reference_cache[key]=result
                self.accept_decoded_reference(index,result);return
            w=FunctionWorker(load_reference_image,p,"As Shot",0)
            def done(result):
                if gen!=self.load_generation:return
                self.reference_cache[key]=result
                while len(self.reference_cache)>6:self.reference_cache.popitem(last=False)
                self.accept_decoded_reference(index,result)
            self.start_worker(w,self.decode_pool,done,lambda m,t:self.load_error(gen,m,t));return
        self.status.setText(f"Decoding {p.name}…")
        if key in self.reference_cache:
            result=self.reference_cache.pop(key);self.reference_cache[key]=result
            self.accept_decoded_reference(index,result);return
        w=FunctionWorker(load_reference_image,p,"As Shot",0)
        def done(result):
            if gen!=self.load_generation:return
            self.reference_cache[key]=result
            while len(self.reference_cache)>6:self.reference_cache.popitem(last=False)
            self.accept_decoded_reference(index,result)
        self.start_worker(w,self.decode_pool,done,lambda m,t:self.load_error(gen,m,t))

    def accept_decoded_reference(self,index,result):
        im,info,is_raw,embedded=result
        self.source_full=im;self.raw_info=info;self.source_is_raw=is_raw;self.source_embedded=embedded
        self.source_native_size=oriented_native_size(im.size,info) if is_raw else im.size
        make=str(info.get("camera_make") or "").strip();model=str(info.get("camera_model") or "").strip()
        if is_raw:
            camera=" ".join(part for part in (make,model) if part) or "Unknown Canon model"
            self.camera_label.setText(f"Camera: {camera} · accepted for experimental rendering")
        else:self.camera_label.setText(f"Image: {Path(self.current_source_path).suffix.upper().lstrip('.')} · {self.source_native_size[0]}×{self.source_native_size[1]}")
        self.filmstrip.set_thumbnail(index,im);self.schedule_render(False)

    def raw_shot_changed(self):
        if self.applying_state:return
        self.commit_history()

    def load_error(self,gen,msg,tb):
        if gen!=self.load_generation:return
        self.viewer.setRendering(False);self.status.setText("Load error");QMessageBox.critical(self,"Image / RAW error",msg+"\n\n"+tb)
    def wb_changed(self,_mode):
        if self.applying_state:return
        self.kelvin.setEnabled(self.wb_combo.currentText()=="Kelvin")
        self.commit_history(False);self.schedule_canon_render(immediate=True)

    def base_changed(self,_x):
        if self.applying_state:return
        if self.base_combo.currentText()!="Imported PF3":self.custom_base_path=None
        self.base_resolution=None;self.update_base_source_status();self.commit_history(False);self.schedule_canon_render(immediate=True)

    # ---------- Render ----------
    def raw_preview_dict(self):
        # Used only by LibRaw/non-Canon fallback. DPP4Lib receives these controls natively.
        mode=self.wb_combo.currentText();kelvin=None
        mapping={"Daylight":5200,"Shade":7000,"Cloudy":6000,"Tungsten":3200,"White Fluorescent":4000,"Flash":6000}
        if self.source_is_raw and not self.source_embedded:
            if mode=="Kelvin":kelvin=self.kelvin.value()
            elif mode in mapping:kelvin=mapping[mode]
        return {"exposure":self.exposure.value(),"kelvin":kelvin,"ab_shift":self.ab_shift.value(),"gm_shift":self.gm_shift.value(),"custom_wb_mult":self.custom_wb_mult}

    def schedule_render(self,interactive=False):
        if self.closing or self.applying_state or self.source_full is None:return
        self.render_generation+=1;gen=self.render_generation
        if interactive:
            # Interactive here means an exact post-Canon composition (LUT opacity,
            # custom eyedropper or approximate sharpness), never an approximation
            # of a native Canon control.
            if self.preview_running:self.preview_pending=gen;return
            self.start_fast_render(gen);return
        if self.render_running:self.render_pending=("full",gen);return
        self.start_render("full",gen)

    def schedule_canon_render(self,_value=None,immediate=False):
        """Debounce a real DPP4Lib working render for Canon-native controls."""
        if self.closing or self.applying_state or self.source_full is None:return
        if not (self.source_is_raw and self.current_source_path):
            self.schedule_render(True);return
        self.render_generation+=1
        # Drop any obsolete queued render before terminating the isolated active
        # worker. The timer below will enqueue only the newest generation.
        self.render_pending=None
        if self.render_running:self.dpp_client.cancel_active_render()
        self.viewer.setRendering(True)
        self.canon_render_timer.start(0 if immediate else 70)

    def start_pending_canon_render(self):
        if self.closing or self.source_full is None:return
        gen=self.render_generation
        if self.render_running:
            self.render_pending=("interactive",gen);return
        self.start_render("interactive",gen)

    def start_final_render(self):
        """Queue final/native detail without invalidating the exact working frame."""
        if self.closing or self.applying_state or self.source_full is None:return
        gen=self.render_generation
        if self.render_running:
            self.render_pending=("full",gen);return
        self.start_render("full",gen)

    def start_fast_render(self,gen):
        if self.closing or self.source_full is None:return
        dll=self.dll_path(optional=True);base=self.current_base_path(optional=True)
        self.preview_running=True;self.preview_pending=None
        luts=list(self.luts);controls=self.controls_dict();mode="canon33" if self.render_mode.currentText().startswith("Canon") else "working"
        source=self.source_full;rawp=self.raw_preview_dict()
        if self.source_is_raw and self.current_source_path:
            desired=self.dpp_settings_dict();path=Path(self.current_source_path)
            w=FunctionWorker(self.render_raw_fast_preview,source,luts,controls,mode,rawp,base,dll,desired,path)
        else:
            w=FunctionWorker(self.render_engine.render,source,dll,base,luts,controls,mode,rawp,1800)
        self.start_worker(w,self.preview_pool,lambda result:self.fast_render_done(gen,result),lambda m,t:self.fast_render_error(gen,m,t))

    def fast_render_done(self,gen,result):
        if self.closing:return
        if gen==self.render_generation:self.display_render_result(gen,result,"interactive")
        self.preview_running=False
        if self.preview_pending is not None:
            next_gen=self.preview_pending;self.preview_pending=None;QTimer.singleShot(0,lambda:self.start_fast_render(next_gen))

    def fast_render_error(self,gen,msg,tb):
        if self.closing:return
        self.preview_running=False
        if self.preview_pending is not None:
            next_gen=self.preview_pending;self.preview_pending=None;QTimer.singleShot(0,lambda:self.start_fast_render(next_gen))
        elif gen==self.render_generation:self.status.setText("Cached composition unavailable: "+msg)
    def start_render(self,quality,gen=None):
        if self.closing or self.source_full is None:return
        if gen is None:
            self.render_generation+=1;gen=self.render_generation
        dll=self.dll_path(optional=True);base=self.current_base_path(optional=True)
        self.render_running=True;self.render_pending=None;self.viewer.setRendering(True)
        luts=list(self.luts);controls=self.controls_dict();mode="canon33" if self.render_mode.currentText().startswith("Canon") else "working"
        if self.source_is_raw and self.current_source_path:
            dpp_settings=self.dpp_settings_dict()
            post_wb={"ab_shift":self.ab_shift.value(),"gm_shift":self.gm_shift.value(),"custom_wb_mult":self.custom_wb_mult}
            wb=dpp_settings.get("wb","As Shot");fallback_decode="As Shot" if wb=="As Shot" else ("Auto" if wb.startswith("Auto") else "Daylight")
            native_size=self.source_native_size or self.source_full.size
            detail_requested=quality=="full" and self.viewer.zoom_mode!="Fit"
            portrait_native=int(native_size[1])>int(native_size[0])
            requested_size=native_size if detail_requested and not portrait_native else None
            w=FunctionWorker(self.render_raw_integrated,Path(self.current_source_path),luts,controls,mode,quality,dpp_settings,post_wb,self.base_combo.currentText(),base,dll,fallback_decode,self.shot_index.value(),self.source_full,requested_size,native_size,detail_requested)
        else:
            source=self.source_full;rawp=self.raw_preview_dict();max_side=1800
            w=FunctionWorker(self.render_engine.render,source,dll,base,luts,controls,mode,rawp,max_side)
        self.start_worker(w,self.engine_pool,lambda result:self.render_done(gen,result,quality),lambda m,t:self.render_error(gen,m,t))

    def render_done(self,gen,result,quality):
        if self.closing:return
        if gen==self.render_generation:self.display_render_result(gen,result,quality)
        self.render_running=False
        if self.render_pending:
            q,next_gen=self.render_pending;self.render_pending=None;QTimer.singleShot(20,lambda:self.start_render(q,next_gen))
        else:self.viewer.setRendering(False)

    def display_render_result(self,gen,result,quality):
        if isinstance(result,tuple) and len(result)==3:
            inp,out,info=result;info=info or {}
        else:
            inp,out=result;info={}
        canon_base=info.pop("_canon_base",None);canon_settings=info.pop("_canon_settings",None);canon_source=info.pop("_canon_source",None);canon_native=bool(info.pop("_canon_native",False));canon_resolution=info.pop("_canon_resolution",None)
        if canon_base is not None:
            self.last_canon_base=canon_base;self.last_canon_settings=canon_settings;self.last_canon_source=canon_source;self.last_canon_native=canon_native;self.last_canon_resolution=canon_resolution or info.get("resolution")
        previous_info=self.raw_info or {}
        for key in ("camera_make","camera_model","exif_orientation","raw_size","visible_size"):
            if key not in info and previous_info.get(key) is not None:info[key]=previous_info[key]
        self.raw_info=info
        logical_size=(info or {}).get("native_size") if self.source_is_raw else inp.size
        self.viewer.setImages(inp,out,logical_size)
        if self.scope_frame.isVisible():self.scope.setImage(out)
        if quality=="full" and self.current_reference>=0:self.filmstrip.set_thumbnail(self.current_reference,inp)
        backend=(info or {}).get("decoder") if self.source_is_raw else "Image"
        resolution=(info or {}).get("resolution")
        if backend and "DPP4Lib" in backend:self.raw_engine_label.setText("Canon DPP4Lib · NATIVE" if resolution=="native" else ("Canon DPP4Lib · PORTRAIT SAFE" if resolution=="portrait-safe" else "Canon DPP4Lib · READY"))
        elif backend and "Cached Canon" in backend:self.raw_engine_label.setText("Canon DPP4Lib · CACHED")
        elif self.source_is_raw:self.raw_engine_label.setText("LibRaw fallback")
        warn=(info or {}).get("warning") or (info or {}).get("fallback_reason")
        base_name=self.base_combo.currentText()
        render_size=(info or {}).get("render_size",inp.size)
        detail="Native RAW detail" if resolution=="native" else (f"Canon portrait safe detail {render_size[0]}×{render_size[1]}" if resolution=="portrait-safe" else ("Canon working resolution" if resolution=="working" else quality))
        self.status.setText(f"{base_name} · {backend or self.render_mode.currentText()} · {self.render_mode.currentText()} · {detail}"+(f" · {warn}" if warn else ""))

    def render_error(self,gen,msg,tb):
        if self.closing:return
        self.render_running=False
        if self.render_pending:
            q,next_gen=self.render_pending;self.render_pending=None;QTimer.singleShot(20,lambda:self.start_render(q,next_gen));return
        self.viewer.setRendering(False)
        if gen==self.render_generation:
            self.status.setText("Preview error");QMessageBox.critical(self,"Preview error",msg+"\n\n"+tb)

    def compare_mode_changed(self,x):self.viewer.setMode(x);self.mark_dirty()
    def zoom_changed(self,x):
        self.viewer.setZoomMode(x);self.request_zoom_resolution(x)
    def request_zoom_resolution(self,zoom):
        if zoom=="Fit" or not (self.source_is_raw and self.current_source_path and self.source_native_size):return
        current=str(Path(self.current_source_path).resolve())
        correct_source=self.last_canon_source==current
        correct_settings=self.last_canon_settings==self.dpp_settings_dict()
        native=self.source_native_size
        expected_resolution="portrait-safe" if int(native[1])>int(native[0]) else "native"
        if not (self.last_canon_resolution==expected_resolution and correct_source and correct_settings):self.schedule_render(False)
    def viewer_clipping(self,on):self.viewer.setClipping(on)
    def toggle_scopes(self,on):
        self.scope_frame.setVisible(on)
        if on and self.viewer.result_pil is not None:self.scope.setImage(self.viewer.result_pil)
    def view_state_changed(self,cx,cy,split,zoom):
        changed=self.zoom_combo.currentText()!=zoom
        self.zoom_combo.blockSignals(True);self.zoom_combo.setCurrentText(zoom);self.zoom_combo.blockSignals(False)
        if changed:self.request_zoom_resolution(zoom)
    def pixel_info(self,a,b):self.rgb_label.setText(f"Input {a[0]:3d} {a[1]:3d} {a[2]:3d}  →  Output {b[0]:3d} {b[1]:3d} {b[2]:3d}")
    def toggle_eyedropper(self,on):
        self.eyedropper_active=bool(on);self.viewer.setEyedropper(on)
        self.eyedrop.setText("Eyedropper WB · ON" if on else "Eyedropper WB")
        self.eyedrop.setProperty("eyedropperActive",bool(on));self.eyedrop.style().unpolish(self.eyedrop);self.eyedrop.style().polish(self.eyedrop)
        self.status.setText("Eyedropper active · click a neutral/gray area in the image" if on else "Ready")
    def pixel_clicked(self,sample):
        if not self.eyedropper_active:return
        try:
            point=sample.get("point") if isinstance(sample,dict) else None
            if point is None or self.viewer.input_pil is None:raise ValueError("No image point was selected.")
            measured=sample_custom_wb(self.viewer.input_pil,point[0],point[1],radius=8)
            correction=measured["mult"]
            if self.custom_wb_mult:
                correction=normalize_rgb_gains([self.custom_wb_mult[i]*correction[i] for i in range(3)])
            self.custom_wb_mult=list(correction);self.viewer.setEyedropperSample(measured["point"]);self.eyedrop.setChecked(False);self.commit_history(True)
            self.status.setText(f"Custom WB · 17×17 patch · RGB {measured['rgb']} · {measured['pixels']} valid pixels")
        except Exception as e:
            self.status.setText("WB sample rejected · "+str(e))
    def clear_custom_wb(self):self.custom_wb_mult=None;self.viewer.clearEyedropperSample();self.commit_history(True)

    # ---------- Snapshots ----------
    def save_snapshot(self,name):self.snapshots[name]=self.edit_state_dict();self.update_snapshot_buttons();self.mark_dirty();self.status.setText(f"Snapshot {name} saved")
    def load_snapshot(self,name):
        if not self.snapshots.get(name):self.status.setText(f"Snapshot {name} is empty · right-click to save");return
        self.apply_edit_state(self.snapshots[name],True);self.commit_history();self.status.setText(f"Snapshot {name} loaded")
    def clear_snapshot(self,name):self.snapshots[name]=None;self.update_snapshot_buttons();self.mark_dirty()
    def update_snapshot_buttons(self):
        for k,b in self.snapshot_buttons.items():b.setStored(bool(self.snapshots.get(k)))

    # ---------- Camera installation / export / drag-drop ----------
    def open_camera_install(self):
        try:self.dll_path();self.current_base_path()
        except Exception as exc:
            QMessageBox.critical(self,"Send to Camera",str(exc));return
        CameraInstallDialog(self,self).exec()

    def open_export(self):
        try:self.dll_path();self.current_base_path()
        except Exception as e:QMessageBox.critical(self,"Export",str(e));return
        if self.base_combo.currentText()!="Imported PF3" and not bool((self.base_resolution or {}).get("validated")):
            answer=QMessageBox.warning(self,"Experimental PF3 base","A hash-validated local PF3 template was not found for this Canon base.\n\nThe generated runtime template is experimental and does not preserve all properties of the validated Canon base. Use Bases… to locate the validated templates.\n\nContinue with experimental export?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:return
        ExportDialog(self,self).exec()
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():
            paths=[Path(u.toLocalFile()) for u in event.mimeData().urls() if u.toLocalFile()]
            lut=sum(1 for p in paths if p.suffix.lower()==".cube")
            raw=sum(1 for p in paths if p.suffix.lower() in CANON_STRONG_RAW_EXTENSIONS)
            self.status.setText(f"Drop to add/open · {lut} LUT · {raw} RAW · {len(paths)} file(s)");event.acceptProposedAction()
        else:super().dragEnterEvent(event)
    def dropEvent(self,event):
        paths=[Path(u.toLocalFile()) for u in event.mimeData().urls() if u.toLocalFile()]
        self.files_dropped(paths);event.acceptProposedAction()
    def files_dropped(self,paths):
        lut=[];refs=[]
        for p0 in paths:
            p=Path(p0);ext=p.suffix.lower()
            if ext==".canonstyleproject":self.open_project(p)
            elif ext==".pf3":self.open_pf3(p)
            elif ext==".cube":lut.append(p)
            elif ext in HALD_IMAGE_EXTENSIONS:
                try:parse_lut_file(p);lut.append(p)
                except Exception:refs.append(p)
            else:refs.append(p)
        if lut:self.add_lut_paths(lut)
        if refs:self.add_references(refs,select_last=True)

    def closeEvent(self,event):
        if self.dirty:
            ans=QMessageBox.question(self,"Unsaved project","Save project changes before closing?",QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
            if ans==QMessageBox.StandardButton.Cancel:event.ignore();return
            if ans==QMessageBox.StandardButton.Save:
                self.save_project_action()
                if self.dirty:event.ignore();return
        self.closing=True;self.full_render_timer.stop();self.canon_render_timer.stop();self.render_generation+=1;self.load_generation+=1
        self.render_pending=None;self.preview_pending=None
        for pool in (self.decode_pool,self.preview_pool,self.engine_pool):
            try:pool.clear()
            except Exception:pass
        try:self.dpp_client.cancel_active_render();self.dpp_client.close(force=True)
        except Exception:pass
        for pool in (self.decode_pool,self.preview_pool,self.engine_pool):
            try:pool.waitForDone(2500)
            except Exception:pass
        event.accept()


def _write_startup_error(text):
    try:
        p = logs_dir() / "startup_error.log"
        p.write_text(text, encoding="utf-8")
        return p
    except Exception:
        return None


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Canon Style Studio")
    app.setOrganizationName("CanonStyleStudio")
    app.setStyle("Fusion")
    app.setStyleSheet(app_stylesheet())

    try:
        w = CanonStyleStudioQt()
        w.show()
    except Exception:
        tb = traceback.format_exc()
        error_path=_write_startup_error(tb)
        try:
            QMessageBox.critical(None, "Canon Style Studio · startup error",
                                 "A aplicação falhou durante o arranque.\n\n"
                                 f"O erro foi guardado em:\n{error_path or 'startup_error.log'}\n\n" + tb)
        except Exception:
            pass
        print(tb, file=sys.stderr, flush=True)
        return 1

    if "--startup-smoke" in sys.argv:
        QTimer.singleShot(1800,app.quit)
    return int(app.exec())


if __name__=="__main__":
    raise SystemExit(main())
