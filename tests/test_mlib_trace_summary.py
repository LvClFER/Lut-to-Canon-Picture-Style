import unittest
from camera_install.mlib_trace_summary import summarize


class SummaryTests(unittest.TestCase):
    def test_every_case_retained_and_no_physical_claim(self):
        def row(model):
            return {"model": model, "cameraId": 1, "payloadSize": 16752,
                    "mlibCalls": {"counts": {"converter": 2}, "captures": [
                        {"callers": {"MLib.dll+0x19795": 3}}]}}
        result = summarize({"files": [row("A"), row("B"), {"model": "C", "cameraId": 2, "error": "rc80"}]})
        self.assertEqual(result["cases"], 3)
        self.assertEqual(result["successfulCases"], 2)
        self.assertEqual(result["failedCases"], 1)
        self.assertEqual(len(result["routes"]), 1)
        self.assertEqual(result["routes"][0]["curveCallers"]["MLib.dll+0x19795"], 6)
        self.assertFalse(result["physicalCompatibilityEstablished"])
