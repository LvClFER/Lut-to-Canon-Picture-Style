import struct
import unittest
from camera_install.icc_profile_reference import inspect_profile, inspect_lut16, encode_observed_lab16


def synthetic_profile():
    lut = bytearray(52 + 3*2*2 + 2**3*3*2 + 3*2*2)
    lut[:4] = b'mft2'
    lut[8:11] = bytes((3,3,2))
    struct.pack_into('>HH', lut, 48, 2, 2)
    data = bytearray(156 + len(lut))
    struct.pack_into('>I', data, 0, len(data))
    data[12:24] = b'scnrRGB Lab '
    data[36:40] = b'acsp'
    struct.pack_into('>I', data, 128, 2)
    for index, name in enumerate((b'A2B0',b'A2B1')):
        struct.pack_into('>4sII',data,132+12*index,name,156,len(lut))
    data[156:] = lut
    return bytes(data)


class ICCReferenceTests(unittest.TestCase):
    def test_observed_lab_encoding_endpoints_and_clamps(self):
        self.assertEqual(encode_observed_lab16(0,0,0),bytes.fromhex('000080008000'))
        self.assertEqual(encode_observed_lab16(100,0,0),bytes.fromhex('ffff80008000'))
        self.assertEqual(encode_observed_lab16(-1,-129,129),bytes.fromhex('00000000ffff'))
        self.assertEqual(encode_observed_lab16(101,129,-129),bytes.fromhex('ffffffff0000'))

    def test_observed_lab_encoding_fractional_truncation(self):
        self.assertEqual(struct.unpack('>3H',encode_observed_lab16(50,0.5,-0.5)),(32767,32896,32640))
        self.assertEqual(struct.unpack('>3H',encode_observed_lab16(0,0.001,-0.001)),(0,32768,32767))
        for value in (True,float('nan'),float('inf'),'0'):
            with self.assertRaises(ValueError):encode_observed_lab16(value,0,0)
    def test_shared_tag_and_geometry(self):
        report = inspect_profile(synthetic_profile())
        self.assertEqual(report['inputColorSpace'],'RGB ')
        self.assertEqual(report['connectionSpace'],'Lab ')
        self.assertEqual(report['tags'][0]['sha256'],report['tags'][1]['sha256'])
        self.assertEqual(report['tags'][0]['lut16']['clutSize'],48)

    def test_three_intent_tags_share_exact_payload(self):
        original=synthetic_profile()
        payload=original[156:]
        data=bytearray(168+len(payload))
        data[:128]=original[:128]
        struct.pack_into('>I',data,0,len(data))
        struct.pack_into('>I',data,128,3)
        for index,name in enumerate((b'A2B0',b'A2B1',b'A2B2')):
            struct.pack_into('>4sII',data,132+12*index,name,168,len(payload))
        data[168:]=payload
        report=inspect_profile(bytes(data))
        self.assertEqual([t['signature'] for t in report['tags']],['A2B0','A2B1','A2B2'])
        self.assertEqual(len({(t['offset'],t['size'],t['sha256']) for t in report['tags']}),1)

    def test_shared_payload_does_not_allow_duplicate_signature(self):
        data=bytearray(synthetic_profile())
        data[144:148]=b'A2B0'
        with self.assertRaisesRegex(ValueError,'duplicate signature'):
            inspect_profile(bytes(data))

    def test_tag_lookup_is_independent_of_table_order(self):
        data=synthetic_profile()
        reversed_table=data[:132]+data[144:156]+data[132:144]+data[156:]
        before=inspect_profile(data)
        after=inspect_profile(reversed_table)
        self.assertEqual([t['signature'] for t in after['tags']],['A2B1','A2B0'])
        self.assertEqual({t['signature']:t for t in before['tags']},
                         {t['signature']:t for t in after['tags']})

    def test_payload_relocation_preserves_tag_data(self):
        original=synthetic_profile()
        data=bytearray(original[:156]+bytes(4)+original[156:])
        struct.pack_into('>I',data,0,len(data))
        for index in range(2):
            struct.pack_into('>I',data,132+12*index+4,160)
        before=inspect_profile(original)
        after=inspect_profile(bytes(data))
        for left,right in zip(before['tags'],after['tags']):
            self.assertEqual(right['offset'],left['offset']+4)
            self.assertEqual(right['sha256'],left['sha256'])
            self.assertEqual(right['lut16'],left['lut16'])

    def test_relocation_requires_updating_each_shared_tag(self):
        original=synthetic_profile()
        data=bytearray(original[:156]+bytes(4)+original[156:])
        struct.pack_into('>I',data,0,len(data))
        struct.pack_into('>I',data,136,160)
        with self.assertRaisesRegex(ValueError,'overlapping'):
            inspect_profile(bytes(data))

    def test_envelope_and_tag_bounds(self):
        for offset,value in ((0,0),(128,100),(136,155),(140,1000000),(148,160)):
            data=bytearray(synthetic_profile());struct.pack_into('>I',data,offset,value)
            with self.assertRaises(ValueError):inspect_profile(bytes(data))
        with self.assertRaises(ValueError):inspect_profile(b'')

    def test_lut_size_and_dimensions(self):
        original=synthetic_profile()[156:]
        for offset,value in ((8,0),(9,0),(10,1),(11,1),(49,0)):
            data=bytearray(original);data[offset]=value
            with self.assertRaises(ValueError):inspect_lut16(bytes(data))
        with self.assertRaises(ValueError):inspect_lut16(original[:-1])

    def test_lut_zero_alignment_padding(self):
        data=bytearray(240);data[:4]=b'mft2';data[8:11]=bytes((3,3,3))
        struct.pack_into('>HH',data,48,2,2)
        self.assertEqual(inspect_lut16(bytes(data))['paddingBytes'],2)
        self.assertEqual(inspect_lut16(bytes(data[:-2]))['paddingBytes'],0)
        data[-1]=1
        with self.assertRaises(ValueError):inspect_lut16(bytes(data))

    def test_curve_linearity_not_assumed(self):
        data=bytearray(synthetic_profile()[156:])
        report=inspect_lut16(bytes(data))
        self.assertEqual(report['linearInputCurves'],[False]*3)
        for offset in (52,56,60,112,116,120):
            struct.pack_into('>HH',data,offset,0,65535)
        report=inspect_lut16(bytes(data))
        self.assertEqual(report['linearInputCurves'],[True]*3)
        self.assertEqual(report['linearOutputCurves'],[True]*3)
