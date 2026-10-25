"""Offline reconstruction of model tone-record selection; no camera validation implied."""
import math
import struct

def _u32(value):
    return value & 4294967295

def _s32(value):
    return (value + 2147483648) % 4294967296 - 2147483648

def model_tone_record_index(model_group, iso, exposure, selector, flags, option):
    """Select a model-table record using the observed bounded scalar inputs."""
    if type(model_group) is not int or not 1 <= model_group <= 117:
        raise ValueError('Unsupported model group')
    if any((type(v) is not int or not 0 <= v <= 4294967295 for v in (iso, selector, flags))):
        raise ValueError('Require unsigned ISO, selector and flags')
    if type(option) is not int or not 0 <= option <= 65535:
        raise ValueError('Require unsigned 16-bit option')
    if type(exposure) not in (int, float) or abs(exposure) > 3.4028234663852886e+38 or not math.isfinite(exposure):
        raise ValueError('Require a finite float32 exposure input')
    exposure = struct.unpack('<f', struct.pack('<f', exposure))[0]
    if model_group in (1,):
        if flags != 0:
            if _s32(iso) < 200:
                if 1.0 > exposure:
                    return 0
                return int(4.0 <= exposure) + 1
            if _s32(iso) >= 1600:
                if _s32(iso) >= 2500:
                    if 1.0 <= exposure:
                        return 8
                    return 7
                if 1.0 <= exposure:
                    return 8
                return 6
            if 1.0 > exposure:
                return 6
            return int(4.0 <= exposure) + 7
        if _s32(iso) >= 200:
            if _s32(iso) >= 250:
                if _s32(iso) >= 1600:
                    if 1.0 <= exposure:
                        return 5
                    return 3
                if 1.0 > exposure:
                    return 3
                return int(4.0 <= exposure) + 4
            if 1.0 > exposure:
                return 3
            return 3 if 4.0 > exposure else 5
        if 1.0 > exposure:
            return 0
        return int(4.0 <= exposure) + 1
    if model_group in (2, 7, 15):
        if _s32(iso) < 100:
            return 0
        return int(4.0 <= exposure) + 3
    if model_group in (3,):
        return 14
    if model_group in (4,):
        return 15
    if model_group in (5, 6, 10):
        return int(4.0 <= exposure) + 9
    if model_group in (8,):
        return 22
    if model_group in (9,):
        return 23
    if model_group in (11, 13):
        return int(_s32(iso) >= 200) + 12
    if model_group in (12,):
        if _s32(iso) < 100:
            return 0
        return int(15.0 <= exposure) + 3
    if model_group in (14,):
        if _s32(iso) >= 100:
            if iso != 100:
                return int(15.0 <= exposure) + 20
            return int(15.0 <= exposure) + 18
        return int(15.0 <= exposure) + 16
    if model_group in (16,):
        if iso in (160, 320, 640, 1250):
            return int(15.0 <= exposure) + 26
        return int(15.0 <= exposure) + 24
    if model_group in (17,):
        return int(_s32(iso) >= 200) + 28
    if model_group in (18, 20):
        if selector != 2:
            return int(_s32(iso) >= 100) + 30
        return 32
    if model_group in (19,):
        if selector != 2:
            if iso in (160, 320, 640, 1250):
                return int(10.0 < exposure) + 35
            return int(10.0 < exposure) + 33
        if iso in (160, 320, 640, 1250):
            return int(10.0 < exposure) + 39
        return int(10.0 < exposure) + 37
    if model_group in (21,):
        if selector != 2:
            return int(iso != 100) + 41
        return int(_s32(iso) > 200) + 43
    if model_group in (22,):
        if _s32(iso) >= 200:
            return int(10.0 > exposure) + 45
        return 45
    if model_group in (23, 26, 28):
        if selector != 2:
            if ((_s32(iso) <= 160 or iso == 320) or iso == 640) or iso == 1250:
                return 49
            if iso in (200, 250, 400, 500, 800, 1000, 1600, 2000, 2500, 3200) or _s32(iso) < 6400:
                return 48
            return int(15.0 <= exposure) + 48
        if ((_s32(iso) <= 320 or iso == 640) or iso == 1250) or iso == 2500:
            return 51
        if iso in (400, 500, 800, 1000, 1600, 2000, 3200, 6400) or iso != 12800:
            return 50
        return int(15.0 <= exposure) + 50
    if model_group in (24,):
        if selector != 2:
            if iso != 50:
                if iso in (100, 125, 200, 250, 400, 500, 800, 1000, 1600, 2000, 2500):
                    return 48
                if iso in (160, 320, 640, 1250) or _s32(iso) >= 6400:
                    return 49
                if iso in (3200, 4000, 5000):
                    return int(15.0 <= exposure) + 48
                return 48
            return 47
        if iso in (200, 250, 400, 500, 800, 1000, 1600, 2000, 3200, 4000, 5000):
            return 50
        if iso in (320, 640, 1250, 2500, 12800, 25600):
            return 51
        if iso in (6400, 8000, 10000):
            return int(15.0 <= exposure) + 50
        return 50
    if model_group in (25,):
        if option != 24:
            if option != 25:
                if option != 26:
                    return 64 if option == 27 else 61
                return 63
            return 62
        return 61
    if model_group in (27,):
        if option != 24:
            if option != 25:
                if option != 26:
                    return 68 if option == 27 else 65
                return 67
            return 66
        return 65
    if model_group in (29, 33, 34, 38, 39, 40, 45, 46, 52, 53, 54, 57, 58, 60, 63, 66, 67, 73, 74, 81, 82, 84, 88, 89, 90, 95, 99, 101, 104, 112):
        if selector != 2:
            if _s32(iso) <= 125:
                return 49
            if iso in (160, 320, 640, 1250):
                return 53
            if iso != 2500:
                return 55
            return 53
        if _s32(iso) <= 250:
            return 51
        if iso in (320, 640, 1250, 2500):
            return 54
        if iso != 5000:
            return _s32(54 + selector)
        return 54
    if model_group in (30,):
        if selector != 2:
            if iso == 50:
                return 52
            if iso in (160, 320, 640, 1250):
                return 53
            if iso in (800, 1000, 1600, 2000):
                if exposure < 15.0:
                    return 55
                return 53
            if iso == 2500:
                if 15.0 <= exposure:
                    return 55
                return 53
            if iso != 5000 or 15.0 <= exposure:
                return 55
            return 53
        if iso in (320, 640, 1250, 2500):
            return 54
        if iso in (1600, 2000, 3200, 4000):
            if exposure < 15.0:
                return _s32(54 + selector)
            return 54
        if iso == 5000:
            if 15.0 <= exposure:
                return _s32(54 + selector)
            return 54
        if iso != 10000 or 15.0 <= exposure:
            return _s32(54 + selector)
        return 54
    if model_group in (31, 32, 35, 36, 37, 43, 44, 48):
        if option & option == 0:
            return 65
        if option == 1:
            return 66
        if option == 2:
            return 67
        return 68 if option == 3 else 65
    if model_group in (41, 51):
        if selector != 2:
            if iso == 50:
                return 52
            if iso in (100, 125, 200, 250, 400, 500):
                return 55
            if iso in (160, 320, 640, 1250, 2500, 5000, 10000):
                return 53
            return 55 if 4.0 > exposure else 53
        if iso in (200, 250, 400, 500, 800, 1000):
            return 56
        if iso in (320, 640, 1250, 2500, 5000, 10000, 20000):
            return 54
        return 56 if 4.0 > exposure else 54
    if model_group in (42, 50):
        if selector != 2:
            if iso == 50:
                return 52
            if _s32(iso) <= 640:
                return 55
            if iso in (10000, 20000, 40000):
                return 53
            return 55 if 4.0 > exposure else 53
        if _s32(iso) <= 1250:
            return 56
        if iso in (20000, 40000):
            return 54
        return 56 if 4.0 > exposure else 54
    if model_group in (47, 49):
        if option & option != 0:
            if option != 1:
                if option != 2:
                    if option != 3:
                        if option != 30:
                            if option != 31:
                                if option != 32:
                                    if option != 33:
                                        return 73 if _s32(iso) >= 8000 else 69
                                    return 76
                                return 75
                            return 74
                        return 73
                    return 72
                return 71
            return 70
        return 69
    if model_group in (55, 56, 59, 61):
        if option & option != 0:
            if option != 1:
                if option != 2:
                    return 80 if option == 3 else 77
                return 79
            return 78
        return 77
    if model_group in (62, 65, 70, 71):
        if option & option != 0:
            if option != 1:
                if option != 2:
                    return 84 if option == 3 else 81
                return 83
            return 82
        return 81
    if model_group in (64, 72):
        return int(selector == 2) + 85
    if model_group in (68, 69, 75):
        if selector != 2:
            if iso != 50:
                if iso != 100:
                    return 55
                return 58
            return 57
        return 56 if iso != 200 else 59
    if model_group in (76, 79, 87):
        return int(selector == 2) + 87
    if model_group in (77, 91, 97, 98, 115):
        if selector != 2:
            if iso == 50:
                return 57
            if iso == 100:
                return 58
            if iso in (160, 320, 640, 1250, 2500, 5000, 10000):
                return 53
            if iso != 20000:
                return 55
            return 53
        if iso != 200:
            if iso in (320, 640, 1250, 2500, 5000, 10000):
                return 54
            if iso != 20000:
                return _s32(54 + selector)
            return 54
        return 59
    if model_group in (78, 80, 86):
        if selector != 2:
            if ((((_u32(-200 + iso) <= 84 or _u32(-400 + iso) <= 169) or _u32(-800 + iso) <= 339) or _u32(-1600 + iso) <= 678) or _u32(-3200 + iso) <= 1357) or _s32(iso) >= 6400:
                return 91
            if _u32(-100 + iso) > 41:
                if ((((_u32(-142 + iso) <= 57 or _u32(-285 + iso) <= 114) or _u32(-570 + iso) <= 229) or _u32(-1140 + iso) <= 459) or _u32(-2279 + iso) <= 920) or _u32(-4558 + iso) <= 1841:
                    return 90
                raise ValueError('Native model selection is undefined for this input')
            return 89
        if ((((_u32(-400 + iso) <= 169 or _u32(-800 + iso) <= 339) or _u32(-1600 + iso) <= 678) or _u32(-3200 + iso) <= 1357) or _u32(-6400 + iso) <= 2716) or _s32(iso) >= 12800:
            return 94
        if _u32(-200 + iso) > 84:
            if (((_u32(-285 + iso) <= 114 or _u32(-570 + iso) <= 229) or _u32(-1140 + iso) <= 459) or _u32(-2279 + iso) <= 920) or _u32(-4558 + iso) <= 1841:
                return 93
            if _u32(-9117 + iso) > 3682:
                raise ValueError('Native model selection is undefined for this input')
            return 93
        return 92
    if model_group in (83, 93):
        if selector != 2:
            if iso != 50:
                if iso in (160, 320, 640, 1250, 2500, 5000):
                    return 53
                if iso != 10000:
                    return 55
                return 53
            return 52
        if iso in (320, 640, 1250, 2500, 5000):
            return 54
        if iso != 10000:
            return _s32(54 + selector)
        return 54
    if model_group in (85, 106):
        return _s32(4294967295)
    if model_group in (92,):
        return 95
    if model_group in (94, 96):
        return int(selector == 2) + 55
    if model_group in (100, 102):
        if selector == 2:
            return 56 if iso != 200 else 59
        if iso == 50:
            return 57
        if iso == 100:
            return 58
        if _s32(iso) < 204800:
            return 55
        return 49
    if model_group in (103,):
        if selector == 2:
            return 56 if iso != 200 else 59
        if iso == 50:
            return 57
        if iso == 100:
            return 58
        if iso != 102400:
            return 55
        return 49
    if model_group in (105,):
        if selector != 2:
            if iso == 50:
                return 60
            if iso != 204800:
                return 55
            return 49
        return 56
    if model_group in (107,):
        if selector == 2:
            return 56 if iso != 200 else 59
        if iso != 100:
            return 55
        return 58
    if model_group in (108, 111, 116):
        if selector != 2:
            if iso != 100:
                return 55
            return 49
        return 56 if iso != 200 else 51
    if model_group in (109, 110):
        if selector == 2:
            return 56 if iso != 200 else 59
        if iso != 100:
            if iso != 204800:
                return 55 if iso != 50 else 57
            return 49
        return 58
    if model_group in (113,):
        if selector == 2:
            return 56 if iso != 200 else 59
        if iso == 50:
            return 57
        if iso != 100:
            if iso != 102400:
                return 55
            return 49
        return 58
    if model_group in (114,):
        if selector == 2:
            return 56
        if iso == 50:
            return 60
        if iso == 204800:
            return 49
        if iso != 409600:
            return 55
        return 49
    if model_group in (117,):
        if selector == 2:
            return 56
        if iso != 50:
            if iso != 102400:
                return 55
            return 49
        return 60


# Model identifiers only; no image calibration data.
_MODEL_GROUPS = {
    0x80000001: 1,
    0x80000167: 2,
    0x01140000: 3,
    0x01668000: 4,
    0x80000168: 5,
    0x80000170: 10,
    0x80000175: 11,
    0x80000174: 7,
    0x80000188: 12,
    0x80000189: 13,
    0x80000213: 14,
    0x80000232: 15,
    0x80000234: 16,
    0x80000236: 17,
    0x80000520: 8,
    0x80000560: 9,
    0x80000169: 18,
    0x80000190: 19,
    0x80000176: 21,
    0x80000215: 20,
    0x80000254: 22,
    0x80000261: 23,
    0x80000292: 28,
    0x80000218: 24,
    0x80000252: 26,
    0x80000250: 29,
    0x80000270: 33,
    0x80000281: 30,
    0x80000287: 34,
    0x80000329: 40,
    0x80000286: 38,
    0x80000288: 39,
    0x80000285: 41,
    0x80000269: 42,
    0x80000301: 45,
    0x80000331: 46,
    0x80000324: 50,
    0x80000302: 51,
    0x80000326: 52,
    0x80000346: 53,
    0x80000325: 54,
    0x80000355: 57,
    0x80000384: 58,
    0x80000327: 60,
    0x80000289: 63,
    0x80000347: 66,
    0x80000393: 67,
    0x80000382: 68,
    0x80000401: 69,
    0x80000350: 73,
    0x80000404: 74,
    0x80000328: 75,
    0x80000349: 77,
    0x80000408: 81,
    0x80000405: 82,
    0x80000406: 83,
    0x80000417: 84,
    0x80000427: 85,
    0x80000422: 88,
    0x80000432: 89,
    0x80000424: 91,
    0x80000433: 93,
    0x80000436: 95,
    0x80000437: 97,
    0x80000428: 100,
    0x80000435: 101,
    0x80000453: 102,
    0x80000421: 103,
    0x80000468: 104,
    0x80000450: 105,
    0x80000464: 107,
    0x80000465: 108,
    0x80000481: 109,
    0x80000487: 110,
    0x80000480: 111,
    0x80000498: 112,
    0x80000496: 113,
    0x80000495: 114,
    0x80000497: 115,
    0x80000516: 116,
    0x80000518: 118,
    0x80000517: 119,
    0x40000218: 106,
    0x40000227: 117,
    0x02490000: 25,
    0x02460000: 27,
    0x02700000: 31,
    0x02720000: 32,
    0x02950000: 35,
    0x02920000: 36,
    0x02230000: 37,
    0x03080000: 43,
    0x03110000: 44,
    0x03330000: 47,
    0x03340000: 48,
    0x03360000: 49,
    0x03550000: 55,
    0x03540000: 56,
    0x03640000: 59,
    0x03750000: 61,
    0x03780000: 62,
    0x03740000: 64,
    0x03850000: 65,
    0x03930000: 70,
    0x03950000: 71,
    0x03840000: 72,
    0x03970000: 76,
    0x03940000: 78,
    0x04100000: 79,
    0x04070000: 80,
    0x03980000: 86,
    0x04180000: 87,
    0x00000412: 90,
    0x00000805: 92,
    0x00000804: 94,
    0x00000808: 96,
    0x00000811: 98,
    0x00000812: 99,
}

def model_tone_group(model_id):
    """Resolve an observed Canon model ID; reject unknown IDs explicitly."""
    if type(model_id) is not int or not 0 <= model_id <= 0xffffffff:
        raise ValueError("Require an unsigned 32-bit model identifier")
    group = _MODEL_GROUPS.get(model_id, 0)
    if not group:
        raise ValueError("Unsupported Canon model identifier")
    return group
