import unittest

from camera_install.descriptor_read_reference import length_guard_rejects, verify_observation


class DescriptorReadReferenceTests(unittest.TestCase):
    def test_observed_geometries(self):
        self.assertTrue(length_guard_rejects(7492, 14796, 65535))
        self.assertFalse(length_guard_rejects(14796, 14796, 65535))
        self.assertFalse(length_guard_rejects(14796, 7492, 65535))

    def test_type_two_exception_and_unknown_later_failure(self):
        self.assertFalse(length_guard_rejects(1, 2, 2))
        self.assertFalse(verify_observation(dict(storedLength=14796,
            requestedLength=14796, storageType=65535, succeeded=False))['lengthGuardRejects'])

    def test_contradictions_and_invalid_fields(self):
        with self.assertRaises(ValueError):
            verify_observation(dict(storedLength=7492, requestedLength=14796,
                                    storageType=65535, succeeded=True))
        for value in (-1, 2**32, True, '7492'):
            with self.assertRaises(ValueError):
                length_guard_rejects(value, 14796, 65535)
