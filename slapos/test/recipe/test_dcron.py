import unittest
from slapos.recipe.dcron import systemd_to_cron

class TestDcron(unittest.TestCase):
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
    _("*-1/2-1,3 *:30", "30 * 1,3 1-11/2 *")
    _("03-05 08:05", "05 08 05 03 *")
    _("08:05:00", "05 08 * * *")
    _("05:40", "40 05 * * *")
    _("Sat,Sun 12-* 08:05", "05 08 * 12 0,6")
    _("Sat,Sun 08:05", "05 08 * * 0,6")
    _("*:25/20", "25-45/20 * * * *")

    def _(systemd):
      self.assertRaises(Exception, systemd_to_cron, systemd)
    _("test")
    _("")
    _("7")
    _("121212:1:2")

    _("Wed *-1")
    _("08:05:40")
    _("2003-03-05")

    _("0-1"); _("13-1"); _("8/5-1")
    _("1-0"); _("1-32"); _("1-14/18")
    _("24:0"); _("8/16:0")
    _("0:60"); _("0:15/45")
