from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from canon_engine import (
    CanonRenderEngine, apply_linear_rgb_gains, canon_table_to_pillow_lut, export_pf3,
    ensure_runtime_base_pf3, find_dll, inspect_pf3, make_wb_lut_from_kelvin, parse_lut_file,
    resolve_validated_base_pf3, load_lut_metadata,
    sample_custom_wb, wb_shift_gains, load_reference_image, read_base_properties, PICTURE_STYLE_IDS,
)
from canon_runtime import (
    app_data_dir, application_root, camera_support_dir, discover_pse,
    ensure_runtime_input_profile, exported_styles_dir,
)
from test_report import create_test_report_zip, validate_test_report_zip
from dpp_client import DppBackendClient, DppBackendError
from project_state import HistoryManager, ProjectDocument, load_project, save_project
from render_geometry import fit_size_within_box, oriented_native_size
from camera_install.rp_assets import RpAssetSet, discover_rp_assets, validate_rp_asset_folder
from camera_install.eos_hook import EosRpInstaller
from camera_install.rp_payload import (
    BLOCK_SIZE, LEGACY_SIZE, NAME_OFFSETS, RP_BLOCK_OFFSET, RP_PAYLOAD_SIZE,
    build_rp_payload, extract_duplicate_block1, extract_legacy_block1, validate_agent_source,
    validate_compiler_selftest,
)
from creative_controls import (
    IDENTITY_TONE_CURVE, apply_creative_rgb, creative_cube,
    creative_is_neutral, normalize_creative_controls,
    apply_recipe_wb_rgb, normalize_recipe_wb, recipe_wb_cube,
    recipe_wb_is_neutral, recipe_wb_linear_gains,
)


HERE = Path(__file__).resolve().parent
RAW_ROOT = Path(os.environ.get("CANON_STYLE_STUDIO_TEST_DIR", HERE / "test_files"))


def luminance_structure_correlation(reference, candidate):
    """Low-resolution geometry check that ignores render resolution and colour."""
    portrait=reference.height>reference.width
    sample_size=(128,192) if portrait else (192,128)
    a=np.asarray(reference.convert("L").resize(sample_size,Image.Resampling.LANCZOS),dtype=np.float32)
    b=np.asarray(candidate.convert("L").resize(sample_size,Image.Resampling.LANCZOS),dtype=np.float32)
    a=(a-a.mean()).ravel();b=(b-b.mean()).ravel()
    denom=float(np.linalg.norm(a)*np.linalg.norm(b))
    return float(np.dot(a,b)/denom) if denom>1e-6 else 0.0


class CoreRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cube_path=HERE / "example_luts" / "superia.cube"
        if cube_path.is_file():cls.cube=parse_lut_file(cube_path)
        else:
            n=17;values=[]
            for b in range(n):
                for g in range(n):
                    for r in range(n):values.extend((min(1,r/(n-1)*1.05),g/(n-1)*0.92,b/(n-1)))
            cls.cube={"size":n,"values":np.asarray(values,dtype=np.float32),"domain_min":[0,0,0],"domain_max":[1,1,1],"source":"generated"}
        cls.hald = parse_lut_file(HERE / "example_luts" / "hald_identity_8.png")

    def test_cube_and_hald(self):
        self.assertIn(self.cube["size"], (17,33))
        self.assertEqual(self.hald["source"], "hald")
        self.assertEqual(self.hald["size"], 64)
        src=Image.fromarray(np.random.default_rng(7).integers(0,256,size=(96,128,3),dtype=np.uint8),"RGB")
        identity=src.filter(CanonRenderEngine().pillow_for_cube(self.hald))
        self.assertLess(float(np.abs(np.asarray(src,dtype=np.int16)-np.asarray(identity,dtype=np.int16)).mean()),0.08)

    def test_hald_uses_validated_linear_r_fastest_order(self):
        # Hald level 2 = 8x8 image = a 4^3 LUT. Its flattened row-major
        # pixels are the LUT rows; no tile reinterpretation is permitted.
        pixels=np.arange(64*3,dtype=np.uint8).reshape(8,8,3)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"ordered_hald.png";Image.fromarray(pixels,"RGB").save(path)
            lut=parse_lut_file(path)
        self.assertEqual(lut["size"],4)
        self.assertTrue(np.allclose(np.asarray(lut["values"]).reshape(-1,3),pixels.reshape(-1,3)/255.0,atol=1e-7))

    def test_lut_metadata_preferred_standard(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"Velvia50_Frontier_CANON_FULL_MATCH_v4_33.cube"
            path.write_text("LUT_3D_SIZE 2\n"+"\n".join(f"{r} {g} {b}" for b in (0,1) for g in (0,1) for r in (0,1)),encoding="utf-8")
            cube=parse_lut_file(path);meta=load_lut_metadata(path,cube)
        self.assertEqual(meta["preferredBaseStyle"],"Standard")
        self.assertEqual(meta["calibrationSource"],"Canon Standard")
        self.assertEqual(meta["lutSize"],2)

    def test_portable_runtime_storage_is_beside_application(self):
        root=application_root().resolve()
        self.assertEqual(app_data_dir().resolve().parent,root)
        self.assertEqual(exported_styles_dir().resolve().parent,root)
        self.assertEqual(camera_support_dir().resolve().parent,root)
        self.assertNotIn("AppData\\Local\\CanonStyleStudio",str(app_data_dir()))

    def test_eos_rp_payload_preserves_carrier_outside_validated_fields(self):
        carrier=bytearray(b"\xA5"*RP_PAYLOAD_SIZE)
        carrier[8:40]=b"TWILIGHT"+bytes(24);carrier[44:76]=b"TWILIGHT"+bytes(24)
        block=bytes((index*17+3)&0xff for index in range(BLOCK_SIZE))
        output=build_rp_payload(bytes(carrier),block,"Teste João")
        self.assertEqual(len(output),RP_PAYLOAD_SIZE)
        self.assertEqual(output[RP_BLOCK_OFFSET:RP_BLOCK_OFFSET+BLOCK_SIZE],block)
        self.assertEqual(output[8:40].split(b"\0",1)[0],b"Teste Joao")
        self.assertEqual(output[44:76].split(b"\0",1)[0],b"Teste Joao")
        protected=set(range(RP_BLOCK_OFFSET,RP_BLOCK_OFFSET+BLOCK_SIZE))
        for offset in NAME_OFFSETS:protected.update(range(offset,offset+32))
        self.assertTrue(all(output[index]==carrier[index] for index in range(len(output)) if index not in protected))

    def test_eos_rp_compiler_selftest_is_exact_and_fail_closed(self):
        expected=bytes((index*11)&0xff for index in range(BLOCK_SIZE))
        legacy=bytes(360)+expected+expected
        self.assertEqual(len(legacy),LEGACY_SIZE)
        self.assertEqual(extract_duplicate_block1(legacy),expected)
        validate_compiler_selftest(legacy,expected)
        corrupted=bytearray(legacy);corrupted[400]^=1
        with self.assertRaises(RuntimeError):validate_compiler_selftest(bytes(corrupted),expected)
        with self.assertRaises(RuntimeError):extract_duplicate_block1(legacy[:-1])

    def test_eos_rp_target_uses_exact_block1_when_block2_differs(self):
        block1=bytes((index*7+1)&0xff for index in range(BLOCK_SIZE))
        block2=bytes((index*11+3)&0xff for index in range(BLOCK_SIZE))
        legacy=bytes(360)+block1+block2
        self.assertEqual(extract_legacy_block1(legacy),block1)
        with self.assertRaisesRegex(RuntimeError,"Block1/Block2"):
            extract_duplicate_block1(legacy)

    def test_camera_agent_keeps_0x115_observation_only(self):
        agent=(HERE/"camera_install"/"rp_loader_agent.js").read_text(encoding="utf-8")
        validate_agent_source(agent)
        self.assertIn("if (!isUserDefSlot) return",agent)
        self.assertNotIn("this.param !== selectedParam",agent)
        self.assertIn("native_payload_captured",agent)
        self.assertIn("args[4].readByteArray(this.n)",agent)

        dynamic=(HERE/"camera_install"/"dynamic_camera_agent.js").read_text(encoding="utf-8")
        validate_agent_source(dynamic)
        self.assertIn("armdynamic",dynamic)
        self.assertIn("EdsCfpGetPropertySize",dynamic)
        self.assertIn("capturedCameraId",dynamic)
        self.assertIn("capturedDescriptor",dynamic)
        self.assertIn("validateNativeRoundTrip",dynamic)
        self.assertIn("meaningfulDifferences",dynamic)
        self.assertIn("Canon compiler output is identical",dynamic)
        self.assertIn("armedLegacyBlock1",dynamic)
        self.assertIn("legacy-dual-8192-block-carrier",dynamic)
        self.assertIn("CAMERA_FAMILY_REGISTRY",dynamic)
        self.assertIn("modern-78980-pf3-table-encoder-v1",dynamic)
        self.assertIn("modern-83076-pf3-table-encoder-v1",dynamic)
        self.assertIn("modern-full33-paired",dynamic)
        self.assertIn("sizes: [78980]",dynamic)
        self.assertIn("sizes: [83076]",dynamic)
        self.assertIn("sizes: [431616]",dynamic)
        self.assertIn("native_payload_captured",dynamic)
        self.assertIn("0x40001070",dynamic)
        self.assertIn("0x40001071",dynamic)
        self.assertIn("preservedRegions: ['0x1F01', '0x102A']",dynamic)
        self.assertIn("const LEGACY_NAME_OFFSETS = [8, 44]",dynamic)
        self.assertIn("const MODERN_NAME_OFFSETS = [8, 46]",dynamic)
        self.assertIn("patchPayloadName(output, MODERN_NAME_OFFSETS)",dynamic)
        self.assertIn("patchPayloadName(output, LEGACY_NAME_OFFSETS)",dynamic)
        self.assertNotIn("api.Set(ref, 0x01000203",dynamic)
        self.assertNotIn("this.n !== 16752",dynamic)

    def test_unknown_camera_payload_capture_is_read_only_and_persistent(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);events=[]
            installer=object.__new__(EosRpInstaller)
            installer.event_callback=events.append
            installer._lock=threading.RLock()
            installer._report={"status":"ARMED","events":[]}
            installer._report_path=root/"EOS_RP_INSTALL_REPORT.json"
            installer.armed=True
            installer._ready=threading.Event()
            raw=bytes((index*29+7)&0xff for index in range(83076))
            installer._on_message(
                {"type":"send","payload":{"type":"native_payload_captured","slot":3,
                                               "inParam":35,"size":len(raw),"readOnly":True}},raw
            )
            capture=root/"NATIVE_01000203_SLOT3_83076.bin"
            self.assertEqual(capture.read_bytes(),raw)
            saved=installer._report["nativePayloadCapture"]
            self.assertEqual(saved["sha256"],hashlib.sha256(raw).hexdigest())
            self.assertTrue(saved["readOnly"]);self.assertFalse(saved["argumentsModified"])
            self.assertEqual(events[-1]["captureFile"],capture.name)

    def test_dynamic_camera_report_hashes_native_carrier_without_storing_it(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);events=[]
            installer=object.__new__(EosRpInstaller)
            installer.event_callback=events.append
            installer._lock=threading.RLock()
            installer._report={"status":"ARMED","events":[]}
            installer._report_path=root/"CANON_CAMERA_INSTALL_REPORT.json"
            installer.armed=True
            installer._ready=threading.Event()
            native=bytes((index*17+9)&0xff for index in range(83076))
            installer._on_message(
                {"type":"send","payload":{"type":"native_payload_observed","slot":1,"size":len(native)}},native
            )
            self.assertEqual(installer._report["nativeCarrier"]["sha256"],hashlib.sha256(native).hexdigest())
            self.assertFalse(installer._report["nativeCarrier"]["stored"])
            self.assertFalse(any(root.glob("NATIVE_*.bin")))
            outgoing=bytes((value^0x5a) for value in native)
            compiler={"cameraIdHex":"81040080","descriptorSize":15076,"outputSize":len(outgoing)}
            installer._on_message(
                {"type":"send","payload":{"type":"payload_patched","slot":1,"size":len(outgoing),"compiler":compiler}},outgoing
            )
            self.assertEqual(installer._report["dynamicCompiler"],compiler)
            self.assertEqual(installer._report["patchedPayloadSize"],len(outgoing))

    def test_external_eos_rp_support_assets_when_configured(self):
        folder=os.environ.get("CANON_STYLE_STUDIO_RP_ASSETS")
        if not folder:self.skipTest("External EOS RP research fixtures are intentionally absent from public packages")
        assets=validate_rp_asset_folder(folder)
        self.assertEqual(len(assets.read_selftest_block()),8192)
        self.assertEqual(len(assets.read_carrier()),16752)
        self.assertEqual(discover_rp_assets(folder).root,assets.root)

    def test_eos_rp_prepare_flow_arms_only_after_exact_selftest(self):
        class FakeExports:
            def __init__(self):self.calls=[]
            def armdynamic(self,slot,pf3_path,name,block1_hex):
                self.calls.append((slot,pf3_path,name,block1_hex));return True
        class FakeScript:
            def __init__(self):self.exports_sync=FakeExports()

        with tempfile.TemporaryDirectory() as td:
            root=Path(td);expected=bytes((index*13)&0xff for index in range(BLOCK_SIZE))
            target=bytes((index*19+5)&0xff for index in range(BLOCK_SIZE))
            paths={
                "selftest_pf3":root/"selftest.pf3","selftest_block":root/"expected.bin",
                "rp_carrier":root/"carrier.bin","camera_id":root/"camera.bin","descriptor":root/"descriptor.bin",
            }
            paths["selftest_pf3"].write_bytes(bytes(434511));paths["selftest_block"].write_bytes(expected)
            paths["rp_carrier"].write_bytes(bytes([0xA5])*RP_PAYLOAD_SIZE)
            paths["camera_id"].write_bytes(bytes(4));paths["descriptor"].write_bytes(bytes(7772))
            assets=RpAssetSet(root=root,hashes={"fixture":"test"},**paths)
            pf3_data=bytearray(434511);pf3_data[4:7]=b"PSP"
            pf3=root/"current.pf3";pf3.write_bytes(pf3_data)
            base_pf3=root/"base.pf3";base_pf3.write_bytes(pf3_data)

            events=[];installer=EosRpInstaller(assets,event_callback=events.append)
            fake=FakeScript();installer.connect=lambda **_kwargs:setattr(installer,"script",fake) or fake
            target_block2=bytes((index*23+9)&0xff for index in range(BLOCK_SIZE))
            compiled=iter((
                ({"ok":True},bytes(360)+expected+expected),
                ({"ok":True},bytes(360)+target+target_block2),
                ({"ok":True},bytes(360)+expected+expected),
            ))
            installer._compile=lambda _path:next(compiled)
            result=installer.prepare_and_arm(
                pf3,2,"Câmara João",root/"output",launch_eos=False,
                base_pf3_path=base_pf3,
            )
            self.assertTrue(installer.armed);self.assertEqual(len(fake.exports_sync.calls),1)
            slot,armed_pf3,name,block1_hex=fake.exports_sync.calls[0]
            self.assertEqual(slot,2);self.assertEqual(name,"Camara Joao");self.assertEqual(Path(armed_pf3),pf3.resolve())
            self.assertEqual(bytes.fromhex(block1_hex),target)
            report=json.loads(Path(result["reportPath"]).read_text(encoding="utf-8"))
            self.assertTrue(report["compilerSelfTest"]["exact"]);self.assertFalse(report["cameraWritePolicy"]["patch115"])
            self.assertEqual(report["targetCompiler"]["policy"],"validated legacy oracle Block1 adapted to the live Canon carrier family")
            self.assertEqual(report["targetCompiler"]["differentBytesFromBase"],sum(a!=b for a,b in zip(target,expected)))
            self.assertTrue(report["cameraWritePolicy"]["requireNativeSizeMatch"])
            self.assertTrue(report["cameraWritePolicy"]["rejectIdenticalCarrier"])
            self.assertTrue(report["cameraWritePolicy"]["requirePf3DifferencesOutsideMetadata"])

            blocked=EosRpInstaller(assets)
            blocked_fake=FakeScript();blocked.connect=lambda **_kwargs:setattr(blocked,"script",blocked_fake) or blocked_fake
            bad=bytearray(expected);bad[0]^=1
            blocked._compile=lambda _path:({"ok":True},bytes(360)+bytes(bad)+bytes(bad))
            with self.assertRaisesRegex(RuntimeError,"byte-for-byte"):
                blocked.prepare_and_arm(pf3,1,"Blocked",root/"blocked",launch_eos=False)
            self.assertFalse(blocked.armed);self.assertEqual(blocked_fake.exports_sync.calls,[])

    def test_runtime_generated_canon_styles(self):
        dll=find_dll()
        if not dll:self.skipTest("Canon EdsCFParse.dll unavailable")
        for name in ("Standard","Portrait","Landscape","Neutral","Faithful","Fine Detail"):
            path=ensure_runtime_base_pf3(dll,name)
            data=path.read_bytes()
            self.assertEqual(len(data),434511,name)
            self.assertEqual(data[4:7],b"PSP",name)

    def test_validated_local_base_selection(self):
        dll=find_dll()
        if not dll:self.skipTest("Canon EdsCFParse.dll unavailable")
        if not (HERE/"bases").is_dir():self.skipTest("Research base fixtures are intentionally absent from public package")
        for style in ("Neutral","Standard","Faithful","Portrait","Landscape"):
            result=resolve_validated_base_pf3(dll,style,[HERE/"bases"])
            self.assertIsNotNone(result,style);self.assertTrue(result["validated"],style)
            self.assertEqual(result["style"],style)

    def test_export_preserves_selected_real_base(self):
        dll=find_dll()
        if not dll or not (HERE/"bases").is_dir():self.skipTest("Validated local research bases unavailable")
        controls={"contrast":0,"saturation":0,"color_tone":0,"sharpness_override":False}
        with tempfile.TemporaryDirectory() as td:
            for style in ("Neutral","Standard","Faithful","Portrait","Landscape"):
                resolved=resolve_validated_base_pf3(dll,style,[HERE/"bases"]);base=resolved["path"];out=Path(td)/(style+".pf3")
                export_pf3(dll,base,out,[],controls,style)
                before=read_base_properties(dll,base,wanted=[(0x00000114,4),(0x40001070,215628),(0x40001071,215628)])
                after=read_base_properties(dll,out,wanted=[(0x00000114,4),(0x40001070,215628),(0x40001071,215628)])
                self.assertEqual(int.from_bytes(after[0x00000114],"little"),PICTURE_STYLE_IDS[style])
                self.assertEqual(before,after,style)

    def test_lut_stack_opacity_and_canon33_without_picture_style(self):
        engine = CanonRenderEngine()
        src = Image.linear_gradient("L").resize((128, 96)).convert("RGB")
        controls = {"sharpness_override": False}
        no_luts = []
        inp, quantized_identity = engine.render_from_canon_base(src, no_luts, controls, "canon33")
        self.assertEqual(inp.tobytes(), quantized_identity.tobytes())

        layer = {"id": "a", "cube": self.cube, "enabled": True, "opacity": 0.35}
        _, working = engine.render_from_canon_base(src, [layer], controls, "working")
        transformed = src.filter(engine.pillow_for_cube(self.cube))
        expected = Image.blend(src, transformed, 0.35)
        self.assertEqual(working.tobytes(), expected.tobytes())

        _, quantized = engine.render_from_canon_base(src, [layer], controls, "canon33")
        self.assertNotEqual(src.tobytes(), quantized.tobytes())

    def test_creative_controls_identity_tone_axes_and_chrome(self):
        samples=np.asarray([[0.20,0.20,0.20],[0.85,0.12,0.08],[0.08,0.20,0.85]],dtype=np.float64)
        self.assertTrue(creative_is_neutral({}))
        self.assertTrue(np.array_equal(apply_creative_rgb(samples,{}),samples))

        tone={"tone_curve":[0.0,0.15,0.45,0.80,1.0]}
        toned=apply_creative_rgb(samples,tone)
        self.assertLess(float(toned[0].mean()),float(samples[0].mean())-0.05)

        axes={"color_axes":{"Red":{"hue":18,"saturation":-35,"luminance":-20}}}
        adjusted=apply_creative_rgb(samples,axes)
        self.assertGreater(float(np.linalg.norm(adjusted[1]-samples[1])),float(np.linalg.norm(adjusted[2]-samples[2]))*3.0)

        chrome=apply_creative_rgb(samples,{"color_chrome":"Strong"})
        blue=apply_creative_rgb(samples,{"color_chrome_fx_blue":"Strong"})
        self.assertLess(float(np.linalg.norm(chrome[0]-samples[0])),0.001)
        self.assertGreater(float(np.linalg.norm(chrome[1]-samples[1])),0.02)
        self.assertGreater(float(np.linalg.norm(blue[2]-samples[2])),float(np.linalg.norm(blue[1]-samples[1]))*3.0)

        neutrals=np.asarray([[0.08,0.08,0.08],[0.30,0.30,0.30],[0.72,0.72,0.72],[0.95,0.95,0.95]],dtype=np.float64)
        softened=apply_creative_rgb(neutrals,{"recipe_highlight":-2,"recipe_shadow":-1})
        self.assertGreater(float(softened[1].mean()),float(neutrals[1].mean()))
        self.assertLess(float(softened[2].mean()),float(neutrals[2].mean()))
        colored=apply_creative_rgb(samples,{"recipe_color":1})
        self.assertLess(float(np.linalg.norm(colored[0]-samples[0])),0.001)
        self.assertGreater(float(np.std(colored[1])),float(np.std(samples[1])))

        cube=creative_cube({"color_chrome":"Strong"},33)
        self.assertEqual(cube["size"],33);self.assertEqual(len(cube["values"]),33**3*3)
        self.assertTrue(str(cube["fingerprint"]).startswith("creative:"))

    def test_fuji_recipe_wb_directions_gamut_and_stack_order(self):
        self.assertEqual(normalize_recipe_wb({"red":99,"blue":-99}),{"red":9,"blue":-9})
        self.assertTrue(recipe_wb_is_neutral({}))
        samples=np.asarray([[0.0,0.0,0.0],[0.18,0.18,0.18],[0.50,0.50,0.50],[1.0,1.0,1.0]],dtype=np.float64)
        self.assertTrue(np.array_equal(apply_recipe_wb_rgb(samples,{}),samples))
        warm=apply_recipe_wb_rgb(samples,{"red":4,"blue":-5})
        self.assertGreater(float(warm[2,0]),float(warm[2,1]))
        self.assertGreater(float(warm[2,1]),float(warm[2,2]))
        self.assertTrue(np.allclose(warm[0],samples[0],atol=1e-9))
        self.assertTrue(np.allclose(warm[-1],samples[-1],atol=1e-9))
        self.assertTrue(np.all((warm>=0.0)&(warm<=1.0)))
        blue=recipe_wb_linear_gains({"red":0,"blue":9})
        self.assertGreater(float(blue[2]),float(blue[0]))
        # Empirical X-T1/Provia calibration anchors. These guard against the
        # former symmetric model, whose B+5 blue gain was 1.42 instead of the
        # measured effective 1.17.
        self.assertTrue(np.allclose(recipe_wb_linear_gains({"red":5,"blue":0}),[1.289562,0.968002,1.010467],atol=1e-6))
        self.assertTrue(np.allclose(recipe_wb_linear_gains({"red":-5,"blue":0}),[0.698804,1.037310,0.998874],atol=1e-6))
        self.assertTrue(np.allclose(recipe_wb_linear_gains({"red":0,"blue":5}),[1.001225,0.966940,1.168587],atol=1e-6))
        self.assertTrue(np.allclose(recipe_wb_linear_gains({"red":0,"blue":-5}),[1.002373,1.041436,0.765947],atol=1e-6))
        cube=recipe_wb_cube({"red":4,"blue":-5},33)
        self.assertEqual(cube["size"],33);self.assertEqual(len(cube["values"]),33**3*3)
        self.assertTrue(str(cube["fingerprint"]).startswith("recipe-wb:"))
        engine=CanonRenderEngine();user={"id":"user","cube":self.cube,"enabled":True,"opacity":1.0}
        effective=engine.effective_luts([user],{"recipe_wb":{"red":4,"blue":-5},"creative":{"recipe_color":1,"recipe_highlight":-1}})
        self.assertEqual([entry["id"] for entry in effective],["fuji-recipe-wb","recipe-color","user","creative-controls"])
        color_only=engine.effective_luts([user],{"creative":{"recipe_color":4}})
        self.assertEqual([entry["id"] for entry in color_only],["recipe-color","user"])

    def test_creative_controls_normalize_and_project_roundtrip(self):
        creative=normalize_creative_controls({
            "recipe_highlight":-9,"recipe_shadow":9,"recipe_color":1,
            "tone_curve":[-1,0.4,0.2,0.8,2],
            "color_axes":{"Blue":{"hue":99,"saturation":-99,"luminance":12}},
            "color_chrome":"strong","color_chrome_fx_blue":"invalid",
        })
        self.assertEqual(creative["tone_curve"],[0.0,0.4,0.4,0.8,1.0])
        self.assertEqual((creative["recipe_highlight"],creative["recipe_shadow"],creative["recipe_color"]),(-2,4,1))
        self.assertEqual(creative["color_axes"]["Blue"],{"hue":30,"saturation":-50,"luminance":12})
        self.assertEqual(creative["color_chrome"],"Strong");self.assertEqual(creative["color_chrome_fx_blue"],"Off")
        doc=ProjectDocument(name="Creative",edit={"creative":creative})
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"creative.canonstyleproject";save_project(path,doc);loaded=load_project(path)
        self.assertEqual(loaded.edit["creative"],creative);self.assertEqual(loaded.version,5)

    def test_canon33_lut_sizes_order_and_opacity(self):
        engine=CanonRenderEngine();n=17
        values=[]
        for b in range(n):
            for g in range(n):
                for r in range(n):
                    values.extend((r/(n-1),min(1.0,g/(n-1)*0.85+0.05),b/(n-1)))
        cube17={"size":17,"values":np.asarray(values,dtype=np.float32),"domain_min":[0,0,0],"domain_max":[1,1,1]}
        src=Image.fromarray(np.random.default_rng(19).integers(0,256,size=(71,93,3),dtype=np.uint8),"RGB")
        controls={"sharpness_override":False}
        a={"id":"17","cube":cube17,"enabled":True,"opacity":0.25}
        b={"id":"33","cube":self.cube,"enabled":True,"opacity":0.55}
        c={"id":"64","cube":self.hald,"enabled":True,"opacity":0.80}
        _,abc=engine.render_from_canon_base(src,[a,b,c],controls,"canon33")
        _,cba=engine.render_from_canon_base(src,[c,b,a],controls,"canon33")
        self.assertNotEqual(abc.tobytes(),cba.tobytes())
        _,full=engine.render_from_canon_base(src,[{**b,"opacity":1.0}],controls,"canon33")
        _,partial=engine.render_from_canon_base(src,[{**b,"opacity":0.2}],controls,"canon33")
        self.assertNotEqual(full.tobytes(),partial.tobytes())

    def test_fast_tungsten_preview_is_visibly_blue(self):
        src=Image.new("RGB",(64,64),(96,96,96))
        out=src.filter(make_wb_lut_from_kelvin(3200,5200))
        mean=np.asarray(out,dtype=np.float32).mean((0,1))
        self.assertGreater(mean[2]/mean[0],1.75)

    def test_wb_shift_directions_and_robust_eyedropper(self):
        gray=Image.new("RGB",(32,32),(120,120,120))
        amber=apply_linear_rgb_gains(gray,wb_shift_gains(9,0))
        blue=apply_linear_rgb_gains(gray,wb_shift_gains(-9,0))
        self.assertGreater(np.asarray(amber,dtype=np.float32).mean((0,1))[0],np.asarray(amber,dtype=np.float32).mean((0,1))[2])
        self.assertGreater(np.asarray(blue,dtype=np.float32).mean((0,1))[2],np.asarray(blue,dtype=np.float32).mean((0,1))[0])
        magenta=apply_linear_rgb_gains(gray,wb_shift_gains(0,9))
        mm=np.asarray(magenta,dtype=np.float32).mean((0,1))
        self.assertLess(mm[1],(mm[0]+mm[2])/2.0)

        rng=np.random.default_rng(42)
        patch=np.empty((41,41,3),dtype=np.int16);patch[:]=[170,125,90]
        patch+=rng.integers(-5,6,size=patch.shape,dtype=np.int16);patch=np.clip(patch,0,255).astype(np.uint8)
        patch[0:3,0:3]=255;patch[-3:,-3:]=0
        sampled=sample_custom_wb(Image.fromarray(patch,"RGB"),20,20,radius=16)
        corrected=apply_linear_rgb_gains(Image.fromarray(patch,"RGB"),sampled["mult"])
        mean=np.asarray(corrected,dtype=np.float32)[5:-5,5:-5].mean((0,1))
        self.assertLess(float(mean.max()-mean.min()),4.0)
        self.assertGreater(sampled["pixels"],500)

    def test_jpeg_and_tiff_decode(self):
        tif = RAW_ROOT / "canon_eos_rp_21.TIF"
        with tempfile.TemporaryDirectory() as td:
            sample=Image.new("RGB",(96,64),(80,120,160))
            jpg=Path(td)/"sample.jpg";local_tif=Path(td)/"sample.tif"
            sample.save(jpg,quality=90);sample.save(local_tif)
            for path in (jpg,local_tif):
                with Image.open(path) as im:im.load();self.assertEqual(im.size,(96,64))
        if tif.exists():
            with Image.open(tif) as im:
                im.load(); self.assertGreater(im.width * im.height, 0)
                im.thumbnail((640,640));small=im.convert("RGB")
            engine=CanonRenderEngine();controls={"contrast":1,"saturation":-1,"color_tone":1,"sharpness_override":False}
            dll=find_dll()
            if dll:
                inp,out=engine.render(small,dll,ensure_runtime_base_pf3(dll,"Neutral"),[],controls,"working",{},640)
                self.assertEqual(inp.size,out.size)
                self.assertNotEqual(inp.tobytes(),out.tobytes())

    def test_history_and_project_roundtrip(self):
        h = HistoryManager(); a = {"contrast": 0}; b = {"contrast": 2}
        h.reset(a); h.push(b)
        self.assertEqual(h.undo(), a); self.assertEqual(h.redo(), b)
        doc = ProjectDocument(name="Regression", edit={"contrast": 2,"base_name":"Standard","basePictureStyle":"Standard"}, snapshots={"A": a, "B": None, "C": None})
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "roundtrip.canonstyleproject"
            save_project(p, doc); loaded = load_project(p)
            self.assertEqual(loaded.to_dict(), doc.to_dict())
            self.assertEqual(loaded.edit["basePictureStyle"],"Standard")
            self.assertFalse(p.with_suffix(p.suffix+".tmp").exists())

    def test_portable_project_embeds_current_and_snapshot_luts_without_photos_or_paths(self):
        cube_text=("TITLE \"Portable test\"\nLUT_3D_SIZE 2\n"+
                   "\n".join(f"{r} {g} {b}" for b in (0,1) for g in (0,1) for r in (0,1))+"\n")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/"Filipe LUT ção.cube";source.write_text(cube_text,encoding="utf-8")
            hald=root/"look.png";Image.new("RGB",(8,8),(20,80,170)).save(hald)
            photo=root/"private portrait.CR3";photo.write_bytes(b"not embedded")
            current={"basePictureStyle":"Standard","base_path":r"X:\\private\\Standard.pf3",
                     "contrast":2,"saturation":-1,"color_tone":3,"raw_wb_mode":"Kelvin","raw_kelvin":4300,
                     "raw_exposure":1.25,"wb_ab_shift":-4,"wb_gm_shift":2,"custom_wb_mult":[1.2,1.0,.8],
                     "recipe_wb":{"red":4,"blue":-5},
                     "creative":normalize_creative_controls({"color_chrome_fx_blue":"Strong"}),"luts":[
                {"id":"cube","path":str(source),"enabled":True,"opacity":0.35,"metadata":{"preferredBaseStyle":"Standard"}},
                {"id":"hald","path":str(hald),"enabled":False,"opacity":0.8,"metadata":{}},
            ]}
            snapshot={"basePictureStyle":"Standard","luts":[
                {"id":"snap","path":str(source),"enabled":True,"opacity":1.0,"metadata":{}}
            ]}
            doc=ProjectDocument(name="Portable ção",edit=current,references=[str(photo)],current_reference=0,
                                zoom=2.0,pan_x=.31,pan_y=.72,snapshots={"A":snapshot,"B":None,"C":None})
            project=root/"portable.canonstyleproject";extract=root/"extracted"
            save_project(project,doc)
            self.assertTrue(zipfile.is_zipfile(project))
            with zipfile.ZipFile(project) as archive:
                names=archive.namelist();self.assertIn("project.json",names);self.assertIn("manifest.json",names)
                self.assertEqual(len([name for name in names if name.startswith("luts/")]),2)
                combined=archive.read("project.json")+archive.read("manifest.json")
                self.assertNotIn(b"X:\\\\private",combined);self.assertNotIn(photo.read_bytes(),combined)
                manifest=json.loads(archive.read("manifest.json"));self.assertFalse(manifest["photosEmbedded"])
                self.assertEqual(len(manifest["assets"]),2)
            source.unlink();hald.unlink()
            loaded=load_project(project,extraction_root=extract)
            self.assertEqual(loaded.name,"Portable ção");self.assertEqual(loaded.references,[])
            self.assertEqual(loaded.referenceHints[0]["name"],photo.name)
            self.assertEqual((loaded.zoom,loaded.pan_x,loaded.pan_y),(2.0,.31,.72))
            self.assertEqual([x["id"] for x in loaded.edit["luts"]],["cube","hald"])
            self.assertEqual(loaded.edit["luts"][0]["opacity"],.35)
            self.assertFalse(loaded.edit["luts"][1]["enabled"])
            for key in ("contrast","saturation","color_tone","raw_wb_mode","raw_kelvin","raw_exposure","wb_ab_shift","wb_gm_shift","custom_wb_mult","recipe_wb","creative"):
                self.assertEqual(loaded.edit[key],current[key],key)
            restored=[Path(x["path"]) for x in loaded.edit["luts"]]
            self.assertTrue(all(path.is_file() for path in restored))
            self.assertEqual(Path(loaded.snapshots["A"]["luts"][0]["path"]),restored[0])
            self.assertEqual(hashlib.sha256(restored[0].read_bytes()).hexdigest(),manifest["assets"][0]["sha256"])

    def test_portable_project_rejects_tampering_and_legacy_json_still_loads(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);legacy=root/"legacy.canonstyleproject"
            legacy.write_text(json.dumps({"version":4,"name":"Legacy","edit":{"contrast":2}}),encoding="utf-8")
            loaded=load_project(legacy,extraction_root=root/"extract")
            self.assertEqual(loaded.name,"Legacy");self.assertEqual(loaded.edit["contrast"],2)

            bad=root/"tampered.canonstyleproject";payload=b"changed lut"
            manifest={"format":"canon-style-studio-portable-project","formatVersion":1,"projectVersion":5,
                      "photosEmbedded":False,"assets":[{"sha256":"0"*64,"size":len(payload),"name":"x.cube","archivePath":"luts/x.cube"}]}
            project={"version":5,"name":"Bad","edit":{"luts":[{"path":"","portableAsset":"0"*64}]}}
            with zipfile.ZipFile(bad,"w") as archive:
                archive.writestr("project.json",json.dumps(project));archive.writestr("manifest.json",json.dumps(manifest));archive.writestr("luts/x.cube",payload)
            with self.assertRaisesRegex(ValueError,"SHA-256"):
                load_project(bad,extraction_root=root/"extract")

            slip=root/"slip.canonstyleproject"
            with zipfile.ZipFile(slip,"w") as archive:
                archive.writestr("project.json","{}");archive.writestr("manifest.json","{}");archive.writestr("../escape.cube",b"x")
            with self.assertRaisesRegex(ValueError,"unsafe"):
                load_project(slip,extraction_root=root/"extract")

            imported=root/"imported.canonstyleproject"
            save_project(imported,ProjectDocument(edit={"base_name":"Imported PF3","basePictureStyle":"Imported PF3",
                                                        "base_path":r"X:\\private\\base.pf3","custom_pf3":r"X:\\private\\look.pf3","luts":[]}))
            imported_doc=load_project(imported,extraction_root=root/"extract")
            self.assertEqual(imported_doc.edit["basePictureStyle"],"Neutral")
            self.assertEqual(imported_doc.edit["portableOriginalBasePictureStyle"],"Imported PF3")
            self.assertTrue(imported_doc.portableWarnings)
            self.assertEqual(imported_doc.edit["custom_pf3"],"")

    def test_oriented_native_raw_geometry(self):
        self.assertEqual(oriented_native_size((3132,2090),{"visible_size":(6264,4180)}),(6264,4180))
        self.assertEqual(oriented_native_size((2010,3012),{"visible_size":(6024,4020)}),(4020,6024))

    def test_pf3_export(self):
        dll = find_dll()
        if not dll:
            self.skipTest("Canon EdsCFParse.dll unavailable")
        controls = {"contrast": 1, "saturation": -1, "color_tone": 2,
                    "sharpness_override": True, "sharp_strength": 5, "fineness": 3, "threshold": 2}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "regression.pf3"
            size, _ = export_pf3(dll, ensure_runtime_base_pf3(dll,"Neutral"), out, [], controls, "Regression")
            self.assertEqual(size, 434511)
            basic = inspect_pf3(dll, out)["basic"]
            for key in ("contrast", "saturation", "color_tone", "sharp_strength", "fineness", "threshold"):
                self.assertEqual(basic[key], controls[key])

    def test_lut_stack_canon33_matches_exported_pf3_table(self):
        dll=find_dll()
        if not dll:self.skipTest("Canon EdsCFParse.dll unavailable")
        engine=CanonRenderEngine();layers=[
            {"id":"superia-a","cube":self.cube,"enabled":True,"opacity":0.35},
            {"id":"hald-b","cube":self.hald,"enabled":True,"opacity":0.60},
        ]
        controls={"contrast":0,"saturation":0,"color_tone":0,"sharpness_override":False,
                  "recipe_wb":{"red":4,"blue":-5},
                  "creative":{"recipe_highlight":-2,"recipe_shadow":-1,"recipe_color":1,"tone_curve":[0.0,0.20,0.48,0.82,1.0],"color_axes":{"Red":{"hue":8,"saturation":12,"luminance":-5}},"color_chrome":"Weak","color_chrome_fx_blue":"Strong"}}
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"stack_regression.pf3"
            validated=resolve_validated_base_pf3(dll,"Standard",[HERE/"bases"])
            base_path=validated["path"] if validated else ensure_runtime_base_pf3(dll,"Standard")
            export_pf3(dll,base_path,out,layers,controls,"Stack Regression")
            exported_lut=canon_table_to_pillow_lut(inspect_pf3(dll,out)["table"])
            # Dense deterministic RGB grid exposes ordering, opacity and 12-bit
            # quantization mistakes much better than a single photograph.
            vals=np.linspace(0,255,19,dtype=np.uint8)
            rgb=np.asarray([(r,g,b) for b in vals for g in vals for r in vals],dtype=np.uint8).reshape(19,361,3)
            src=Image.fromarray(rgb,"RGB")
            base=src.filter(engine.load_base(dll,base_path)["lut"])
            expected=base.filter(engine.quantized_stack_lut(engine.effective_luts(layers,controls)))
            actual=src.filter(exported_lut)
            mae=np.abs(np.asarray(expected,dtype=np.int16)-np.asarray(actual,dtype=np.int16)).mean()
            self.assertLess(float(mae),1.25)

    def test_pse_runtime_profile_and_report_privacy(self):
        install=discover_pse()
        if install:
            profile=ensure_runtime_input_profile(install)
            data=profile.read_bytes()
            self.assertEqual(data[36:40],b"acsp")
            self.assertEqual(data[48:52],b"CANO")
        with tempfile.TemporaryDirectory() as td:
            report=Path(td)/"report.zip"
            create_test_report_zip(report,{"path":str(Path.home()/"private"/"image.CR3")},{"wb":"Tungsten"})
            self.assertTrue(validate_test_report_zip(report))
            import zipfile
            with zipfile.ZipFile(report) as archive:
                names=archive.namelist();payload=b"".join(archive.read(n) for n in names)
            self.assertFalse(any(n.lower().endswith((".cr2",".cr3")) for n in names))
            self.assertNotIn((os.environ.get("USERNAME") or "__NO_USER__").encode().lower(),payload.lower())


class CanonRawRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = RAW_ROOT / "canon_eos_rp_03.cr3"
        if not cls.raw.exists():
            raise unittest.SkipTest("Canon RAW samples unavailable")
        cls.temp = tempfile.TemporaryDirectory()
        cls.client = DppBackendClient(HERE / "canon_dpp_worker.py", Path(cls.temp.name) / "cache")
        cls.base = {"wb": "Daylight", "kelvin": 5200, "exposure": 0, "contrast": 0,
                    "saturation": 0, "color_tone": 0, "sharp_strength": 0, "fineness": 2, "threshold": 4}

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "client"): cls.client.close()
        if hasattr(cls, "temp"): cls.temp.cleanup()

    def render(self, **changes):
        settings = {**self.base, "style": "Neutral", **changes}
        return self.client.render(self.raw, settings, 600, 400)

    def test_cancel_obsolete_render_and_recover(self):
        settings={**self.base,"style":"Neutral","exposure":0.314159}
        box={}
        def work():
            try:self.client.render(self.raw,settings,1620,1080);box["completed"]=True
            except Exception as e:box["error"]=str(e)
        thread=threading.Thread(target=work);thread.start();deadline=time.time()+3.0
        while self.client._inflight_cmd!="render" and time.time()<deadline:time.sleep(0.005)
        cancelled=self.client.cancel_active_render();thread.join(10)
        self.assertTrue(cancelled);self.assertFalse(thread.is_alive());self.assertIn("cancelled",box.get("error",""))
        recovered,_=self.client.render(self.raw,{**settings,"exposure":0.271828},300,200)
        self.assertEqual(recovered.size,(300,200))

    def test_fixed_wb_tungsten_is_strongly_blue(self):
        daylight, _ = self.render(wb="Daylight")
        tungsten, _ = self.render(wb="Tungsten")
        d = np.asarray(daylight, dtype=np.float32).mean((0, 1))
        t = np.asarray(tungsten, dtype=np.float32).mean((0, 1))
        self.assertGreater(t[2] / t[0], (d[2] / d[0]) * 1.5)

    def test_all_fixed_white_balance_modes_change_pixels(self):
        baseline,_=self.render(wb="As Shot")
        base=np.asarray(baseline,dtype=np.int16)
        fixed=("Daylight","Shade","Cloudy","Tungsten","White Fluorescent","Flash","Kelvin")
        signatures={}
        for mode in fixed:
            image,_=self.render(wb=mode,kelvin=4700 if mode=="Kelvin" else 5200)
            arr=np.asarray(image,dtype=np.int16)
            mae=float(np.abs(arr-base).mean())
            self.assertGreater(mae,0.12,mode)
            signatures[mode]=hashlib.sha256(arr.tobytes()).digest()
        self.assertNotEqual(signatures["Daylight"],signatures["Kelvin"])
        self.assertNotEqual(signatures["Tungsten"],signatures["White Fluorescent"])
        # Cloudy and Flash intentionally map to the same documented 6000 K
        # target; identical pixels are valid for those two labels.
        self.assertGreaterEqual(len(set(signatures.values())),6)
        # Auto modes depend on camera metadata and may legitimately coincide with
        # As Shot, but both paths must render successfully and deterministically.
        for mode in ("Auto — Ambience","Auto — White"):
            first,_=self.render(wb=mode);second,_=self.render(wb=mode)
            self.assertEqual(first.tobytes(),second.tobytes(),mode)

    def test_all_picture_styles_are_distinct(self):
        hashes = set()
        for style in ("Standard", "Portrait", "Landscape", "Neutral", "Faithful", "Fine Detail"):
            im, _ = self.render(style=style)
            hashes.add(hashlib.sha256(im.tobytes()).digest())
        self.assertEqual(len(hashes), 6)

    def test_saturation_and_color_tone_are_not_swapped(self):
        baseline,_=self.render();sat,_=self.render(saturation=4);tone,_=self.render(color_tone=4)
        values=[np.asarray(image.convert("HSV"),dtype=np.float32) for image in (baseline,sat,tone)]
        mask=values[0][...,1]>30
        sat_delta=float((values[1][...,1]-values[0][...,1])[mask].mean())
        tone_sat_delta=float(abs((values[2][...,1]-values[0][...,1])[mask].mean()))
        def hue_delta(candidate):
            delta=np.abs(candidate[...,0]-values[0][...,0]);return float(np.minimum(delta,256-delta)[mask].mean())
        self.assertGreater(sat_delta,20.0)
        self.assertGreater(sat_delta,tone_sat_delta*5.0)
        self.assertGreater(hue_delta(values[2]),hue_delta(values[1]))

    def test_develop_cache(self):
        self.render(style="Faithful")
        _, info = self.render(style="Faithful")
        self.assertTrue(info.get("cached"))
        self.assertTrue(info.get("memory_cached"))

    def test_chrome_controls_change_real_canon_pixels_and_strength(self):
        canon,_=self.render(style="Standard")
        engine=CanonRenderEngine();base={"sharpness_override":False}
        _,neutral=engine.render_from_canon_base(canon,[],{**base,"creative":{}},"working")
        reference=np.asarray(neutral,dtype=np.int16)
        metrics={}
        for control in ("color_chrome","color_chrome_fx_blue"):
            for level in ("Weak","Strong"):
                _,image=engine.render_from_canon_base(canon,[],{**base,"creative":{control:level}},"working")
                delta=np.abs(np.asarray(image,dtype=np.int16)-reference)
                metrics[(control,level)]=(float(delta.mean()),float(np.mean(np.any(delta>0,axis=2))*100.0))
            self.assertGreater(metrics[(control,"Weak")][0],0.04,control)
            self.assertGreater(metrics[(control,"Weak")][1],2.0,control)
            self.assertGreater(metrics[(control,"Strong")][0],metrics[(control,"Weak")][0]*1.65,control)

    def test_fresh_worker_is_warmed_and_rgb_ipc_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            client=DppBackendClient(HERE/"canon_dpp_worker.py",Path(td)/"cache")
            settings={**self.base,"style":"Portrait","wb":"Tungsten","exposure":0.37,
                      "contrast":2,"saturation":-1,"color_tone":1,"probe_nonce":1}
            try:
                first,_=client.render(self.raw,settings,900,600)
                second,_=client.render(self.raw,{**settings,"probe_nonce":2},900,600)
                self.assertEqual(first.tobytes(),second.tobytes())
                cache_files=list((Path(td)/"cache").glob("render_*.rgb"))
                self.assertEqual(len(cache_files),2)
                self.assertTrue(all(p.stat().st_size==900*600*3 for p in cache_files))
                self.assertFalse(list((Path(td)/"cache").glob("render_*.png")))
            finally:client.close()

    def test_unicode_worker_cache_path(self):
        with tempfile.TemporaryDirectory() as td:
            cache=Path(td)/"Utilizador João Silva"/"cache"
            client=DppBackendClient(HERE/"canon_dpp_worker.py",cache)
            try:
                image,_=client.render(self.raw,{**self.base,"style":"Standard","saturation":1},300,200)
                self.assertEqual(image.size,(300,200))
                self.assertTrue(list(cache.glob("render_*.rgb")))
                self.assertFalse((Path(td)/"Utilizador JoÃ£o Silva").exists())
            finally:client.close()

    def test_native_wb_shift_axes(self):
        blue,_=self.render(wb_ab_shift=-9,wb_gm_shift=0)
        amber,_=self.render(wb_ab_shift=9,wb_gm_shift=0)
        b=np.asarray(blue,dtype=np.float32).mean((0,1));a=np.asarray(amber,dtype=np.float32).mean((0,1))
        self.assertGreater(a[0]/a[2],(b[0]/b[2])*1.18)
        green,_=self.render(wb_ab_shift=0,wb_gm_shift=-9)
        magenta,_=self.render(wb_ab_shift=0,wb_gm_shift=9)
        g=np.asarray(green,dtype=np.float32).mean((0,1));m=np.asarray(magenta,dtype=np.float32).mean((0,1))
        self.assertLess(m[1]/((m[0]+m[2])/2.0),g[1]/((g[0]+g[2])/2.0)*0.90)

    def test_landscape_and_portrait_geometry(self):
        landscape,_=self.client.render(self.raw,{**self.base,"style":"Neutral"},600,400)
        self.assertEqual(landscape.size,(600,400))
        native_landscape,_=self.client.render(self.raw,{**self.base,"style":"Neutral"},6264,4180)
        self.assertEqual(native_landscape.size,(6264,4180))
        portrait=RAW_ROOT/"IMG_2748.CR3"
        if not portrait.exists():self.skipTest("Portrait RAW sample unavailable")
        # Above the validated canvas DPP4Lib returns success but the pixels are
        # stretched garbage. The worker must reject that request and the app uses
        # the fitted Canon portrait frame while retaining native logical geometry.
        reference=load_reference_image(portrait,"As Shot",0)[0]
        requested=fit_size_within_box((4020,6024),1080,1620)
        vertical,_=self.client.render(portrait,{**self.base,"style":"Neutral"},*requested)
        self.assertEqual(vertical.size,requested)
        self.assertGreater(vertical.height,vertical.width)
        references=[reference] if reference.height>reference.width else [
            reference.transpose(Image.Transpose.ROTATE_90),
            reference.transpose(Image.Transpose.ROTATE_270),
        ]
        self.assertGreater(max(luminance_structure_correlation(item,vertical) for item in references),0.65)
        with self.assertRaisesRegex(DppBackendError,"Unsafe DPP4Lib portrait output"):
            self.client.render(portrait,{**self.base,"style":"Neutral"},4020,6024)


if __name__ == "__main__":
    unittest.main(verbosity=2)
