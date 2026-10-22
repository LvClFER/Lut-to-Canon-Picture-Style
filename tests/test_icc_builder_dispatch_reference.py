import struct
import itertools
import unittest
from camera_install.icc_builder_dispatch_reference import inspect_dispatch, decode_mode_one_grid, sample_mode_one_grid, split_mode_two_records
from camera_install.icc_builder_dispatch_reference import mode_two_consumer_plan


class ICCBuilderDispatchTests(unittest.TestCase):
    def test_mode_two_kind_gates_and_order(self):
        for selector in (0,1,2,3,0xffffffff):
            for first,axis,second in itertools.product((None,0,1,2,3),repeat=3):
                plan=mode_two_consumer_plan(selector,first,axis,second)
                order=plan['operations']
                self.assertEqual(plan['numericMode'],11 if selector==2 else 10)
                self.assertEqual('first-selective' in order,first==1)
                self.assertEqual('companion-axis' in order,axis==2)
                self.assertEqual('second-selective' in order,second==1)
                self.assertEqual('fixed-roundtrip-10-to-11' in order,selector!=2)
                self.assertEqual('fixed-roundtrip-11-to-10' in order,selector!=2)
                if axis==2 and selector!=2:
                    self.assertLess(order.index('fixed-roundtrip-10-to-11'),order.index('companion-axis'))
                    self.assertLess(order.index('companion-axis'),order.index('fixed-roundtrip-11-to-10'))
                self.assertEqual(order[-2:],('rgb-clamp','floating-color'))

    def test_mode_two_plan_rejects_ambiguous_words(self):
        for invalid in (None,True,-1,2**32,1.0,'2'):
            with self.assertRaises(ValueError):mode_two_consumer_plan(invalid)
        for invalid in (True,-1,2**32,1.0):
            with self.assertRaises(ValueError):mode_two_consumer_plan(1,invalid)

    def test_mode_zero_and_unknown(self):
        self.assertEqual(inspect_dispatch(struct.pack('<I', 0))['entry'], '0x4720')
        self.assertIsNone(inspect_dispatch(struct.pack('<I', 3))['entry'])

    def test_mode_one_routes_and_header_checks(self):
        for nodes, entry, accepted, step in ((0,'0x5930',False,None),
                (8,'0x5930',False,None),(9,'0x5930',True,40),
                (10,'0x5930',True,32),(11,'0x6260',True,102),
                (33,'0x6260',True,32),(0xffffffff,'0x6260',True,0)):
            result = inspect_dispatch(struct.pack('<5I',1,7,3,nodes,99))
            self.assertEqual((result['entry'],result['entryHeaderAccepted'],result['localStep']),
                             (entry,accepted,step))
            self.assertEqual((result['field4'],result['field16']),(7,99))
        self.assertFalse(inspect_dispatch(struct.pack('<5I',1,0,4,33,0))['entryHeaderAccepted'])

    def test_mode_two_count_branches(self):
        for prefix,total,route in ((4,3,'null'),(0,3,'unsplit'),(3,3,'unsplit'),
                                   (1,3,'split'),(-1,3,'split'),(-2,-3,'null')):
            data=bytearray(0xf14)
            struct.pack_into('<I',data,0,2)
            struct.pack_into('<i',data,0x47c,prefix)
            struct.pack_into('<i',data,0xf0c,total)
            struct.pack_into('<I',data,0xf10,5)
            result=inspect_dispatch(bytes(data))
            self.assertEqual(result['route'],route)
            self.assertEqual(result['recordWidth'],5)
            self.assertEqual(result['thirdCurveGroupOffset'],0x25c)
            self.assertEqual(result['matrixOffset'],0x388)

    def test_mode_two_full_record_split(self):
        for prefix in (0,1,3):
            data=bytearray(0xf10)
            struct.pack_into('<I',data,0,2)
            struct.pack_into('<i',data,0x47c,prefix)
            struct.pack_into('<2I',data,0xf08,7,3)
            records=[struct.pack('<I',2)+bytes([index+1])*32 for index in range(3)]
            data.extend(b''.join(records))
            parts=split_mode_two_records(bytes(data))
            if prefix in (0,3):self.assertEqual(parts,(struct.pack('<2I',7,3)+b''.join(records),))
            else:self.assertEqual(parts,(struct.pack('<2I',7,1)+records[0],struct.pack('<2I',7,2)+b''.join(records[1:])))
            for invalid in (bytes(data[:-1]),bytes(data)+b'\0'):
                with self.assertRaises(ValueError):split_mode_two_records(invalid)
            struct.pack_into('<I',data,0xf10+36,1)
            with self.assertRaises(ValueError):split_mode_two_records(bytes(data))

    def test_reject_truncated_or_mutable_inputs(self):
        for data in (b'',bytearray(4),None,struct.pack('<I',1),struct.pack('<I',2)):
            with self.assertRaises(ValueError):inspect_dispatch(data)

    def test_planar_unsigned_grid(self):
        count=9**3
        planes=list(range(count))+[0x80000000+i for i in range(count)]+[0xffffffff]*count
        raw=struct.pack('<5I',1,0,3,9,0)+struct.pack(f'<{3*count}I',*planes)
        decoded=decode_mode_one_grid(raw)
        for node in (0,1,8,9,80,81,count-1):
            self.assertEqual(decoded[node],(node,0x80000000+node,0xffffffff))
        for invalid in (raw[:-1],raw+b'\0',struct.pack('<5I',1,0,3,34,0),
                        struct.pack('<5I',1,0,2,9,0),struct.pack('<I',0)):
            with self.assertRaises(ValueError):decode_mode_one_grid(invalid)

    def test_sampler_affine_all_orders_and_ties(self):
        nodes=9
        values=[(r*64+g*32+b*16)+(channel*0x80000000 if channel<2 else 100)
                for channel in range(3) for r in range(nodes) for g in range(nodes) for b in range(nodes)]
        data=struct.pack('<5I',1,0,3,nodes,0)+struct.pack(f'<{len(values)}I',*values)
        for xyz in list(itertools.permutations((1.25,2.5,3.75)))+[(1.5,2.5,3.5),(0.,0.,0.)]:
            base=xyz[0]*64+xyz[1]*32+xyz[2]*16
            self.assertEqual(sample_mode_one_grid(data,xyz),(base,base+0x80000000,base+100))

    def test_sampler_rejects_unproved_endpoints(self):
        data=struct.pack('<5I',1,0,3,9,0)+bytes(12*9**3)
        for xyz in ((8,0,0),(-1,0,0),(float('nan'),0,0),(True,0,0),(0,0)):
            with self.assertRaises(ValueError):sample_mode_one_grid(data,xyz)

    def test_explicit_endpoint_policy(self):
        nodes=9
        values=[r*64+g*32+b*16+channel*100 for channel in range(3)
                for r in range(nodes) for g in range(nodes) for b in range(nodes)]
        data=struct.pack('<5I',1,0,3,nodes,0)+struct.pack(f'<{len(values)}I',*values)
        for xyz in list(itertools.product((0.,8.),repeat=3))+[(8.,1.5,2.5),(8.,8.,2.5)]:
            base=xyz[0]*64+xyz[1]*32+xyz[2]*16
            self.assertEqual(sample_mode_one_grid(data,xyz,allow_endpoints=True),(base,base+100,base+200))
        for policy in (1,None,'true'):
            with self.assertRaises(ValueError):sample_mode_one_grid(data,(0,0,0),allow_endpoints=policy)
