import struct,unittest
from camera_install.packed10_reference import pack10_integer,unpack10_integer,packed_index


class UnpackTests(unittest.TestCase):
    def test_signed_boundaries_and_full_grid_roundtrip(self):
        values=[i%1024 for i in range(1000)]
        edges=(-512,-1,0,1,511)
        values += [edges[i%5] for i in range(1000)]
        values += [edges[(i+2)%5] for i in range(1000)]
        self.assertEqual(unpack10_integer(pack10_integer(values)),values)

    def test_unused_slots_and_high_bits_do_not_change_samples(self):
        used={packed_index(r,g,b) for r in range(10) for g in range(10) for b in range(10)}
        words=[0xc0000000 if i in used else 0xffffffff for i in range(1024)]
        self.assertEqual(unpack10_integer(struct.pack('<1024I',*words)),[0]*3000)

    def test_size_and_type_are_strict(self):
        for data in (bytes(4095),bytes(4097),None,bytearray(4096)):
            with self.assertRaises(ValueError):unpack10_integer(data)
