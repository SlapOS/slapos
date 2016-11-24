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
import os

from slapos.recipe.librecipe import GenericBaseRecipe
from zc.buildout import UserError

class Recipe(GenericBaseRecipe):

  def install(self):
    self.logger.info("Installing dcron...")

    options = self.options
    script = self.createWrapper(name=options['binary'],
                                command=options['dcrond-binary'].strip(),
                                parameters=[
                                    '-s', options['cron-entries'],
                                    '-c', options['crontabs'],
                                    '-t', options['cronstamps'],
                                    '-f', '-l', '5',
                                    '-M', options['catcher']
                                    ])

    self.logger.debug('Main cron executable created at : %r', script)

    self.logger.info("dcron successfully installed.")

    return [script]


class Part(GenericBaseRecipe):

  def install(self):
    try:
      periodicity = self.options['frequency']
    except KeyError:
      periodicity = self.options['time']
      try:
        periodicity = systemd_to_cron(periodicity)
      except Exception:
        raise UserError("Invalid systemd calendar spec %r" % periodicity)
    cron_d = self.options['cron-entries']
    name = self.options['name']
    filename = os.path.join(cron_d, name)

    with open(filename, 'w') as part:
      part.write('%s %s\n' % (periodicity, self.options['command']))

    return [filename]


day_of_week_dict = dict((name, dow) for dow, name in enumerate(
    "sunday monday tuesday wednesday thursday friday saturday".split())
  for name in (name, name[:3]))
symbolic_dict = dict(minutely = '* * * * *',
                     hourly   = '0 * * * *',
                     daily    = '0 0 * * *',
                     weekly   = '0 0 * * 0',
                     monthly  = '0 0 1 * *',
                     yearly   = '0 0 1 1 *')

def systemd_to_cron(spec):
  """Convert from systemd.time(7) calendar spec to crontab spec"""
  try:
    return symbolic_dict[spec]
  except KeyError:
    pass
  if not spec.strip():
    raise ValueError
  spec = spec.split(' ')
  try:
    dow = ','.join(sorted('-'.join(str(day_of_week_dict[x.lower()])
                                   for x in x.split('-', 1))
                          for x in spec[0].split(',')
                          if x))
    del spec[0]
  except KeyError:
    dow = '*'
  day = spec.pop(0) if spec else '*-*'
  if spec:
    time, = spec
  elif ':' in day:
    time = day
    day = '*-*'
  else:
    time = '0:0'
  day = day.split('-')
  time = time.split(':')
  if (# years not supported
      len(day) > 2 and day.pop(0) != '*' or
      # some crons ignore day of month if day of week is given, and dcron
      # treats day of month in a way that is not compatible with systemd
      dow != '*' != day[1] or
      # seconds not supported
      len(time) > 2 and int(time.pop())):
    raise ValueError
  month, day = day
  hour, minute = time
  spec = [minute, hour, day, month, dow]
  for i, (y, z) in enumerate(((0, 60), (0, 24), (1, 31), (1, 12))):
    x = spec[i]
    if x != '*':
      for x in x.split(','):
        x = map(int, x.split('/', 1))
        a = x[0] - y
        if 0 <= a < z:
          if len(x) == 1:
            continue
          b = x[1]
          if b > 0:
            a = (z - a - 1) // b * b
            if a:
              spec[i] = '%s-%s/%s' % (x[0], x[0] + a, b)
              continue
        raise ValueError
  return ' '.join(spec)

