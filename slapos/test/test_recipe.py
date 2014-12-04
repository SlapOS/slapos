import os
import sys
import unittest

def additional_tests():
  """
  Load all recipe tests. test file must be called or finished by "test_recipe.py".
  """
  setup_file = sys.modules['__main__'].__file__
  setup_directory = os.path.abspath(os.path.dirname(setup_file))
  recipe_directory = os.path.join(setup_directory, 'slapos', 'test', 'recipe')
  return unittest.defaultTestLoader.discover(recipe_directory)

