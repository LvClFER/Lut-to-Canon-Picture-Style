import unittest

from camera_install.raw_recipe_reference import chroma_from_rgb16,rgb16_from_ycbcr,sample_tone64,scale_channel_q10,auxiliary_luma_bin


class RawRecipeReferenceTests(unittest.TestCase):
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
