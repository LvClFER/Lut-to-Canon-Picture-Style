import unittest
from unittest.mock import patch
from camera_install.compact_carrier_reference import compact_upstream_grid,build_observed_compact16752_pixel,build_observed_compact16752


class CompactCarrierTests(unittest.TestCase):
    def test_explicit_route_validation_precedes_processing(self):
        for paths in (None,['pixel']*4,('pixel',)*3,('pixel',)*5,('integer',)*4):
            with self.assertRaises(ValueError):
                build_observed_compact16752({},None,None,block_paths=paths,pixel_scale=256,internal_selector=0)
        for selector in (True,-1,0x100000000,1.0):
            with self.assertRaises(ValueError):
                build_observed_compact16752({},None,None,block_paths=('cache',)*4,pixel_scale=256,internal_selector=selector)

    def test_cache_blocks_use_source_pair_and_id_policy_without_pixel_calls(self):
        module='camera_install.compact_carrier_reference.'
        fields={0x1009:(0,(0x84).to_bytes(4,'little')),0x1070:(0,b'first'),0x1071:(0,b'second')}
        with patch(module+'build_control_plain',return_value=bytes(8)),patch(module+'decode',side_effect=lambda data,keys,seed:data),patch(module+'build_compact16752_prefix',return_value=bytes(368)),patch(module+'build_compact_cache',side_effect=[bytes([i])*4096 for i in (1,2,1,2)]) as cache,patch(module+'compact_upstream_grid') as grid:
            output=build_observed_compact16752(fields,None,None,block_paths=('cache',)*4,pixel_scale=256,internal_selector=0x80000169)
        self.assertEqual(len(output),16752)
        self.assertEqual(output[368:8560],output[8560:])
        self.assertEqual([call.args[0] for call in cache.call_args_list],[b'first',b'second']*2)
        self.assertTrue(all(call.kwargs==dict(grid_flag=0,coefficient_mode=True) for call in cache.call_args_list))
        grid.assert_not_called()

    def test_unobserved_scale_rejected_before_processing(self):
        for scale in (254,257,True,255.0,None):
            with self.assertRaises(ValueError):
                build_observed_compact16752_pixel({},bytes(14796),None,pixel_scale=scale)

    def test_descriptor_and_index_are_explicitly_bounded(self):
        for descriptor in (bytes(7492),bytes(14795),bytes(14797),None):
            with self.assertRaises(ValueError):compact_upstream_grid(descriptor,0x84,0)
        for index in (-1,4,True,1.0):
            with self.assertRaises(ValueError):compact_upstream_grid(bytes(14796),0x84,index)

    def test_unknown_style_rejected_even_for_parameterless_pair(self):
        for index in range(4):
            with self.assertRaises(ValueError):compact_upstream_grid(bytes(14796),0x86,index)
