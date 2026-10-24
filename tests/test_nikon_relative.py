import unittest
from concurrent.futures import CancelledError
import numpy as np
from nikon_conversion.relative import relative_coordinates,sample_grid
from nikon_conversion.prepare import neutral_style
from nikon_np3 import NP3Style


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


if __name__=='__main__':unittest.main()
