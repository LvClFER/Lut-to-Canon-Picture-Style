import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from canon_engine import CanonRenderEngine, CubeSampler, parse_cube
from creative_controls import DEFAULT_GRADING, apply_creative_rgb, normalize_creative_controls
from project_state import ProjectDocument, save_project, load_project


class LutGeneratorTests(unittest.TestCase):
    def test_neutral_preserves_existing_pixels_and_each_control_changes_the_look(self):
        samples=np.array([[.12,.12,.12],[.3,.4,.55],[.65,.2,.12],[.8,.85,.7]])
        self.assertTrue(np.array_equal(apply_creative_rgb(samples),samples))
        for key in DEFAULT_GRADING:
            with self.subTest(control=key):
                result=apply_creative_rgb(samples,{'grading':{key:45}})
                self.assertGreater(float(np.max(np.abs(result-samples))),.005)
                self.assertTrue(np.all(np.isfinite(result)))
                self.assertTrue(np.all((result>=0)&(result<=1)))

    def test_extremes_remain_finite_and_project_roundtrip_preserves_grading(self):
        samples=np.random.default_rng(0).random((200,3))
        for value in (-100,100):
            creative=normalize_creative_controls({'grading':dict.fromkeys(DEFAULT_GRADING,value)})
            result=apply_creative_rgb(samples,creative)
            self.assertTrue(np.all(np.isfinite(result)))
            self.assertTrue(np.all((result>=0)&(result<=1)))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'look.canonstyleproject'
            save_project(path,ProjectDocument(edit={'creative':creative}))
            self.assertEqual(load_project(path).edit['creative'],creative)

    def test_export_sizes_identity_channel_order_and_title_sanitization(self):
        with tempfile.TemporaryDirectory() as directory:
            for size in (17,33,65):
                path=Path(directory)/f'look-{size}.cube'
                CanonRenderEngine().export_cube(path,[],{},size,'Look"\nLUT_3D_SIZE 2')
                cube=parse_cube(path);self.assertEqual(cube['size'],size)
                self.assertEqual(sum(line.startswith('LUT_3D_SIZE ') for line in path.read_text().splitlines()),1)
                sampler=CubeSampler(cube)
                np.testing.assert_allclose(sampler.sample(.12,.4,.85),[.12,.4,.85],atol=1e-6)

    def test_export_matches_generated_colour_lut_and_preserves_existing_file_on_failure(self):
        controls={'creative':{'grading':{'red_gamma':35,'toe':25,'density':20}}}
        engine=CanonRenderEngine()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'look.cube'
            engine.export_cube(path,[],controls,17)
            output=CubeSampler(parse_cube(path))
            expected=CubeSampler(engine.effective_luts([],controls)[0]['cube'])
            for rgb in ((.25,.5,.75),(.5,.25,.125),(0,0,0),(1,1,1)):
                np.testing.assert_allclose(output.sample(*rgb),expected.sample(*rgb),atol=1e-6)
            previous=path.read_bytes()
            with patch('canon_engine.os.replace',side_effect=OSError('disk unavailable')):
                with self.assertRaises(OSError):engine.export_cube(path,[],{},17)
            self.assertEqual(path.read_bytes(),previous)
            self.assertEqual(list(Path(directory).glob('*.tmp')),[])
            with self.assertRaises(ValueError):engine.export_cube(path,[],{},32)

    def test_export_respects_disabled_luts_strength_and_basic_controls(self):
        values=np.tile([1.,0.,0.],8)
        red=dict(size=2,values=values,domain_min=[0,0,0],domain_max=[1,1,1],title='Red')
        engine=CanonRenderEngine()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'look.cube'
            entries=[dict(cube=red,enabled=False,opacity=1),dict(cube=red,enabled=True,opacity=.5)]
            engine.export_cube(path,entries,{},17)
            np.testing.assert_allclose(CubeSampler(parse_cube(path)).sample(.25,.5,.75),[.625,.25,.375],atol=1e-6)
            engine.export_cube(path,[],{'saturation':-4},17)
            self.assertLess(CubeSampler(parse_cube(path)).sample(1,0,0)[0],1)


if __name__=='__main__':unittest.main()
