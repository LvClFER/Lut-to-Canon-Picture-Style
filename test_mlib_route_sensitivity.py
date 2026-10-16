import unittest
from camera_install.mlib_route_sensitivity import summarize_sensitivity


class SensitivityTests(unittest.TestCase):
    def test_unchanged_and_failure_not_conflated(self):
        common = {"model": "test", "cameraId": 1}
        report = summarize_sensitivity({"files": [
            dict(common, source="01_IDENTITY.pf3", payloadSha256="a", payloadSize=16744),
            dict(common, source="curve.pf3", payloadSha256="a", payloadSize=16744),
            dict(common, source="bad.pf3", error="rc80")]})
        variants = report["models"][0]["variants"]
        self.assertTrue(variants[0]["compiled"])
        self.assertFalse(variants[0]["payloadChanged"])
        self.assertFalse(variants[1]["compiled"])
        self.assertFalse(report["physicalCompatibilityEstablished"])
