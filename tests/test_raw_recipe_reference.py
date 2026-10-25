import unittest

from camera_install.raw_recipe_reference import chroma_from_rgb16,rgb16_from_ycbcr,sample_tone64,scale_channel_q10,auxiliary_luma_bin


class RawRecipeReferenceTests(unittest.TestCase):
    def test_model_tone_style_indices(self):
        from camera_install.raw_recipe_reference import model_tone_style_index
        for style,index in ((0x21,7),(0x22,7),(0x23,7),(0x81,0),(0x82,1),
                            (0x83,2),(0x84,3),(0x85,4),(0x86,5),(0x87,0),(0x88,3),(0xff,8)):
            self.assertEqual(model_tone_style_index(style),index)
        for invalid in (0,-1,0x89,0x100,0xffffffff,True,129.0):
            with self.assertRaises(ValueError):model_tone_style_index(invalid)

    def test_model_tone_record_endianness_scaling_and_bounds(self):
        import struct
        from camera_install.raw_recipe_reference import decode_model_tone_record
        record=struct.pack('>15H',3,9,3,0,2048,4095,0,1000,4095,4095,0,4095,0,5,100)
        descriptor,consumed=decode_model_tone_record(record,7,True)
        self.assertEqual(consumed,len(record))
        self.assertEqual(struct.unpack_from('<3H',descriptor,6),(0,8193,16383))
        self.assertEqual(struct.unpack_from('<3H',descriptor,134),(0,4000,16383))
        self.assertEqual(struct.unpack_from('<6H',descriptor,262),(4095,0,4095,0,7,400))
        self.assertEqual(descriptor[12:134],bytes(122))
        record=struct.pack('>14H',2,10,2,0,16383,0,16383,16383,0,16383,0,0,1200,123)
        descriptor,consumed=decode_model_tone_record(record+b'extra',1,True)
        self.assertEqual(consumed,len(record))
        self.assertEqual(struct.unpack_from('<6H',descriptor,262),(4095,0,4095,0,1,1200))
        self.assertEqual(struct.unpack_from('<2H',descriptor,6),(0,16383))
        descriptor,_=decode_model_tone_record(record,1,False)
        self.assertEqual(struct.unpack_from('<H',descriptor,262),(16383,))
        for bad in (b'',record[:5],record[:-1],struct.pack('>3H',65,9,65),struct.pack('>3H',2,9,3)):
            with self.assertRaises(ValueError):decode_model_tone_record(bad,1,True)
        with self.assertRaises(ValueError):decode_model_tone_record(record,True,True)
        with self.assertRaises(ValueError):decode_model_tone_record(record,1,1)

    def test_vector_auxiliary_indices_round_negative_differences_down(self):
        from camera_install.raw_recipe_reference import auxiliary_indices
        self.assertEqual(auxiliary_indices([0,0,31],vectorized=True),(0,1,0,False))
        self.assertEqual(auxiliary_indices([0,0,31]),(0,0,0,True))
        self.assertEqual(auxiliary_indices([0,0,33],vectorized=True),(0,2,0,False))
        self.assertEqual(auxiliary_indices([0,0,33]),(0,1,0,False))
        with self.assertRaises(ValueError):auxiliary_indices([0]*3,vectorized=1)

    def test_second_chroma_conversion_matches_native_in_both_modes(self):
        from camera_install.raw_recipe_reference import post_lookup_chroma
        cases = [([[0, 65535, 0], 0], [-21759, -27391]), ([[0, 65535, 0], 1], [-24478, -27391]), ([[-41010, 11779, -33370], 1], [-15420, -22690]), ([[-55341, 9136, -27533], 0], [-7504, -29230])]
        for (rgb, mode), expected in cases:
            self.assertEqual(post_lookup_chroma(rgb, bool(mode)), expected)
        self.assertEqual(post_lookup_chroma([65535]*3), [0,0])
        for rgb, mode in (([True,0,0],False),([262145,0,0],False),([0]*3,1)):
            with self.assertRaises(ValueError):post_lookup_chroma(rgb,mode)

    def test_signed_lookup_reflects_about_nonzero_origin_and_caps_only_positive(self):
        from camera_install.raw_recipe_reference import signed_curve_lookup
        full=[(i*3+7)%65536 for i in range(131073)]
        coarse=[(i*5+3)%4096 for i in range(4097)]
        self.assertEqual(signed_curve_lookup(-32,0,full=full),-89)
        self.assertEqual(signed_curve_lookup(32,0,full=full),7)
        self.assertEqual(signed_curve_lookup(-31,0,coarse=coarse),-64)
        self.assertEqual(signed_curve_lookup(31,131072,coarse=coarse),256)
        self.assertEqual(signed_curve_lookup(-33,0),-66)
        self.assertEqual(signed_curve_lookup(32,0,full=full,coarse=coarse),7)
        for value,limit in ((True,0),(131073,0),(0,-1)):
            with self.assertRaises(ValueError):signed_curve_lookup(value,limit)
        with self.assertRaises(ValueError):signed_curve_lookup(0,0,full=[0])

    def test_mixed_channel_exposure_truncates_before_signed_clipping(self):
        from camera_install.raw_recipe_reference import scale_mixed_channels
        self.assertEqual(scale_mixed_channels([-1,1,16385],8192,-131071,131071),[0,0,8192])
        self.assertEqual(scale_mixed_channels([-131071,0,131071],65536,-65535,65535),[-65535,0,65535])
        for values,factor,low,high in (([True,0,0],1,-1,1),([0]*3,65537,-1,1),([0]*3,1,1,-1)):
            with self.assertRaises(ValueError):scale_mixed_channels(values,factor,low,high)

    def test_continuous_chroma_block_matches_native_vectors(self):
        from camera_install.raw_recipe_reference import scale_chroma_pair, mix_chroma_luma
        cases = [([[14043, 57398, 34363], [306, 601, 117], [-10253, 2944], 850, [171, 99, 184, 185], 32767], [35229, 45321, 41288]), ([[28075, 18587, 21551], [306, 601, 117], [-13763, 12679], 243, [102, 187, 190, 122], 65535], [16989, 26225, 20422]), ([[35881, 35288, 28951], [306, 601, 117], [7597, 13273], 41, [58, 54, 116, 17], 32767], [34878, 35222, 34474])]
        for inputs, expected in cases:
            channels, weights, chroma, amount, gains, maximum = inputs
            adjusted = scale_chroma_pair(chroma, amount, gains)
            self.assertEqual(mix_chroma_luma(channels, weights, adjusted, maximum), expected)

    def test_post_gain_mix_caps_only_upper_chroma_and_truncates(self):
        from camera_install.raw_recipe_reference import mix_chroma_luma
        self.assertEqual(mix_chroma_luma([0]*3,[306,601,117],[-65536,65534],32767),[-65536,32767,-4095])
        self.assertEqual(mix_chroma_luma([0]*3,[306,601,117],[1,0],65535),[1,0,0])
        self.assertEqual(mix_chroma_luma([1000]*3,[306,601,117],[0,0],65535),[1000]*3)
        for channels,weights,chroma,limit in (([0]*3,[1024]*3,[0,0],0),([0]*3,[0]*3,[65536,0],0),
                                             ([0]*3,[0]*3,[0,0],True),([True]*3,[0]*3,[0,0],0)):
            with self.assertRaises(ValueError):mix_chroma_luma(channels,weights,chroma,limit)

    def test_chroma_gain_uses_sign_and_truncates_each_stage(self):
        from camera_install.raw_recipe_reference import scale_chroma_pair
        self.assertEqual(scale_chroma_pair([1025,-1025],1023,[64,128,192,256]),[511,-2046])
        self.assertEqual(scale_chroma_pair([-1,1],1023,[64,128,192,256]),[0,0])
        self.assertEqual(scale_chroma_pair([-32768,32767],1024,[256]*4),[-65536,65534])
        for args in (([True,0],0,[0]*4),([32768,0],0,[0]*4),([0,0],1025,[0]*4),
                     ([0,0],True,[0]*4),([0,0],0,[257]*4),([0,0],0,[0]*3)):
            with self.assertRaises(ValueError):scale_chroma_pair(*args)

    def test_auxiliary_indices_use_truncated_difference_for_table_sign(self):
        from camera_install.raw_recipe_reference import auxiliary_indices
        self.assertEqual(auxiliary_indices([0,0,31]),(0,0,0,True))
        self.assertEqual(auxiliary_indices([0,0,32]),(0,1,0,False))
        self.assertEqual(auxiliary_indices([0,65535,0]),(511,1023,1023,True))
        self.assertEqual(auxiliary_indices([65535,0,65535]),(1023,1023,0,False))

    def test_auxiliary_luma_minimum_branch_with_q10_gains(self):
        for rgb,gains,expected in (([65535]*3,[1024]*3,1023),
                                   ([65535]*3,[512,1024,2048],1023),
                                   ([31]*3,[1024]*3,0),([32]*3,[1024]*3,1),
                                   ([1000,2000,3000],[512,1024,2048],15),
                                   ([65535]*3,[8192,1,0],0)):
            self.assertEqual(auxiliary_luma_bin(rgb,gains),expected)
        for gains in ([0,0],[-1,0,0],[8193,0,0],[True,0,0],[1.0,0,0]):
            with self.assertRaises(ValueError):auxiliary_luma_bin([0]*3,gains)

    def test_default_auxiliary_luma_bin_boundaries_and_channel_order(self):
        for rgb, expected in (([0,0,0],0),([63,0,0],0),([64,0,0],1),
                              ([0,127,0],0),([0,128,0],1),([0,0,128],1),
                              ([65535,0,0],1023),([0,65535,0],511),
                              ([32768]*3,1023),([65535]*3,1023)):
            self.assertEqual(auxiliary_luma_bin(rgb),expected)
        for rgb in ([True,0,0],[-1,0,0],[65536,0,0],[1.0,0,0],[0,0]):
            with self.assertRaises(ValueError):auxiliary_luma_bin(rgb)

    def test_channel_gain_rounds_between_stages_and_caps(self):
        for args, expected in (((99,99,1536,65535),147), ((1,99,1536,65535),0),
                               ((65535,200,1536,65535),65535), ((65535,100,1,65535),63),
                               ((32767,100,1023,65535),32735), ((65535,0,8192,65535),0)):
            self.assertEqual(scale_channel_q10(*args),expected)
        for index in range(4):
            for invalid in (-1, True, 1.5):
                args=[100,100,1024,65535];args[index]=invalid
                with self.assertRaises(ValueError):scale_channel_q10(*args)

    def test_native_chroma_vectors_and_signed_rounding(self):
        cases=(([0,0,65535],[32767,-5327]),([0,65535,0],[-21695,-27423]),
               ([65535,0,0],[-11055,32767]),([65535]*3,[15,15]),
               ([342,398,444],[32,-31]),([0,0,1],[0,0]))
        for rgb,expected in cases:
            with self.subTest(rgb=rgb):self.assertEqual(chroma_from_rgb16(rgb),expected)

    def test_native_rgb_vectors_and_clipping(self):
        cases=((0,[-32768,-32768],[0,34696,0]),(0,[-32768,32767],[45951,0,0]),
               (0,[32767,-32768],[0,12104,58030]),(65535,[0,0],[65535,65535,65519]),
               (12782,[1610,-1453],[10744,13271,15630]))
        for y,chroma,expected in cases:
            with self.subTest(y=y,chroma=chroma):self.assertEqual(rgb16_from_ycbcr(y,chroma),expected)

    def test_vector_chroma_rounds_negative_values_down(self):
        self.assertEqual(chroma_from_rgb16([342,398,444], vectorized=True), [32,-32])
        self.assertEqual(chroma_from_rgb16([0,0,1], vectorized=True), [0,-1])
        self.assertEqual(chroma_from_rgb16([65535]*3, vectorized=True), [15,15])
        with self.assertRaises(ValueError):
            chroma_from_rgb16([0,0,0], vectorized=1)

    def test_native_vector_pre_tone_round_trip(self):
        from camera_install.raw_recipe_reference import pre_tone_rgb16
        for rgb, expected in (([2262,2381,2476],[4524,4764,4952]),
                               ([2291,2404,2506],[4580,4808,5008]),
                               ([2366,2493,2602],[4732,4986,5202])):
            self.assertEqual(pre_tone_rgb16(rgb,vectorized=True),expected)
        self.assertEqual(pre_tone_rgb16([0,0,0],vectorized=True),[0,0,0])
        for invalid in (-1,65536,True,1.0):
            with self.assertRaises(ValueError):pre_tone_rgb16([invalid,0,0])

    def test_native_cubic_spline_kernel(self):
        from camera_install.raw_recipe_reference import sample_cubic_spline
        knots=[0,0.1,0.35,0.7,1]
        values=[0,0.2,0.3,0.8,1]
        second=[0,-0.4,0.25,0.6,0]
        for coordinate, expected in ((-0.2,-0.396),(0,0),(0.01,0.020066),
                                     (0.1,0.2),(0.2,0.240725),(0.35,0.3),
                                     (0.5,0.5080357142857144),(0.7,0.8),
                                     (0.9,0.9306666666666666),(1,1),(1.2,1.1366666666666667)):
            self.assertAlmostEqual(sample_cubic_spline(knots,values,second,coordinate),expected,places=14)
        self.assertEqual(sample_cubic_spline([0,1],[0,2],[0,0],0.5),1)
        for bad_knots in ([0],[0,0],[1,0],[0,float('nan')],[0,float('inf')]):
            with self.assertRaises(ValueError):
                sample_cubic_spline(bad_knots,[0]*len(bad_knots),[0]*len(bad_knots),0)
        with self.assertRaises(ValueError):sample_cubic_spline([0,1],[0],[0,0],0)
        with self.assertRaises(ValueError):sample_cubic_spline([0,1],[0,1],[0,0],True)

    def test_spline_second_derivatives(self):
        from camera_install.raw_recipe_reference import spline_second_derivatives
        self.assertEqual(spline_second_derivatives([0,1,2],[0,1,4]),[0,3,0])
        for value in spline_second_derivatives([0,1,2],[0,1,4],0,4):
            self.assertAlmostEqual(value,2,places=14)
        self.assertEqual(spline_second_derivatives([0,1],[0,1],0,0),[6,-6])
        self.assertEqual(spline_second_derivatives([0,1],[0,1],1e30,1e30),[0,0])
        knots=[0,0.30000000000000004,0.8,1.5,2.4000000000000004]
        values=[0,0.3045202066613396,0.7813560908995228,1.2224949866040544,1.2514631805511507]
        expected=[5.9060161735949315,-1.510685236433896,0.5538360076943238,-3.592434109281939,8.355594114096165]
        for actual, target in zip(spline_second_derivatives(knots,values,0.5,2),expected):
            self.assertAlmostEqual(actual,target,places=13)
        for knots,values in (([0],[0]),([0,0],[0,1]),([1,0],[0,1]),([0,1],[0]),([0,float('inf')],[0,1])):
            with self.assertRaises(ValueError):spline_second_derivatives(knots,values)
        for slope in (True,float('nan'),float('inf')):
            with self.assertRaises(ValueError):spline_second_derivatives([0,1],[0,1],slope)

    def test_spline_lookup_quantization_and_monotonicity(self):
        from camera_install.raw_recipe_reference import build_spline_lookup
        self.assertEqual(build_spline_lookup([0,2],[0,4],5,5),[0,2,4,4,4])
        self.assertEqual(build_spline_lookup([0,2],[4,0],5,5),[4,4,4,4,4])
        knots=[0,128,408,512,612,892,1020]
        lookup=build_spline_lookup(knots,knots,1024,1024)
        for position,expected in ((0,0),(357,356),(654,653),(850,849),(885,884),(1023,1023)):
            self.assertEqual(lookup[position],expected)
        for size,maximum in ((0,1),(1,0),(65536,1),(1,65536),(True,1)):
            with self.assertRaises(ValueError):build_spline_lookup([0,1],[0,1],size,maximum)

    def test_spline_densification_preserves_controls(self):
        from camera_install.raw_recipe_reference import densify_spline
        x,y=densify_spline([0,1],[0,2])
        self.assertEqual(len(x),126)
        self.assertEqual((x[0],y[0],x[-1],y[-1]),(0,0,1,2))
        self.assertTrue(all(a<b for a,b in zip(x,x[1:])))
        for coordinate,value in zip(x,y):self.assertAlmostEqual(value,2*coordinate,places=14)
        x,y=densify_spline([0,0.25,1],[0,0.5,1])
        self.assertEqual(len(x),167)
        self.assertEqual((x[83],y[83]),(0.25,0.5))
        with self.assertRaises(ValueError):densify_spline(list(range(252)),list(range(252)))
        with self.assertRaises(ValueError):densify_spline([0],[0])

    def test_tone_interpolation_and_saturated_endpoint(self):
        curve=[min(i*17,1023) for i in range(2048)]
        for position,expected in ((0,0),(1,17),(63,1071),(64,1088),(65,1105),
                                  (131007,65472),(131008,65472),(131071,65472)):
            with self.subTest(position=position):self.assertEqual(sample_tone64(curve,position),expected)
        self.assertEqual(sample_tone64([0]*2047+[1023],131007),64449)

    def test_invalid_color_inputs(self):
        for rgb in ([True,0,0],[-1,0,0],[65536,0,0],[1.0,0,0],[0,0]):
            with self.assertRaises(ValueError):chroma_from_rgb16(rgb)
        for y,chroma in ((True,[0,0]),(-1,[0,0]),(65536,[0,0]),(0,[32768,0]),
                         (0,[-32769,0]),(0,[0.0,0]),(0,[0])):
            with self.assertRaises(ValueError):rgb16_from_ycbcr(y,chroma)

    def test_invalid_tone_inputs(self):
        for coordinate in (-1,131072,True,1.0):
            with self.assertRaises(ValueError):sample_tone64([0]*2048,coordinate)
        for curve in ([0]*2047,[0]*2047+[1024],[0]*2047+[-1],[0]*2047+[1.0]):
            with self.assertRaises(ValueError):sample_tone64(curve,0)


if __name__=='__main__':unittest.main()


class ToneNormalizationTests(unittest.TestCase):
    def test_identity_and_nonzero_range(self):
        from camera_install.raw_recipe_reference import normalize_tone_curve
        knots = [0, 8191.5, 16383]
        values = [0, 4000, 16383]
        self.assertEqual(normalize_tone_curve(knots, values, 0, 4095, 0, 4095),
                         (knots, values))
        x, y = normalize_tone_curve(knots, values, 1365, 2730, 0, 4095)
        self.assertEqual(x, [5461, 8191.5, 10922])
        self.assertEqual(y, values)

    def test_reject_invalid_coordinates_and_ranges(self):
        from camera_install.raw_recipe_reference import normalize_tone_curve
        for knots, values, bounds in (([0], [0], (0, 4095, 0, 4095)),
                ([0, 1], [0], (0, 4095, 0, 4095)),
                ([1, 0], [0, 1], (0, 4095, 0, 4095)),
                ([0, float('nan')], [0, 1], (0, 4095, 0, 4095)),
                ([0, 1], [0, float('inf')], (0, 4095, 0, 4095)),
                ([0, 1], [0, 1], (0, 0, 0, 4095)),
                ([0, 1], [0, 1], (0, 4095, 4095, 0)),
                ([0, 1], [0, 1], (-1, 4095, 0, 4095)),
                ([0, 1], [0, 1], (0, 65536, 0, 4095)),
                ([0, 1], [0, 1], (False, 4095, 0, 4095))):
            with self.subTest(knots=knots, bounds=bounds), self.assertRaises(ValueError):
                normalize_tone_curve(knots, values, *bounds)


class ToneWarpChainTests(unittest.TestCase):
    def parameters(self):
        return dict(raw_pivot=4095, end_input=16383, base_span=4095,
                    base_offset=0, edge_span=4095, edge_offset=0, left_power=2,
                    right_power=2, pivot=4095, right_threshold=4095,
                    scale=16383, start_input=0, right_span=4095, right_offset=0)

    def test_identity_coordinates_and_resampling(self):
        from camera_install.raw_recipe_reference import warp_tone_coordinates, resample_tone_curve
        knots = [0, 4095, 16383]
        x, y = warp_tone_coordinates(knots, knots, **self.parameters())
        self.assertEqual(x, knots)
        self.assertEqual(y, [0, 4095*65535/16383, 65535])
        table = resample_tone_curve(x, y)
        self.assertEqual(len(table), 2048)
        self.assertEqual([table[i] for i in (0, 1, 100, 255, 256, 2047)],
                         [0, 4, 400, 1020, 1023, 1023])
        self.assertTrue(all(a <= b for a, b in zip(table, table[1:])))

    def test_warp_domain_validation(self):
        from camera_install.raw_recipe_reference import warp_tone_coordinates
        for key, value in (('scale', 0), ('left_power', .5),
                           ('right_power', float('nan')), ('raw_pivot', -1),
                           ('end_input', 0)):
            params = self.parameters()
            params[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                warp_tone_coordinates([0, 16383], [0, 16383], **params)

    def test_nonmonotonic_fallback_is_explicit(self):
        from camera_install.raw_recipe_reference import warp_tone_coordinates
        params = self.parameters()
        params.update(base_span=-4095, edge_span=-4095, right_span=-4095)
        with self.assertRaisesRegex(ValueError, 'fallback'):
            warp_tone_coordinates([0, 4095, 16383], [0, 4095, 16383], **params)


class ToneParameterDerivationTests(unittest.TestCase):
    def test_symmetric_generator_ranges(self):
        from camera_install.raw_recipe_reference import derive_tone_warp_parameters
        for flag in (0, 1):
            p = derive_tone_warp_parameters([1, 2, 3, 2, 4, 0], 1000, 250, 0, 4095, flag)
            self.assertEqual(p['base_span'], 4095)
            self.assertEqual(p['right_span'], 4095)
            self.assertEqual(p['edge_span'], 4095)
            self.assertEqual(p['base_offset'], 0)
            self.assertEqual(p['right_offset'], 0)
            self.assertEqual(p['left_power'], 3)
            self.assertEqual(p['right_power'], 3)
            self.assertEqual(p['scale'], 32767+(flag << 15))
            self.assertEqual(p['pivot'], p['right_threshold'])

    def test_invalid_generator_inputs(self):
        from camera_install.raw_recipe_reference import derive_tone_warp_parameters
        base = [[1, 2, 3, 2, 4, 0], 1000, 250, 0, 4095, 0]
        for index, value in ((0, [1]), (0, [1, 0, 3, 2, 4, 0]),
                             (0, [1, 2, 3, 4, 4, 0]),
                             (0, [1, 2, float('nan'), 2, 4, 0]),
                             (1, 0), (1, 16383), (2, 0), (3, 4095),
                             (4, 65536), (5, 2), (5, True)):
            case = base.copy()
            case[index] = value
            with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                derive_tone_warp_parameters(*case)


class AdaptiveToneSamplerTests(unittest.TestCase):
    def test_curvature_change_uses_linear_interpolation(self):
        from camera_install.raw_recipe_reference import resample_tone_curve
        table = resample_tone_curve([0, 100, 200], [0, 3200, 12800])
        self.assertEqual(table[:4], [0, 32, 92, 188])
        self.assertEqual(table[-1], 1023)


class EditorExposureToneInputsTests(unittest.TestCase):
    def test_native_verified_exposure_entry_scalars(self):
        from camera_install.raw_recipe_reference import derive_tone_warp_parameters
        fixtures = [(1200, 20630, 16380, 20965.901995653032, 2.343805671236489), (377, 6498, 5146.05, 6604.852400711323, 2.337395154861804), (238, 4093, 3248.7000000000003, 4159.729895277613, 2.342964626396629), (150, 2578, 2047.4999999999998, 2619.928472633867, 2.344529655737059), (75, 1289, 1023.7499999999999, 1309.9642363169335, 2.344529655737059)]
        for target, upper, base_span, right_span, power in fixtures:
            with self.subTest(target=target, upper=upper):
                p = derive_tone_warp_parameters([1, 2, 3, 2, 4, 0],
                                                1200, target, 0, upper, 0)
                self.assertEqual(p["base_span"], base_span)
                self.assertEqual(p["right_span"], right_span)
                self.assertEqual(p["right_power"], power)
