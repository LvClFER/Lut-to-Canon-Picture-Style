import math
import struct
import unittest
from camera_install.default_axis_reference import sector_weights,adjustments,transform


class DefaultAxisTests(unittest.TestCase):
    def test_centres_and_boundaries(self):
        for axis in range(6):
            weights = sector_weights(axis)
            self.assertEqual(weights[axis],1)
            boundary = sector_weights(axis+.5)
            self.assertAlmostEqual(boundary[axis],.5)
            self.assertAlmostEqual(boundary[(axis+1)%6],.5)

    def test_transition_matches_observed_weight(self):
        self.assertAlmostEqual(sector_weights(1/3)[0],.7837623544704053,places=14)

    def test_periodicity_and_partition(self):
        for hue in (-.25,0,.2,.7,5.8,6,6.1):
            weights = sector_weights(hue)
            self.assertAlmostEqual(sum(weights),1)
            self.assertTrue(all(0<=w<=1 for w in weights))
            for a,b in zip(weights,sector_weights(hue+6)): self.assertAlmostEqual(a,b,places=14)

    def test_negative_and_positive_saturation_differ(self):
        positive = [(0,10,0)]+[(0,0,0)]*5
        negative = [(0,-50,0)]+[(0,0,0)]*5
        for a,b in zip(transform([.8,.2,.2],positive),[.89,.11,.11]): self.assertAlmostEqual(a,b,places=14)
        for a,b in zip(transform([.8,.2,.2],negative),[.65,.35,.35]): self.assertAlmostEqual(a,b,places=14)

    def groups(self):
        return [struct.pack('<21i',5,0,i*60,50,50,1,(i*60-30)%360,0,0,2,
                            (i*60+30)%360,100,100,3,10,-20,5,5,20,0,0) for i in range(6)]

    def test_geometry_checked_and_adjustments_decoded(self):
        self.assertEqual(adjustments(self.groups()),[(10,-20,5)]*6)
        groups = self.groups(); modified = list(struct.unpack('<21i',groups[0])); modified[18]=30
        groups[0]=struct.pack('<21i',*modified)
        with self.assertRaises(ValueError): adjustments(groups)

    def test_bad_triplet_layout(self):
        with self.assertRaises(ValueError): transform([.8,.2,.2],[(0,0,0)])

    def test_native_transition_endpoint(self):
        # colorsys normalizes hue through 0..1 and changes the final bit,
        # crossing the native strict branch at the 10-degree endpoint.
        actual = transform([.8,.2,.4],[(10,10,10)]+[(0,0,0)]*5,10)
        for a,b in zip(actual,[.9434,.1166,.2544]):
            self.assertAlmostEqual(a,b,places=14)
