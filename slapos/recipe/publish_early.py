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

import slapos.slap
from slapos.recipe.librecipe import unwrap, wrap
from slapos.recipe.librecipe import GenericSlapRecipe

class Recipe(GenericSlapRecipe):
  """
  Early initialization of published parameters.

  The '-init' option defines parameters that should be published before
  requesting any partitions, and how they are initialized.

  Example:

    [publish-early]
    recipe = slapos.cookbook:publish-early
    -init =
      foo gen-foo:x
      bar gen-bar:y
    bar = z

    [gen-foo]
    ...

    [publish]
    recipe = slapos.cookbook:publish.serialised
    -extends = publish-early
    ...

  ${publish-early:foo} is initialized with the value of the published
  parameter 'foo', or ${gen-foo:x} if it hasn't been published yet
  (and in this case, it is published immediately as a way to save the value).
  ${publish-early:bar} is forced to 'z' (${gen-bar:y} ignored):
  a line like 'bar = z' is usually rendered conditionally with Jinja2.
  """
  def __init__(self, buildout, name, options):
    GenericSlapRecipe.__init__(self, buildout, name, options)
    published_dict = None
    publish = False
    publish_dict = {}
    for line in options['-init'].splitlines():
      if line:
        k, v = line.split()
        if k not in options:
          if published_dict is None:
            self.slap.initializeConnection(self.server_url, self.key_file,
              self.cert_file)
            computer_partition = self.slap.registerComputerPartition(
              self.computer_id, self.computer_partition_id)
            published_dict = unwrap(
              computer_partition.getConnectionParameterDict())
          try:
            publish_dict[k] = published_dict[k]
          except KeyError:
            section, key = v.split(":")
            publish_dict[k] = self.buildout[section][key]
            publish = True
    if publish:
      computer_partition.setConnectionDict(wrap(publish_dict))
    options.update(publish_dict)

  install = update = lambda self: None
