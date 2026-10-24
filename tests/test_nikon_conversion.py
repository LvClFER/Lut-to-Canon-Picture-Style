from concurrent.futures import CancelledError
import struct
import unittest
from unittest.mock import patch
from nikon_conversion import compile_cube


def document():
    records=((0x100,b'0310'),(0x200,b'Synthetic'+bytes(11)),(0x300,b'\0 '))
    return b'NCP\0'+b''.join(struct.pack('>II',tag,len(value))+value for tag,value in records)+bytes(4)


class NikonConversionTests(unittest.TestCase):
    def test_grid_order_progress_and_normalization_without_profile_assets(self):
        progress=[]
        with patch('nikon_conversion.load_conversion_profile',return_value=b'profile') as load, \
                patch('nikon_conversion.prepare_grid',return_value={}), \
                patch('nikon_conversion.grid_point',side_effect=lambda p,n,f,m,k:[v*65280/(n-1) for v in p]):
            cube=compile_cube(document(),'local-prm.bin',17,progress.append)
        load.assert_called_once_with('local-prm.bin')
        self.assertEqual(cube['title'],'Synthetic')
        self.assertEqual(len(cube['values']),17**3*3)
        for r,g,b in ((0,0,0),(16,0,0),(0,16,0),(0,0,16),(7,9,11),(16,16,16)):
            offset=((b*17+g)*17+r)*3
            self.assertEqual(cube['values'][offset:offset+3],[r/16,g/16,b/16])
        self.assertEqual(progress[0],0);self.assertEqual(progress[-1],100)
        self.assertEqual(progress,sorted(progress))

    def test_invalid_input_and_early_cancel_do_not_open_profile(self):
        with patch('nikon_conversion.load_conversion_profile') as load:
            with self.assertRaises(ValueError):compile_cube(document(),'missing',2)
            with self.assertRaises(ValueError):compile_cube(b'invalid','missing')
            with self.assertRaises(CancelledError):compile_cube(document(),'missing',cancel=lambda:True)
        load.assert_not_called()

    def test_nonlinear_device_base_is_not_applied_a_second_time(self):
        def point(coordinates,size,flags,mode,configuration):
            gain=.5 if configuration['look'] else 1
            return [(v/(size-1))**2*gain*65280 for v in coordinates]
        with patch('nikon_conversion.load_conversion_profile',return_value=b'profile'), \
                patch('nikon_conversion.prepare_grid',side_effect=[{'look':True},{'look':False}]), \
                patch('nikon_conversion.grid_point',side_effect=point):
            cube=compile_cube(document(),'local',17)
        for r,g,b in ((0,0,0),(7,9,11),(16,16,16)):
            offset=((b*17+g)*17+r)*3
            for actual,expected in zip(cube['values'][offset:offset+3],(r/32,g/32,b/32)):
                self.assertAlmostEqual(actual,expected,delta=.002)

    def test_cancel_during_conversion_returns_no_partial_cube(self):
        with patch('nikon_conversion.load_conversion_profile',return_value=b'profile'), \
                patch('nikon_conversion.prepare_grid',return_value={}), \
                patch('nikon_conversion.grid_point',return_value=[0,0,0]) as point:
            with self.assertRaises(CancelledError):
                compile_cube(document(),'local',17,cancel=unittest.mock.Mock(side_effect=[False,False,True]))
            self.assertEqual(point.call_count,17)


if __name__=='__main__':unittest.main()
