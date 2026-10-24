import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from nikon_profile_data import decode_profile,load_conversion_profile


def encoded_record(identifier,plain,alias=0,packed=None,length=None):
    if packed is None:
        compressed=zlib.compress(plain);state=0x10dcd;packed=bytearray()
        for value in compressed:
            state=(state*0x6c078965+1)&0xffffffff
            packed.append(value^((state>>13)&255))
    return struct.pack('<8I',0x1002,identifier,alias,3,len(packed),len(plain) if length is None else length,0,0)+packed


def container(*records):return b'NKON\x00\x00\x01\x01'+bytes(24)+b''.join(records)


class NikonProfileDataTests(unittest.TestCase):
    def test_decode_and_alias_use_only_synthetic_data(self):
        data=container(encoded_record(1,b'profile'),encoded_record(1072,b'',alias=1))
        self.assertEqual(decode_profile(data,1072),b'profile')

    def test_rejects_invalid_record_geometry_aliases_and_compression(self):
        record=encoded_record(1072,b'profile')
        invalid=(b'',container(record[:-1]),container(record,record),
            container(encoded_record(1072,b'',alias=1072)),
            container(encoded_record(1072,b'profile',length=3)),
            container(encoded_record(1072,b'',packed=b'bad')),
            container(encoded_record(1072,b'',packed=bytes(1),length=17*1024*1024)))
        for data in invalid:
            with self.subTest(bytes=len(data)),self.assertRaises(ValueError):decode_profile(data,1072)
        with self.assertRaises(ValueError):decode_profile(container(record),2)

    def test_local_loader_rejects_unvalidated_profile_and_preserves_file(self):
        data=container(encoded_record(1072,b'synthetic profile'))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'prm.bin';path.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'not been validated'):load_conversion_profile(path)
            self.assertEqual(path.read_bytes(),data)
            with self.assertRaises(FileNotFoundError):load_conversion_profile(Path(directory)/'missing.bin')


if __name__=='__main__':unittest.main()
