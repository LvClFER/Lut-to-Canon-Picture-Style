from __future__ import annotations

import ctypes
import json
import os
import sys
import traceback
from pathlib import Path

import numpy as np
from PIL import Image

from canon_runtime import (
    discover_pse, ensure_runtime_input_profile, sha256_file,
    validate_canon_scanner_profile,
)

HERE = Path(__file__).resolve().parent

# The parent IPC client always speaks UTF-8. A frozen console executable would
# otherwise inherit the Windows ANSI code page and turn paths such as "João"
# into "JoÃ£o" while still returning superficially plausible JSON.
for _stream in (sys.stdin,sys.stdout):
    try:_stream.reconfigure(encoding="utf-8",errors="replace")
    except Exception:pass

WB_MODES = {
    "As Shot": 255,
    "Auto — Ambience": 0,
    "Auto — White": 23,
    "Daylight": 1,
    "Shade": 8,
    "Cloudy": 2,
    "Tungsten": 3,
    "White Fluorescent": 4,
    "Flash": 5,
    "Kelvin": 9,
}

# DPP4Lib's standalone preset enums are accepted but several of them have only
# a weak/inconsistent visual effect without the rest of the DPP application
# context.  Driving the documented Kelvin mode gives stable Canon-native RAW
# development and makes the fixed presets meaningfully distinct.
WB_PRESET_KELVIN = {
    "Daylight": 5200.0,
    "Shade": 7000.0,
    "Cloudy": 6000.0,
    "Tungsten": 3200.0,
    "White Fluorescent": 4000.0,
    "Flash": 6000.0,
}

PICTURE_STYLES = {
    "Standard": 0x81,
    "Portrait": 0x82,
    "Landscape": 0x83,
    "Neutral": 0x84,
    "Faithful": 0x85,
    "Fine Detail": 0x88,
}


def _pv(x):
    try:
        return int(x.value or 0)
    except Exception:
        return int(x or 0)


def _hrc(x):
    return f"0x{int(x) & 0xffffffff:08X}"


def validate_profile(path: Path):
    try:
        return validate_canon_scanner_profile(Path(path))
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def locate_dpp4lib():
    install = discover_pse()
    return install.dpp4lib_dir if install else None


class DppCore:
    def __init__(self):
        if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
            raise RuntimeError("Canon DPP4Lib backend requires Windows.")
        self.install = discover_pse()
        if not self.install:
            raise RuntimeError("Canon Picture Style Editor is required for Canon RAW rendering")
        self.libdir = self.install.dpp4lib_dir
        explicit_profile = os.environ.get("CANON_STYLE_STUDIO_PROFILE_PATH")
        self.profile_path = Path(explicit_profile) if explicit_profile else ensure_runtime_input_profile(self.install)
        self.profile_bytes = validate_profile(self.profile_path)

        if hasattr(os, "add_dll_directory"):
            self.dll_dir_ctx = os.add_dll_directory(str(self.libdir))
        else:
            self.dll_dir_ctx = None
        try:
            ctypes.windll.kernel32.SetDllDirectoryW(str(self.libdir))
        except Exception:
            pass
        # Canon's own standalone path expects its companion resources/DLLs relative to DPP4Lib.
        os.chdir(str(self.libdir))

        self.preloaded = []
        for name in [
            "Dpp3Engine.dll", "crxdec.dll", "DppCoreSub.dll", "DppCoreSubD.dll",
            "DppCoreSubM.dll", "DppCoreSubQ.dll", "DppCoreSubW.dll",
        ]:
            p = self.libdir / name
            if p.exists():
                try:
                    self.preloaded.append(ctypes.WinDLL(str(p)))
                except Exception:
                    pass

        self.dll = ctypes.WinDLL(str(self.libdir / "DppCore.dll"))
        self._bind()
        rc = self.InitializeSDK()
        if rc != 0:
            raise RuntimeError(f"DppInitializeSDK failed: {_hrc(rc)}")
        self.initialized = True
        # DPPCore's first process after SDK initialization is not colour-stable:
        # controlled probes show a large first/second-frame delta, while frames
        # two and three are byte-identical. Warm exactly once inside this process.
        self.render_warmed = False
        self.fs = ctypes.c_void_p()
        self.recipe = ctypes.c_void_p()
        self.raw_path = None

    def _fn(self, name, restype, argtypes):
        fn = getattr(self.dll, name)
        fn.restype = restype
        fn.argtypes = argtypes
        return fn

    def _bind(self):
        U = ctypes.c_uint32
        Q = ctypes.c_uint64
        P = ctypes.c_void_p
        PP = ctypes.POINTER(P)
        self.InitializeSDK = self._fn("DppInitializeSDK", U, [])
        self.TerminateSDK = self._fn("DppTerminateSDK", U, [])
        self.CreateFileStreamA = self._fn("DppCreateFileStreamA", U, [ctypes.c_char_p, U, U, PP])
        self.CreateImageServer = self._fn("DppCreateImageServer", U, [P, PP])
        self.RevertRecipe = self._fn("DppRevertRecipeToCaptured", U, [P])
        self.SetPropertyData = self._fn("DppSetPropertyData", U, [P, U, U, U, P])
        self.CreateMemoryStreamFromPointer = self._fn("DppCreateMemoryStreamFromPointer", U, [P, U, PP])
        self.SetPictureStyleUserProfile = self._fn("DppSetPictureStyleUserProfile", U, [P, P])
        self.ProcessImageEx = self._fn("DppProcessImageEx", U, [P, U, U, U, P, Q, P, PP])
        self.ProcessImageWithImageEx = self._fn("DppProcessImageWithImageEx", U, [P, P, U, U, P, Q, P, PP])
        self.OutputImageToStream = self._fn("DppOutputImageToStream", U, [P, U, U, P])
        try:
            self.Release = self._fn("DppRelease", U, [P])
        except Exception:
            self.Release = None

    def _release(self, p):
        if self.Release is not None and _pv(p):
            try:
                self.Release(p)
            except Exception:
                pass

    def close_raw(self):
        self._release(self.recipe)
        self._release(self.fs)
        self.recipe = ctypes.c_void_p()
        self.fs = ctypes.c_void_p()
        self.raw_path = None

    def open_raw(self, raw_path):
        raw_path = str(Path(raw_path).resolve())
        if self.raw_path == raw_path and _pv(self.recipe):
            return
        self.close_raw()
        fs = ctypes.c_void_p()
        rc = self.CreateFileStreamA(os.fsencode(raw_path), 2, 0, ctypes.byref(fs))
        if rc != 0 or not _pv(fs):
            raise RuntimeError(f"DppCreateFileStreamA failed: {_hrc(rc)}")
        recipe = ctypes.c_void_p()
        rc2 = self.CreateImageServer(fs, ctypes.byref(recipe))
        if rc2 != 0 or not _pv(recipe):
            self._release(fs)
            raise RuntimeError(f"DppCreateImageServer failed: {_hrc(rc2)}")
        self.fs = fs
        self.recipe = recipe
        self.raw_path = raw_path

    def _set_u32(self, prop, value):
        v = ctypes.c_uint32(int(value))
        rc = self.SetPropertyData(self.recipe, prop, 0, 4, ctypes.byref(v))
        if rc != 0:
            raise RuntimeError(f"DppSetPropertyData(0x{prop:05X}) failed: {_hrc(rc)}")

    def _set_f64(self, prop, value):
        v = ctypes.c_double(float(value))
        rc = self.SetPropertyData(self.recipe, prop, 0, 8, ctypes.byref(v))
        if rc != 0:
            raise RuntimeError(f"DppSetPropertyData(0x{prop:05X}) failed: {_hrc(rc)}")

    def _apply_settings(self, s):
        self._set_f64(0x20001, s.get("exposure", 0.0))
        wb = s.get("wb", "As Shot")
        if wb == "Auto Calculated":  # compatibility with V0.4 projects
            wb = "Auto — Ambience"
        fixed_kelvin = WB_PRESET_KELVIN.get(wb)
        if wb == "Kelvin" or fixed_kelvin is not None:
            self._set_u32(0x20101, WB_MODES["Kelvin"])
            self._set_f64(0x20102, fixed_kelvin if fixed_kelvin is not None else s.get("kelvin", 5200.0))
        else:
            self._set_u32(0x20101, WB_MODES.get(wb, 255))
        # Confirmed against warmed standalone renders.  DPP stores these as
        # float64 recipe properties: 0x20106 positive moves B->A (amber), while
        # 0x20105 positive moves M->G, hence the sign inversion for our UI where
        # positive G<->M means magenta.
        self._set_f64(0x20106, s.get("wb_ab_shift", 0.0))
        self._set_f64(0x20105, -float(s.get("wb_gm_shift", 0.0)))
        self._set_u32(0x10200, 1)
        self._set_u32(0x20301, PICTURE_STYLES.get(s.get("style", "Neutral"), 0x84))
        self._set_f64(0x20303, s.get("contrast", 0.0))
        # Validated on warmed EOS RP DPP4Lib renders. 0x20304 primarily changes
        # hue/skin Color Tone; 0x20305 is the strong chroma/Saturation control.
        # These were historically wired in the opposite order in the Studio UI.
        self._set_f64(0x20304, s.get("color_tone", 0.0))
        self._set_f64(0x20305, s.get("saturation", 0.0))
        # These setters are accepted by DppCore, but their visual develop path has not
        # yet been confirmed standalone. They are still written so future DPP builds
        # can consume them without changing the IPC contract.
        self._set_f64(0x20308, s.get("sharp_strength", 0.0))
        self._set_f64(0x20309, s.get("fineness", 2.0))
        self._set_f64(0x2030A, s.get("threshold", 4.0))

    def render(self, raw_path, settings, width=1620, height=1080):
        if not self.render_warmed:
            long_side=max(1,int(max(width,height)))
            scale=min(1.0,480.0/long_side)
            warm_width=max(1,int(round(int(width)*scale)))
            warm_height=max(1,int(round(int(height)*scale)))
            self._render_once(raw_path,settings,warm_width,warm_height)
            self.render_warmed=True
        return self._render_once(raw_path,settings,width,height)

    def _render_once(self, raw_path, settings, width=1620, height=1080):
        self.open_raw(raw_path)
        rc = self.RevertRecipe(self.recipe)
        if rc != 0:
            raise RuntimeError(f"DppRevertRecipeToCaptured failed: {_hrc(rc)}")
        self._apply_settings(settings)

        keep = []
        profile_stream = base_image = output_image = output_stream = ctypes.c_void_p()
        try:
            pbuf = ctypes.create_string_buffer(self.profile_bytes, len(self.profile_bytes))
            keep.append(pbuf)
            profile_stream = ctypes.c_void_p()
            rc = self.CreateMemoryStreamFromPointer(
                ctypes.cast(pbuf, ctypes.c_void_p), len(self.profile_bytes), ctypes.byref(profile_stream)
            )
            if rc != 0 or not _pv(profile_stream):
                raise RuntimeError(f"Create profile stream failed: {_hrc(rc)}")
            rc = self.SetPictureStyleUserProfile(self.recipe, profile_stream)
            if rc != 0:
                raise RuntimeError(f"DppSetPictureStyleUserProfile failed: {_hrc(rc)}")

            Rect = ctypes.c_int32 * 4

            # Canon RAW orientation is metadata. The internal DPP develop stage still
            # operates in sensor/native landscape geometry, while the streamed RGB
            # output is orientation-aware. If we rotate the ProcessImage geometry too,
            # portrait files render only a cropped top section.
            output_width = int(width)
            output_height = int(height)
            if output_height > output_width:
                # DPP4Lib standalone silently corrupts portrait streams above
                # the validated 1080x1620 canvas: it returns success but leaves
                # most of the image as stretched rows/columns. Never expose such
                # a frame to the viewer or persist it in the render cache.
                if output_width > 1080 or output_height > 1620:
                    raise RuntimeError(
                        "Unsafe DPP4Lib portrait output rejected: "
                        f"{output_width}x{output_height} exceeds 1080x1620"
                    )
                # Stage 1 remains in sensor-landscape geometry; stage 2 below
                # requests the final orientation-aware portrait stream.
                process_width = output_height
                process_height = output_width
            else:
                process_width = output_width
                process_height = output_height

            process_packed = (int(process_height) << 32) | int(process_width)
            auxbuf = (ctypes.c_ubyte * 256)()
            keep.append(auxbuf)
            aux = ctypes.cast(auxbuf, ctypes.c_void_p)

            rect1 = Rect(0, 0, int(process_width), int(process_height))
            base_image = ctypes.c_void_p()
            rc = self.ProcessImageEx(
                self.recipe, 1, 1, 1, ctypes.byref(rect1), process_packed, aux, ctypes.byref(base_image)
            )
            if rc != 0 or not _pv(base_image):
                raise RuntimeError(f"DppProcessImageEx failed: {_hrc(rc)}")

            # Stage 1 must use native/sensor landscape geometry, but stage 2 is
            # the oriented output geometry.  Passing landscape here too produces
            # a cropped top section and makes a portrait stride fail with 0x60.
            # This split was confirmed with both EOS RP portrait samples.
            output_packed = (int(output_height) << 32) | int(output_width)
            rect2 = Rect(0, 0, int(output_width), int(output_height))
            output_image = ctypes.c_void_p()
            rc = self.ProcessImageWithImageEx(
                self.recipe, base_image, 0, 0, ctypes.byref(rect2), output_packed, aux, ctypes.byref(output_image)
            )
            if rc != 0 or not _pv(output_image):
                raise RuntimeError(f"DppProcessImageWithImageEx failed: {_hrc(rc)}")

            # The stream is orientation-aware: portrait RAWs are written as
            # output_width x output_height, even though develop ran landscape.
            stride = output_width * 3
            size = stride * output_height
            rgbbuf = ctypes.create_string_buffer(size)
            keep.append(rgbbuf)
            output_stream = ctypes.c_void_p()
            rc = self.CreateMemoryStreamFromPointer(
                ctypes.cast(rgbbuf, ctypes.c_void_p), size, ctypes.byref(output_stream)
            )
            if rc != 0 or not _pv(output_stream):
                raise RuntimeError(f"Create output stream failed: {_hrc(rc)}")
            rc = self.OutputImageToStream(output_image, 0x0D, stride, output_stream)
            if rc != 0:
                raise RuntimeError(f"DppOutputImageToStream failed: {_hrc(rc)}")

            # Canon format 0x0D is BGR24, proven against PSE/DPP renders.
            arr = np.frombuffer(rgbbuf.raw[:size], dtype=np.uint8).reshape(output_height, stride)
            arr = arr[:, :output_width * 3].reshape(output_height, output_width, 3)
            rgb = arr[..., ::-1].copy()
            return Image.fromarray(rgb, "RGB")
        finally:
            for p in [output_stream, output_image, base_image, profile_stream]:
                self._release(p)

    def shutdown(self):
        self.close_raw()
        if getattr(self, "initialized", False):
            try:
                self.TerminateSDK()
            except Exception:
                pass
            self.initialized = False


def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    core = None
    try:
        core = DppCore()
        send({
            "type": "ready",
            "ok": True,
            "dpp4lib": str(core.libdir),
            "dppcore": str(core.install.dppcore_dll),
            "dppcore_version": core.install.dppcore_version,
            "dppcore_sha256": sha256_file(core.install.dppcore_dll),
            "pse": str(core.install.pse_dir),
            "pse_exe": str(core.install.pse_exe),
            "pse_version": core.install.pse_version,
            "profile": str(core.profile_path),
            "profile_sha256": sha256_file(core.profile_path),
            "profile_bytes": len(core.profile_bytes),
        })
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            req = json.loads(line)
            rid = req.get("id")
            cmd = req.get("cmd")
            try:
                if cmd == "ping":
                    send({
                        "id": rid, "ok": True, "dpp4lib": str(core.libdir), "raw": core.raw_path,
                        "dppcore": str(core.install.dppcore_dll),
                        "dppcore_version": core.install.dppcore_version,
                        "dppcore_sha256": sha256_file(core.install.dppcore_dll),
                        "pse": str(core.install.pse_dir), "pse_exe": str(core.install.pse_exe),
                        "pse_version": core.install.pse_version,
                        "profile": str(core.profile_path), "profile_sha256": sha256_file(core.profile_path),
                    })
                elif cmd == "render":
                    out = Path(req["output"])
                    out.parent.mkdir(parents=True, exist_ok=True)
                    im = core.render(
                        req["path"], req.get("settings") or {},
                        int(req.get("width", 1620)), int(req.get("height", 1080)),
                    )
                    # Atomic uncompressed RGB IPC/cache avoids PNG compression and
                    # decoding on every slider render. Dimensions are carried in
                    # the response and validated by the client before use.
                    tmp = out.with_suffix(out.suffix + ".tmp")
                    tmp.write_bytes(im.tobytes())
                    tmp.replace(out)
                    send({
                        "id": rid, "ok": True, "output": str(out), "size": list(im.size),
                        "backend": "Canon DPP4Lib standalone", "dpp4lib": str(core.libdir),
                    })
                elif cmd == "close_raw":
                    core.close_raw()
                    send({"id": rid, "ok": True})
                elif cmd == "shutdown":
                    send({"id": rid, "ok": True})
                    break
                else:
                    raise RuntimeError(f"Unknown worker command: {cmd}")
            except Exception as e:
                send({"id": rid, "ok": False, "error": str(e), "traceback": traceback.format_exc()})
    except Exception as e:
        send({"type": "ready", "ok": False, "error": str(e), "traceback": traceback.format_exc()})
        return 2
    finally:
        if core is not None:
            try:
                core.shutdown()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
