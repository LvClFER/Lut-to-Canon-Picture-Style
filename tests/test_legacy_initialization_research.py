import unittest
from camera_install.legacy_initialization_research import classify, base_context_prepares_legacy_aliases, pf3_context_converts_dense, extract


class LegacyInitializationTests(unittest.TestCase):
    def setUp(self):
        # Synthetic switch geometry only; no Canon binary fixture.
        self.rules={'explicitSkipIds':[999],'switchBase':100,'switchSelectors':[0,1,2]}

    def test_explicit_and_indexed_routes(self):
        for identifier,expected in ((999,'skip-record-initialization'),
                                    (100,'skip-record-initialization'),
                                    (101,'legacy-record-list'),(102,'common-record-list')):
            self.assertEqual(classify(identifier,self.rules),expected)

    def test_default_branch_not_support_claim(self):
        for identifier in (0,99,103,0xffffffff):
            self.assertEqual(classify(identifier,self.rules),'common-record-list')

    def test_identifier_domain(self):
        for identifier in (True,False,1.0,'100',-1,0x100000000):
            with self.assertRaises(ValueError): classify(identifier,self.rules)

    def test_unknown_selector(self):
        for selector in (True,3,-1,'1'):
            with self.assertRaises(ValueError):
                classify(100,dict(self.rules,switchSelectors=[selector]))

    def test_base_context_alias_preparation_gate(self):
        for family in range(11):
            self.assertEqual(base_context_prepares_legacy_aliases(family), family not in (8,9,10))
        # Replays a branch, not a verdict on an unknown camera.
        self.assertTrue(base_context_prepares_legacy_aliases(0xffffffff))

    def test_alias_gate_domain(self):
        for family in (True,False,1.0,'1',-1,0x100000000):
            with self.assertRaises(ValueError):
                base_context_prepares_legacy_aliases(family)

    def test_pf3_gate_same_classes_different_preparation(self):
        for family in range(11):
            self.assertEqual(pf3_context_converts_dense(family), family not in (8,9,10))
        for family in (True,1.0,-1,0x100000000):
            with self.assertRaises(ValueError): pf3_context_converts_dense(family)

    def test_unknown_extraction_context(self):
        for context in ('other',True,None):
            with self.assertRaises(ValueError): extract(None,context)
