from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from canon_engine import inspect_pf3
from canon_style_studio import CanonStyleStudioQt, ExportDialog, app_stylesheet
from canon_runtime import exported_styles_dir
from project_state import SettingsStore, load_project


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setStyleSheet(app_stylesheet())
    temporary = tempfile.TemporaryDirectory()
    window = CanonStyleStudioQt()
    window.settings = SettingsStore(Path(temporary.name) / "settings.json")
    window.show()
    target = Path(temporary.name) / "UI Export R+4 B-5.canonstyleproject"
    result = {"code": 1}

    try:
        window.recipe_wb_red.setValue(4)
        window.recipe_wb_blue.setValue(-5)
        window.recipe_color.setValue(4)
        dialog = ExportDialog(window, window)
        if Path(dialog.path.text()).parent.resolve() != exported_styles_dir().resolve():
            raise AssertionError(f"Default PF3 folder is not the shared Documents folder: {dialog.path.text()}")
        dialog.path.setText(str(target.with_suffix("")))
        dialog.start_export()
        dialog.show()

        def verify(_worker_result=None):
            try:
                if not target.is_file():
                    raise AssertionError("Export dialog did not create the PF3")
                project = load_project(target)
                if target.with_suffix('.manifest.json').exists() or target.with_suffix('.canonstyle.json').exists():
                    raise AssertionError('Style export created external sidecars')
                expected = {"red": 4, "blue": -5}
                actual = project.edit['recipe_wb']
                if actual != expected:
                    raise AssertionError(f"Recipe WB manifest mismatch: {actual}")
                if project.edit['creative']['recipe_color'] != 4:
                    raise AssertionError('Recipe Color was not preserved')
                basic = inspect_pf3(window.dll_path(optional=True), Path(project.renderedPf3))["basic"]
                result.update(code=0, size=target.stat().st_size, basic=basic, project=target.name)
            except Exception:
                result["error"] = traceback.format_exc()
            finally:
                app.quit()

        def failed(message, tb):
            result["error"] = f"{message}\n{tb}"
            app.quit()

        dialog.worker.signals.result.connect(verify)
        dialog.worker.signals.error.connect(failed)
        QTimer.singleShot(30000, lambda: (result.setdefault("error", "timeout"), app.quit()))
        app.exec()
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        if not window.engine_pool.waitForDone(30000):
            result.setdefault("error", "engine pool did not finish")
        window.dirty = False
        window.close()
        try:
            temporary.cleanup()
        except PermissionError as exc:
            result.setdefault("error", f"temporary PF3 remained locked: {exc}")
    print(result)
    return int(result["code"])


if __name__ == "__main__":
    raise SystemExit(main())
