from __future__ import annotations

import json
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
from project_state import SettingsStore


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(app_stylesheet())
    temporary = tempfile.TemporaryDirectory()
    window = CanonStyleStudioQt()
    window.settings = SettingsStore(Path(temporary.name) / "settings.json")
    target = Path(temporary.name) / "UI Export R+4 B-5.pf3"
    result = {"code": 1}

    try:
        window.recipe_wb_red.setValue(4)
        window.recipe_wb_blue.setValue(-5)
        dialog = ExportDialog(window, window)
        if Path(dialog.path.text()).parent.resolve() != exported_styles_dir().resolve():
            raise AssertionError(f"Default PF3 folder is not portable exported_styles: {dialog.path.text()}")
        dialog.path.setText(str(target.with_suffix("")))
        dialog.start_export()

        def verify(_worker_result=None):
            try:
                if not target.is_file():
                    raise AssertionError("Export dialog did not create the PF3")
                if target.stat().st_size != 434511:
                    raise AssertionError(f"Unexpected PF3 size: {target.stat().st_size}")
                manifest_path = target.with_suffix(".manifest.json")
                sidecar_path = target.with_suffix(".canonstyle.json")
                if not manifest_path.is_file() or not sidecar_path.is_file():
                    raise AssertionError("Export dialog did not create manifest and sidecar")
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                expected = {"red": 4, "blue": -5}
                actual = {key: manifest["recipeWhiteBalance"][key] for key in expected}
                if actual != expected:
                    raise AssertionError(f"Recipe WB manifest mismatch: {actual}")
                if manifest["recipeWhiteBalance"]["method"] != "fuji-xt1-provia-rb-lut-v2":
                    raise AssertionError("Manifest contains the obsolete Recipe WB method")
                basic = inspect_pf3(window.dll_path(), target)["basic"]
                result.update(code=0, size=target.stat().st_size, basic=basic, manifest=manifest_path.name)
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
        window.dirty = False
        window.close()
        temporary.cleanup()
    print(result)
    return int(result["code"])


if __name__ == "__main__":
    raise SystemExit(main())
