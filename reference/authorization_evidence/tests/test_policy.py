import copy
import unittest
from ..policy import narrow
from ..core import Rejected
from .fixtures import Fixture

class PolicyTests(unittest.TestCase):
    def setUp(self):self.parent=Fixture().limits
    def test_equal_not_strict(self):
        with self.assertRaises(Rejected):narrow(copy.deepcopy(self.parent),self.parent,strict=True)
    def test_resource_split_not_strict(self):
        parent=copy.deepcopy(self.parent);parent['allow'][0]['resources']=['a','b']
        child=copy.deepcopy(parent);child['allow']=[copy.deepcopy(parent['allow'][0]) for _ in range(2)]
        child['allow'][0]['resources']=['a'];child['allow'][1]['resources']=['b']
        with self.assertRaises(Rejected):narrow(child,parent,strict=True)
    def test_smaller_resource_strict(self):
        parent=copy.deepcopy(self.parent);parent['allow'][0]['resources']=['a','b']
        child=copy.deepcopy(parent);child['allow'][0]['resources']=['a'];narrow(child,parent,strict=True)
    def test_time_narrow_strict(self):
        child=copy.deepcopy(self.parent);child['allow'][0]['valid_from']='2026-10-21T00:01:00Z';narrow(child,self.parent,strict=True)
    def test_budget_narrow_strict(self):
        child=copy.deepcopy(self.parent);child['total_budget']['amount']='99';narrow(child,self.parent,strict=True)
    def test_widen_rejected(self):
        child=copy.deepcopy(self.parent);child['allow'][0]['resources'].append('other')
        with self.assertRaises(Rejected):narrow(child,self.parent)
    def test_parent_deny_not_removed(self):
        parent=copy.deepcopy(self.parent);parent['deny']=[copy.deepcopy(parent['allow'][0])]
        with self.assertRaises(Rejected):narrow(self.parent,parent)
