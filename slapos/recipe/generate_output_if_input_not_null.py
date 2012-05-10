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

class Recipe(GenericBaseRecipe):
  """Generate an output from one or several input and a template.
  
  Take "input-list" buildout parameter as input.
  Each input of the list is separated by \n
  Each input contains :
    1/ The parameter to use (like mybuildoutpart:myparameter)
    2/ The name of the input to use as key.

  If all parameters in input are found, create an "output" parameter from a
  "template" parameter. The "template" parameter is just a string containing
  python parameters (like %(mykey)s).

  Will produce nothing if one element of "input_list" doesn't exist.
  Will raise if any input reference non-existent buildout part.

  Example : 
  [get-output]
  recipe = slapos.cookbook:generate_output_if_input_not_null
  input-list =
    firstkey mybuildoutpart:myparameter
    otherkey myotherbuildoutpart:myotherparameter
  template = I want to get %(key)s and %(otherkey)s

  This example will produce an "output" parameter if myparameter and
  myotherparameter are defined.
  """
  def __init__(self, buildout, name, options):
    # Get all inputs
    input_dict = {}
    for line in options['input-list'].strip().split('\n'):
      key, buildout_parameter = line.split(' ')
      buildout_part, parameter_name = buildout_parameter.split(':')
      parameter_value = buildout[buildout_part].get(parameter_name)
      # If any parameter is not defined, don't do anything
      if not parameter_value:
        return
      input_dict[key] = parameter_value
    # Generate output
    options['output'] = options['template'] % input_dict

  def install(self):
    return []
