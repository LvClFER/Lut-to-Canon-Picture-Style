import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from camera_install.virtual_compatibility import classify, compile_vector, load_models, summarize


class VirtualCompatibilityTests(unittest.TestCase):
    def test_proxy_dependency_is_not_reported_as_universal_success(self):
        result = summarize([
            {"cameraId": 1, "model": "A", "descriptor": "old", "descriptorSha256": "old", "classification": "blocked"},
            {"cameraId": 1, "model": "A", "descriptor": "new", "descriptorSha256": "new", "classification": "compiler-validated"},
            {"cameraId": 2, "model": "B", "descriptor": "new", "descriptorSha256": "new", "classification": "blocked"},
        ])
        self.assertEqual(result["testedModels"], 2)
        self.assertEqual(result["modelsPassingAtLeastOneProxyDescriptor"], 1)
        self.assertEqual(result["modelsBlockedWithAllTestedDescriptors"], ["B"])

    def test_matrix_filters_non_eos_and_deduplicates_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "models.json"
            path.write_text(json.dumps({"descriptors": {"proxy": {"models": [
                {"cameraIdHex": "0x80000433", "model": "RP", "scope": "EOS"},
                {"cameraIdHex": "0x80000433", "model": "RP", "scope": "EOS"},
                {"cameraIdHex": "0x123", "model": "compact", "scope": "compact"},
            ]}}}), encoding="utf-8")
            self.assertEqual(load_models(path), [{"cameraId": 0x80000433, "model": "RP"}])

    def test_acceptance_alone_cannot_hide_ignored_look(self):
        vectors = {name: {"validated": True, "size": 16752, "sha256": "same"}
                   for name in ("identity", "look")}
        self.assertEqual(classify(vectors), "look-ignored")
        vectors["look"]["sha256"] = "different"
        self.assertEqual(classify(vectors), "compiler-validated")
        vectors["look"]["size"] = 83076
        self.assertEqual(classify(vectors), "inconsistent-output-size")
        vectors["look"]["validated"] = False
        self.assertEqual(classify(vectors), "blocked")

    def test_attach_failure_does_not_leave_host_running(self):
        device = Mock()
        device.spawn.return_value = 123
        device.attach.side_effect = RuntimeError("attach failed")
        result = compile_vector(device, Path("host"), Path("dll"), "agent",
                                Path("look.pf3"), {"cameraId": 1}, b"descriptor")
        self.assertFalse(result["validated"])
        device.kill.assert_called_once_with(123)

    def test_host_start_failure_is_recorded_without_aborting_matrix(self):
        device = Mock()
        device.spawn.side_effect = RuntimeError("host unavailable")
        result = compile_vector(device, Path("host"), Path("dll"), "agent",
                                Path("look.pf3"), {"cameraId": 1}, b"descriptor")
        self.assertEqual(result["error"], "host unavailable")
        self.assertFalse(result["validated"])
        device.kill.assert_not_called()

    def test_failed_compiler_result_is_never_validated(self):
        device = Mock()
        loader, agent = Mock(), Mock()
        device.attach.return_value.create_script.side_effect = [loader, agent]
        agent.exports_sync.testnativecompile.return_value = (
            {"ok": False, "acceptanceHook": {"ok": True}}, b"payload",
        )
        result = compile_vector(device, Path("host"), Path("dll"), "source",
                                Path("look.pf3"), {"cameraId": 0x80000433}, b"descriptor")
        self.assertFalse(result["validated"])
        self.assertEqual(agent.exports_sync.testnativecompile.call_args.args[2], "33040080")
        agent.unload.assert_called_once()
        loader.unload.assert_called_once()
        device.attach.return_value.detach.assert_called_once()
        device.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
