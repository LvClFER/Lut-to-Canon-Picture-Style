import random
import struct
import subprocess
import sys
import unittest

from camera_install.cipher_stream_reference import decode
from camera_install.identity_pf3_bootstrap_reference import recover_identity_calibration, recover_known_fields_calibration, _rectangle
from camera_install.pf3_source_reference import read_source_fields, write_source_fields


class IdentityBootstrapTests(unittest.TestCase):
    def test_caller_owned_records_recover_without_an_identity_table_or_fixed_offset(self):
        known = {0x1020: (2, random.Random(513).randbytes(2500))}
        for seed, padding in ((21, 37), (33, 1501)):
            keys = self.keys(seed)
            fields = {0x1002: (2, b'N'*padding), **known, 0x1070: (3, b'\0\0'*100)}
            raw = write_source_fields(fields, keys)
            recovered = recover_known_fields_calibration(raw, known)
            self.assertEqual(read_source_fields(raw, recovered), fields)
            with self.assertRaises(ValueError):
                recover_identity_calibration(raw)

    def test_known_record_prefix_is_insufficient_and_short_records_fail(self):
        known = {0x1020: (2, random.Random(514).randbytes(2500))}
        changed = dict(known)
        changed[0x1020] = (2, known[0x1020][1][:-1] + bytes([known[0x1020][1][-1] ^ 1]))
        with self.assertRaises(ValueError):
            recover_known_fields_calibration(write_source_fields(changed, self.keys(22)), known)
        with self.assertRaisesRegex(ValueError, '2048'):
            recover_known_fields_calibration(b'', {0x1020: (2, b'x')})

    @staticmethod
    def keys(seed):
        rng = random.Random(seed)
        return (rng.randbytes(512), rng.randbytes(513))

    @staticmethod
    def identity():
        axis = [round(i * 4095 / 32) for i in range(33)]
        words = [12, 3, 33]
        words.extend(value for r in axis for g in axis for b in axis for value in (r, g, b))
        return struct.pack('>' + 'H' * len(words), *words)

    @staticmethod
    def wrap(records, keys):
        body = b''.join(struct.pack('>HHI', identifier, kind, len(data)) + data
                        for identifier, kind, data in records)
        body += struct.pack('>HHII', 0xfffe, 4, 4, sum(body) & 0xffffffff)
        body += struct.pack('>HHI', 0xffff, 0xffff, 0)
        raw = bytes.fromhex('0000300050535000') + struct.pack('>I', len(body)) + decode(body, keys, 12)
        return raw

    def test_rectangle_cancels_random_stream_at_different_seeds(self):
        rng = random.Random(503)
        plain = rng.randbytes(4096)
        for seed in (0, 12, 877):
            self.assertEqual(_rectangle(plain), _rectangle(decode(plain, self.keys(seed), seed)))

    def test_single_identity_bootstraps_at_unannounced_offsets_and_both_record_ids(self):
        identity = self.identity()
        for seed, padding, identifier in ((1, 7, 0x1070), (2, 1501, 0x1071)):
            keys = self.keys(seed)
            records = [(0x1009, 3, struct.pack('>H', 0x84)),
                       (0x1002, 2, b'N' * padding), (identifier, 3, identity)]
            raw = self.wrap(records, keys)
            recovered = recover_identity_calibration(raw)
            self.assertEqual(recovered[0][0], 0)
            self.assertEqual(decode(raw[12:], recovered, 12), decode(raw[12:], keys, 12))
            self.assertEqual(read_source_fields(raw, recovered), read_source_fields(raw, keys))

    def test_two_identity_candidates_resolve_to_same_equivalent_tables(self):
        raw = self.wrap([(0x1070, 3, self.identity()), (0x1071, 3, self.identity())], self.keys(4))
        recovered = recover_identity_calibration(raw)
        self.assertEqual(decode(raw[12:], recovered, 12), decode(raw[12:], self.keys(4), 12))

    def test_known_prefix_or_wrong_record_is_not_a_calibration(self):
        identity = self.identity()
        changed = bytearray(identity)
        changed[-2:] = struct.pack('>H', 2048)
        keys = self.keys(6)
        for records in ([(0x1070, 3, bytes(changed))], [(0x1020, 3, identity)],
                        [(0x1070, 2, identity)]):
            with self.assertRaises(ValueError):
                recover_identity_calibration(self.wrap(records, keys))

    def test_bad_checksum_envelope_and_nonidentity_fail(self):
        raw = self.wrap([(0x1070, 3, self.identity())], self.keys(9))
        broken = raw[:-16] + bytes([raw[-16] ^ 1]) + raw[-15:]
        for value in (bytearray(raw), raw[:-1], bytes(8) + raw[8:], broken,
                      self.wrap([(0x1070, 3, bytes(215628))], self.keys(9))):
            with self.assertRaises(ValueError):
                recover_identity_calibration(value)

    def test_bootstrap_imports_no_native_solver_or_device_modules(self):
        script = '''
import builtins
original = builtins.__import__
forbidden = {'camera_install.compiler_regression', 'camera_install.virtual_compatibility',
             'camera_install.wpd_connection', 'frida', 'z3', 'numpy'}
def guarded(name, globals=None, locals=None, fromlist=(), level=0):
    package = (globals or {}).get('__package__', '')
    resolved = package + '.' + name if level else name
    if resolved in forbidden:
        raise RuntimeError('Forbidden dependency: ' + resolved)
    return original(name, globals, locals, fromlist, level)
builtins.__import__ = guarded
from test_identity_pf3_bootstrap_reference import IdentityBootstrapTests
IdentityBootstrapTests().test_two_identity_candidates_resolve_to_same_equivalent_tables()
IdentityBootstrapTests().test_caller_owned_records_recover_without_an_identity_table_or_fixed_offset()
'''
        result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
