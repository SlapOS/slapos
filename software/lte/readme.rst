LTE eNodeB software release
###########################

Simple software release which starts LTE service upon instantiation.
LTE is managed by systemd and we are taking advantage of this.

It is necessary to install SlapOS from "amarisoft" branch because
it has modified ``slapos node format`` to give group ``slapsoft``
the rights to operate ``systemctl <start/stop/enable/disable> lte``.
