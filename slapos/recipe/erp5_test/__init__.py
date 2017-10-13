##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from slapos.recipe.librecipe import GenericBaseRecipe

# The follow recipes should be unified somehow in order to improve
# code mantainence.

class CloudoooRecipe(GenericBaseRecipe):
  def install(self):
    path_list = []
    common_dict = dict(
        prepend_path=self.options['prepend-path'],
    )
    common_list = [
           "--paster_path", self.options['ooo-paster'],
           self.options['configuration-file']
          ]
    run_unit_test_path = self.createPythonScript(self.options['run-unit-test'],
        __name__ + '.test.runUnitTest', [dict(
        call_list=[self.options['run-unit-test-binary'],
          ] + common_list, **common_dict)])

    path_list.append(run_unit_test_path)
    path_list.append(self.createPythonScript(self.options['run-test-suite'],
        __name__ + '.test.runTestSuite', [dict(
        call_list=[self.options['run-test-suite-binary'],
          ], **common_dict)]))

    return path_list

class EggTestRecipe(GenericBaseRecipe):
  """
  Recipe used to create wrapper used to run test suite (python setup.py test)
  off a list of Python eggs.
  """
  def install(self):
    path_list = []
    test_list = self.options['test-list'].strip().replace('\n', ',')
    common_dict = {}

    environment_dict = {}
    if self.options.get('environment'):
      environment_part = self.buildout.get(self.options['environment'])
      if environment_part:
        for key, value in environment_part.iteritems():
          environment_dict[key] = value

    common_list = [ "--source_code_path_list", test_list]

    argument_dict = dict(
        call_list=[self.options['run-test-suite-binary'],] + common_list,
        environment=environment_dict,
        **common_dict
    )
    if 'prepend-path' in self.options:
      argument_dict['prepend_path'] = self.options['prepend-path']

    run_test_suite_script = self.createPythonScript(
        self.options['run-test-suite'], __name__ + '.test.runTestSuite',
        [argument_dict]
    )

    path_list.append(run_test_suite_script)

    return path_list
