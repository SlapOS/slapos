import glob
import os
from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise


@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def sense(self):
    domain_list = (
      glob.glob('/sys/class/powercap/intel-rapl*/energy_uj') +
      glob.glob('/sys/class/powercap/amd-rapl*/energy_uj'))
    if not domain_list:
      # A warning, not an error: this is a hardware/virtualization
      # limitation (eg. a nested VM, as a test runner commonly is),
      # not something any operator action here can fix, so it must
      # not fail the promise.
      self.logger.warning(
        "No RAPL power domain found under /sys/class/powercap. "
        "This host's CPU may not support RAPL, this may be a "
        "virtualized host RAPL isn't exposed into, or the "
        "intel_rapl_msr/intel_rapl_common (or amd_energy) kernel "
        "module isn't loaded: energy-monitoring cannot produce "
        "real data on this node.")
      return
    unreadable = [
      path for path in domain_list if not os.access(path, os.R_OK)]
    if unreadable:
      self.logger.error(
        "%s found but not readable by this partition (eg. %s). "
        "The kernel restricts RAPL energy_uj to root by default "
        "since CVE-2020-8694/8695: the node operator needs to make "
        "them world-readable, eg. with a udev rule (see "
        "software/kvm/README.rst)." % (len(unreadable), unreadable[0]))
      return
    self.logger.info(
      "%s RAPL energy_uj file(s) found and readable." % len(domain_list))
