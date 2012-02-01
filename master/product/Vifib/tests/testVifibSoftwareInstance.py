from Products.ERP5Type.tests.backportUnittest import skip
import unittest
from VifibMixin import testVifibMixin

class TestVifibSoftwareInstance(testVifibMixin):
  ########################################
  # Software Instance graph helpers
  ########################################

  def _test_si_tree(self):
    software_instance = self.portal.software_instance_module.newContent(
      portal_type='Software Instance')
    self.checkConnected = software_instance.checkConnected
    self.checkNotCyclic = software_instance.checkNotCyclic

  def test_si_tree_simple_connected(self):
    """Graph of one element is connected

    A
    """
    self._test_si_tree()
    graph = {'A': []}
    root = 'A'
    self.assertEqual(True, self.checkConnected(graph, root))

  def test_si_tree_simple_list_connected(self):
    """Graph of list is connected

    B->C->A
    """
    self._test_si_tree()
    graph = {'A': [], 'B': ['C'], 'C': ['A']}
    root = 'B'
    self.assertEqual(True, self.checkConnected(graph, root))

  def test_si_tree_complex_connected(self):
    """Tree is connected

    B --> A
      \-> C --> D
            \-> E --> F
    """
    self._test_si_tree()
    graph = {
      'A': [],
      'B': ['A', 'C'],
      'C': ['D', 'E'],
      'D': [],
      'E': ['F'],
      'F': [],
    }
    root = 'B'
    self.assertEqual(True, self.checkConnected(graph, root))

  def test_si_tree_simple_list_disconnected(self):
    """Two lists are disconnected

    A->B
    C
    """
    self._test_si_tree()
    graph = {'A': ['B'], 'B': [], 'C': []}
    root = 'A'
    from erp5.document.SoftwareInstance import DisconnectedSoftwareTree
    self.assertRaises(DisconnectedSoftwareTree, self.checkConnected, graph,
      root)

  @skip('For now limitation of implementation gives false positive')
  def test_si_tree_cyclic_connected(self):
    """Cyclic is connected

    A<->B
    """
    self._test_si_tree()
    graph = {'A': ['B'], 'B': ['A']}
    root = 'B'
    self.assertEqual(True, self.checkConnected(graph, root))

  def test_si_tree_cyclic_disconnected(self):
    """Two trees, where one is cyclic are disconnected

    B --> A
      \-> H
    C --> D --> G
    ^ \-> E --> F \
     \------------/
    """
    self._test_si_tree()
    graph = {
      'A': [],
      'B': ['A', 'H'],
      'C': ['D', 'E'],
      'D': ['G'],
      'E': ['F'],
      'F': ['C'],
      'G': [],
      'H': [],
    }
    root = 'B'
    from erp5.document.SoftwareInstance import DisconnectedSoftwareTree
    self.assertRaises(DisconnectedSoftwareTree, self.checkConnected, graph,
      root)

  def test_si_tree_simple_not_cyclic(self):
    """Graph of one element is not cyclic

    A
    """
    self._test_si_tree()
    graph = {'A': []}
    self.assertEqual(True, self.checkNotCyclic(graph))

  def test_si_tree_simple_list_not_cyclic(self):
    """Graph of list is not cyclic

    B->C->A
    """
    self._test_si_tree()
    graph = {'A': [], 'B': ['C'], 'C': ['A']}
    self.assertEqual(True, self.checkNotCyclic(graph))

  def test_si_tree_simple_list_cyclic(self):
    """Graph of cyclic list is cyclic

    B->C->A-\
    ^-------/
    """
    self._test_si_tree()
    graph = {'A': ['B'], 'B': ['C'], 'C': ['A']}
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree, self.checkNotCyclic, graph)

  def test_si_tree_simple_list_cyclic_non_root(self):
    """Graph of cyclic list is cyclic

    B->C->D->A-\
       ^-------/
    """
    self._test_si_tree()
    graph = {'A': ['C'], 'B': ['C'], 'C': ['D'], 'D': ['A']}
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree, self.checkNotCyclic, graph)

  def test_si_tree_complex_not_cyclic(self):
    """Tree is not cyclic

    B --> A
      \-> C --> D
            \-> E --> F
    """
    self._test_si_tree()
    graph = {
      'A': [],
      'B': ['A', 'C'],
      'C': ['D', 'E'],
      'D': [],
      'E': ['F'],
      'F': [],
    }
    self.assertEqual(True, self.checkNotCyclic(graph))

  def test_si_tree_complex_cyclic(self):
    """Tree is not cyclic

    B --> A
      \-> C --> D
          ^ \-> E --> F -\
           \-------------/
    """
    self._test_si_tree()
    graph = {
      'A': [],
      'B': ['A', 'C'],
      'C': ['D', 'E'],
      'D': [],
      'E': ['F'],
      'F': ['C'],
    }
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree, self.checkNotCyclic, graph)

  def test_si_tree_simple_list_disconnected_not_cyclic(self):
    """Two lists are disconnected

    A->B
    C
    """
    self._test_si_tree()
    graph = {'A': ['B'], 'B': [], 'C': []}
    self.assertEqual(True, self.checkNotCyclic(graph))

  def test_si_tree_cyclic(self):
    """Cyclic is connected

    A<->B
    """
    self._test_si_tree()
    graph = {'A': ['B'], 'B': ['A']}
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree, self.checkNotCyclic, graph)

  def test_si_tree_cyclic_disconnected_cyclic(self):
    """Two trees, where one is cyclic are disconnected

    B --> A
      \-> H
    C --> D --> G
    ^ \-> E --> F \
     \------------/
    """
    self._test_si_tree()
    graph = {
      'A': [],
      'B': ['A', 'H'],
      'C': ['D', 'E'],
      'D': ['G'],
      'E': ['F'],
      'F': ['C'],
      'G': [],
      'H': ['A'],
    }
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree, self.checkNotCyclic, graph)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSoftwareInstance))
  return suite
