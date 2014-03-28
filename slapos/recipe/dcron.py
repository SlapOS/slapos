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

if __name__ == '__main__': # Hack to easily run test below.
  GenericBaseRecipe = object
else:
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
symbolic_dict = dict(hourly  = '0 * * * *',
                     daily   = '0 0 * * *',
                     monthly = '0 0 1 * *',
                     weekly  = '0 0 * * 0')

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
  spec = minute, hour, day, month, dow
  for x, (y, z) in zip(spec, ((0, 60), (0, 24), (1, 31), (1, 12))):
    if x != '*':
      for x in x.split(','):
        x = map(int, x.split('/', 1))
        x[0] -= y
        if x[0] < 0 or len(x) > 1 and x[0] >= x[1] or z <= sum(x):
          raise ValueError
  return ' '.join(spec)

def test(self):
  def _(systemd, cron):
    self.assertEqual(systemd_to_cron(systemd), cron)
  _("Sat,Mon-Thu,Sun", "0 0 * * 0,1-4,6")
  _("mon,sun *-* 2,1:23", "23 2,1 * * 0,1")
  _("Wed, 17:48", "48 17 * * 3")
  _("Wed-Sat,Tue 10-* 1:2", "2 1 * 10 2,3-6")
  _("*-*-7 0:0:0", "0 0 7 * *")
  _("10-15", "0 0 15 10 *")
  _("monday *-12-* 17:00", "00 17 * 12 1")
  _("12,14,13,12:20,10,30", "20,10,30 12,14,13,12 * * *") # TODO: sort
  _("*-1/2-1,3 *:30", "30 * 1,3 1/2 *")
  _("03-05 08:05", "05 08 05 03 *")
  _("08:05:00", "05 08 * * *")
  _("05:40", "40 05 * * *")
  _("Sat,Sun 12-* 08:05", "05 08 * 12 0,6")
  _("Sat,Sun 08:05", "05 08 * * 0,6")

  def _(systemd):
    self.assertRaises(Exception, systemd_to_cron, systemd)
  _("test")
  _("")
  _("7")
  _("121212:1:2")

  _("Wed *-1")
  _("08:05:40")
  _("2003-03-05")

  _("0-1"); _("13-1"); _("6/4-1"); _("5/8-1")
  _("1-0"); _("1-32"); _("1-4/3"); _("1-14/18")
  _("24:0");_("9/9:0"); _("8/16:0")
  _("0:60"); _("0:22/22"); _("0:15/45")

if __name__ == '__main__':
  import unittest
  unittest.TextTestRunner().run(type('', (unittest.TestCase,), {
    'runTest': test})())
