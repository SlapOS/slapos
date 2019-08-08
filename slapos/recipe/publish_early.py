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

from collections import defaultdict
from .librecipe import unwrap, wrap, GenericSlapRecipe

def patchOptions(options, override):
  def get(option, *args, **kw):
    try:
      return override[option]
    except KeyError:
      return options_get(option, *args, **kw)
  try:
    options_get = options._get
  except AttributeError:
    options_get = options.get
    options.get = get
  else:
    options._get = get


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
    -update =
      baz update-baz:z
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

  The '-update' option has the same syntax than '-init'. The recipes of the
  specified sections must implement 'publish_early(publish_dict)':
  - it is always called, just before early publishing
  - publish_dict is a dict with already published values
  - 'publish_early' can change published values by modifying publish_dict.

  In the above example:
  - publish_dict is {'z': ...}
  - during the execution of 'publish_early', other sections can access the
    value with ${update-baz:z}
  - once [publish-early] is initialized, the value should be accessed with
    ${publish-early:bar} ([update-baz] does not have it if it's accessed
    before [publish-early])
  """
  def __init__(self, buildout, name, options):
    GenericSlapRecipe.__init__(self, buildout, name, options)
    init = defaultdict(dict)
    update = defaultdict(dict)
    for d, k in (init, '-init'), (update, '-update'):
      for line in options.get(k, '').splitlines():
        if line:
          k, v = line.split()
          if k not in options:
            section, v = v.split(':')
            d[section][k] = v
    if init or update:
      self.slap.initializeConnection(self.server_url, self.key_file,
        self.cert_file)
      computer_partition = self.slap.registerComputerPartition(
        self.computer_id, self.computer_partition_id)
      published_dict = unwrap(computer_partition.getConnectionParameterDict())

      publish = False
      publish_dict = {}
      for section, init in init.iteritems():
        for k, v in init.iteritems():
          try:
            publish_dict[k] = published_dict[k]
          except KeyError:
            publish_dict[k] = buildout[section][v]
            publish = True

      for section, update in update.iteritems():
        override = {}
        for k, v in update.iteritems():
          try:
            override[v] = published_dict[k]
          except KeyError:
            pass
        section = buildout[section]
        patchOptions(section, override)
        old = override.copy()
        section.recipe.publish_early(override)
        if override != old:
          publish = True
        for k, v in update.iteritems():
          try:
            publish_dict[k] = override[v]
          except KeyError:
            pass

      if publish:
        computer_partition.setConnectionDict(wrap(publish_dict))

      publish = [k for k in options
        if k != 'recipe' and not k.startswith('-')]
      publish += publish_dict
      publish_dict['-publish'] = ' '.join(publish)
      patchOptions(options, publish_dict)

  install = update = lambda self: None
