import unittest
from camera_install.legacy_metadata_reference import extract_opaque_record,verify_seed_influence


class LegacyMetadataTests(unittest.TestCase):
    def test_two_observed_geometries(self):
        for size,offset in ((8164,76),(8168,332)):
            zero=bytes(size)
            ff=zero[:offset]+bytes([255])*1460+zero[offset+1460:]
            proof=verify_seed_influence(zero,ff)
            self.assertEqual(proof['offset'],offset)
            self.assertFalse(proof['cameraInstallValidated'])
            self.assertEqual(len(extract_opaque_record(ff)[1]),1460)

    def test_unknown_geometry_and_non_seed(self):
        for size in (0,1460,8163,8165,16744):
            with self.assertRaises(ValueError): extract_opaque_record(bytes(size))
        with self.assertRaises(ValueError): verify_seed_influence(bytes(8164),bytes(8164))

    def test_outside_mutation_and_mismatch(self):
        zero=bytes(8164);offset=76
        ff=bytearray(zero[:offset]+bytes([255])*1460+zero[offset+1460:])
        ff[-1]=1
        with self.assertRaises(ValueError): verify_seed_influence(zero,ff)
        with self.assertRaises(ValueError): verify_seed_influence(zero,bytes(8168))
