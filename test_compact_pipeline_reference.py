import unittest
import numpy as np
from camera_install.compact_grid_reference import compact_flag1, synthetic
from camera_install.compact_pipeline_reference import verify_links
from camera_install.packed10_reference import pack10


class CompactPipelineReferenceTests(unittest.TestCase):
    def test_link_and_missing_link_rejection(self):
        source=synthetic('product')
        output=compact_flag1(source)
        hex_output=np.asarray(output,dtype='<f8').tobytes().hex()
        converter=dict(functionRva='0x196a0',converterOption=1,optionalCurves300Hex=None,
                       outputGrid=dict(headerWord12=1),
                       sourceDenseFloat64Hex=np.asarray(source,dtype='<f8').tobytes().hex(),
                       outputDenseFloat64Hex=hex_output)
        packer=dict(functionRva='0x4b760',inputPlanarFloat64Hex=hex_output,coefficientMode=False,
                    nativePackedHex=pack10(output.ravel().tolist(),False).hex())
        self.assertTrue(verify_links([converter,packer])[0]['exactPacking'])
        with self.assertRaises(ValueError):verify_links([converter])
        packer['nativePackedHex']=bytes(4096).hex()
        with self.assertRaises(ValueError):verify_links([converter,packer])
        with self.assertRaises(ValueError):verify_links([])
