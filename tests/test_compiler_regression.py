import struct
import hashlib
import copy
import unittest

from camera_install.compiler_regression import decode, full33_planar, recheck_historical_reference, ten_node_reference_order, merge_reference_proof


class CompilerRegressionTests(unittest.TestCase):
    def test_full33_channels_and_endpoints(self):
        count = 33 ** 3
        raw = struct.pack("<3H", 0, 2048, 4095) * count
        result = struct.unpack(f"<{count * 3}H", full33_planar(raw))
        self.assertEqual(set(result[:count]), {0})
        self.assertEqual(set(result[count:2 * count]), {16388})
        self.assertEqual(set(result[2 * count:]), {32768})

    def test_rejects_wrong_size(self):
        with self.assertRaises(ValueError):
            full33_planar(b"\0" * 6)

    def test_rejects_non_12_bit_values(self):
        raw = struct.pack("<H", 4096) + bytes(33 ** 3 * 6 - 2)
        with self.assertRaises(ValueError):
            full33_planar(raw)

    def test_cipher_round_trip(self):
        keys = (bytes(range(256)) * 2, bytes(range(256)) * 2 + b"\x01")
        raw = bytes(range(256)) * 32
        for seed in (0xB8ED, 0x33137):
            self.assertEqual(decode(decode(raw, keys, seed), keys, seed), raw)

    def test_cipher_rejects_bad_key_size(self):
        with self.assertRaises(ValueError):
            decode(b"test", (b"", b""))

    def test_historical_reference_keeps_numeric_limitation_explicit(self):
        row = {"vector": "test", "ok": False, "sha256": "abc", "namePreserved": True,
               "transport": {"stale": {"staleBlocked": True}},
               "tables": {"method": "independent-compact-grid-reference", "exactTables": [True, False]}}
        report = recheck_historical_reference({"rows": [row]}, {"test": {"sha256": "abc"}})
        self.assertTrue(row["ok"])
        self.assertFalse(row["tables"]["allNumericTablesChecked"])
        self.assertEqual(report["summary"]["numericSecondGridUnresolved"], 1)

    def test_missing_historical_reference_does_not_pass(self):
        row = {"vector": "missing", "ok": False, "namePreserved": True,
               "transport": {"stale": {"staleBlocked": True}},
               "tables": {"method": "independent-compact-grid-reference", "exactTables": [True, False]}}
        recheck_historical_reference({"rows": [row]}, {})
        self.assertFalse(row["ok"])

    def test_reference_order_comparison_does_not_modify_payload(self):
        reference = bytes(368) + b"a" * 8192 + b"b" * 8192
        opposite = bytes(368) + b"b" * 8192 + b"a" * 8192
        digest = hashlib.sha256(reference).hexdigest()
        self.assertEqual(ten_node_reference_order(reference, digest), [1, 2])
        self.assertEqual(ten_node_reference_order(opposite, digest), [2, 1])
        self.assertEqual(opposite[368], ord("b"))
        self.assertIsNone(ten_node_reference_order(opposite[:-1], digest))
        self.assertIsNone(ten_node_reference_order(opposite[:-1] + b"c", digest))

    def test_reference_proof_requires_matching_context_and_bytes(self):
        row = {"cameraId": 1, "vector": "test", "ok": False, "sha256": "bytes",
               "sourcePf3Sha256": "source", "namePreserved": True,
               "transport": {"stale": {"staleBlocked": True}}, "tables": {}}
        report = {"descriptorSha256": "descriptor", "dllSha256": "dll",
                  "productionAgentSha256": "agent", "rows": [row]}
        proof = copy.deepcopy(report)
        proof["rows"][0].update(ok=True, tables={"independentResearchOutputExact": True})
        self.assertEqual(merge_reference_proof(copy.deepcopy(report), proof)["summary"]["passed"], 1)
        wrong_context = copy.deepcopy(proof)
        wrong_context["dllSha256"] = "other"
        with self.assertRaises(ValueError):
            merge_reference_proof(copy.deepcopy(report), wrong_context)
        wrong_bytes = copy.deepcopy(proof)
        wrong_bytes["rows"][0]["sha256"] = "different"
        with self.assertRaises(ValueError):
            merge_reference_proof(copy.deepcopy(report), wrong_bytes)


if __name__ == "__main__":
    unittest.main()
