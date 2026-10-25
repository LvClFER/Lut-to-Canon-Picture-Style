import unittest
import numpy as np
from creative_controls import apply_creative_rgb, linear_to_srgb


class RecipeToneTests(unittest.TestCase):
    def test_tone_controls_are_monotonic_and_only_affect_their_half(self):
        x=np.linspace(0,1,4097)
        rgb=np.repeat(x[:,None],3,axis=1)
        join=float(linear_to_srgb(np.asarray(.5**3)))
        for control in ('recipe_highlight','recipe_shadow'):
            for level in (-2,-1,1,2,3,4):
                y=apply_creative_rgb(rgb,{control:level})[:,0]
                self.assertTrue(np.all(np.diff(y)>=-1e-7),(control,level))
                unaffected=x<join if control=='recipe_highlight' else x>join
                np.testing.assert_allclose(y[unaffected],x[unaffected],atol=2e-6)
                difference=y-x
                affected=~unaffected
                direction=level if control=='recipe_highlight' else -level
                self.assertGreater(direction*float(difference[affected].sum()),0)
                np.testing.assert_allclose(y[[0,-1]],[0,1],atol=2e-6)

    def test_midtones_have_no_slope_jump_at_extreme_settings(self):
        join=float(linear_to_srgb(np.asarray(.5**3)))
        x=join+np.array([-.001,-.0005,0,.0005,.001])
        rgb=np.repeat(x[:,None],3,axis=1)
        for control in ('recipe_highlight','recipe_shadow'):
            for level in (-2,4):
                y=apply_creative_rgb(rgb,{control:level})[:,0]
                np.testing.assert_allclose(np.diff(y)/np.diff(x),1,atol=.03)

    def test_neutral_remains_exact(self):
        rgb=np.random.default_rng(42).random((100,3))
        np.testing.assert_array_equal(apply_creative_rgb(rgb,{'recipe_highlight':0,'recipe_shadow':0}),rgb)


if __name__=='__main__':unittest.main()
