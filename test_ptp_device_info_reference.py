import struct
import unittest
from camera_install.ptp_device_info_reference import decode


def string(value):
    raw=value.encode('utf-16-le')+b'\0\0'
    return bytes([len(raw)//2])+raw

def dataset():
    data=struct.pack('<HIH',100,11,100)+string('Canon')+struct.pack('<H',0)
    for items in ((0x1001,0x9127,0x9189),(0xc189,),(0xd163,0xd170),(),(0x3801,)):
        data+=struct.pack('<I',len(items))+struct.pack('<'+'H'*len(items),*items)
    return data+b''.join(string(s) for s in ('Canon','Synthetic Câmara','1.0','private-serial'))


class DeviceInfoTests(unittest.TestCase):
    def test_capabilities_and_non_ascii(self):
        info=decode(dataset())
        self.assertEqual(info.operations,(0x1001,0x9127,0x9189))
        self.assertEqual(info.model,'Synthetic Câmara')
        self.assertNotIn('private-serial',repr(info))
    def test_every_truncation_and_extra_bytes(self):
        data=dataset()
        for size in range(len(data)):
            with self.assertRaises(ValueError): decode(data[:size])
        with self.assertRaises(ValueError): decode(data+b'x')
    def test_array_bound_before_allocation(self):
        data=struct.pack('<HIH',100,11,100)+b'\0'+struct.pack('<HI',0,0xffffffff)
        with self.assertRaisesRegex(ValueError,'array'): decode(data)
    def test_unterminated_string(self):
        data=bytearray(dataset());data[-1]=1
        with self.assertRaisesRegex(ValueError,'Unterminated'): decode(data)
