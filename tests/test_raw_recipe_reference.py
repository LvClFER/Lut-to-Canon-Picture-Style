import unittest

from camera_install.raw_recipe_reference import chroma_from_rgb16,rgb16_from_ycbcr,sample_tone64,scale_channel_q10,auxiliary_luma_bin


class RawRecipeReferenceTests(unittest.TestCase):
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
