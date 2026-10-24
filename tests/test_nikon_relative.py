import unittest
from concurrent.futures import CancelledError
import numpy as np
from nikon_conversion.relative import relative_coordinates,sample_grid,regularize_values
from nikon_conversion.prepare import neutral_style
from nikon_np3 import NP3Style
from nikon_conversion.grid import grid_rgb,grid_encode


class NikonRelativeTests(unittest.TestCase):
    def setUp(self):
        b,g,r=np.meshgrid(*([np.linspace(0,1,5)]*3),indexing='ij')
        self.target=np.stack((r,g,b),axis=-1)

    def test_clipped_device_base_has_bounded_finite_coordinates(self):
        base=np.clip(self.target*1.4-.1,0,1)
        actual=relative_coordinates(base,5,5)
        self.assertTrue(np.all((actual>=0)&(actual<=4095)))

    def test_device_base_is_removed_before_look_is_applied(self):
        base=self.target**2
        coordinates=relative_coordinates(base,5,5)
        np.testing.assert_allclose(sample_grid(base,coordinates/4095),self.target,atol=.002)

    def test_cancel_and_nonfinite_input(self):
        with self.assertRaises(CancelledError):relative_coordinates(self.target,5,5,cancel=lambda:True)
        invalid=self.target.copy();invalid[0,0,0,0]=np.nan
        with self.assertRaises(ValueError):relative_coordinates(invalid,5,5)

    def test_neutral_controls_are_independent_of_original_recipe(self):
        style=neutral_style(NP3Style('Any',((0x300,b'\0 '),(2,b'custom tone'))))
        self.assertEqual(style.color_values,(0,)*39+(50,0))
        self.assertIsNone(style.block(2))

    def test_extended_rgb_retains_information_until_final_encoding(self):
        values=[2048,2047,-2048]
        extended=grid_rgb(values)
        self.assertLess(min(extended),0);self.assertGreater(max(extended),1)
        encoded=grid_encode(values,1,0,[0]*9)
        self.assertEqual(encoded,[int(np.floor(np.clip(v,0,1)*65280+.5)) for v in extended])

    def test_wide_gamut_inverse_has_no_isolated_coordinate_jumps(self):
        matrix=np.array([[1.5,-.25,-.25],[-.25,1.5,-.25],[-.25,-.25,1.5]])
        base=self.target@matrix.T
        coordinates=relative_coordinates(base,5,17)/4095
        b,g,r=np.meshgrid(*([np.linspace(0,1,17)]*3),indexing='ij')
        target=np.stack((r,g,b),axis=-1)
        np.testing.assert_allclose(coordinates@matrix.T,target,atol=.001)
        self.assertLess(max(float(np.abs(np.diff(coordinates,axis=i)).max()) for i in range(3)),.05)

    def test_colour_regularization_preserves_affine_looks_and_endpoints(self):
        affine=self.target*.8+.1
        actual=np.asarray(regularize_values(affine,5)).reshape(affine.shape)
        np.testing.assert_allclose(actual,affine,atol=1e-14)

    def test_colour_regularization_removes_isolated_grid_spikes(self):
        damaged=self.target.copy();damaged[2,2,2,0]+=.3
        repaired=np.asarray(regularize_values(damaged,5)).reshape(damaged.shape)
        self.assertLess(repaired[2,2,2,0]-.5,.04)
        self.assertGreater(repaired[2,2,2,0],.5)
        self.assertTrue(np.all((repaired>=0)&(repaired<=1)))
        damaged[0,0,0,0]=np.nan
        with self.assertRaises(ValueError):regularize_values(damaged,5)


if __name__=='__main__':unittest.main()
