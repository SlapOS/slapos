tsn-demo
========

Software release to provide required scripts to run `Time-Sensitive Networking`
measurements.


setup
=====

To allow SlapOS to setup gpio pins, you need to add the following configuration
in ``/etc/udev/rules.d/99-gpio.rules``::

SUBSYSTEM=="gpio", KERNEL=="gpiochip*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:slapsoft /sys/class/gpio/export /sys/class/gpio/unexport ; chmod 220 /sys/class/gpio/export /sys/class/gpio/unexport'"
SUBSYSTEM=="gpio", KERNEL=="gpio*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:slapsoft /sys%p/direction /sys%p/value ; chmod 660 /sys%p/direction /sys%p/value'"

.. _Time-Sensitive Networking: https://1.ieee802.org/tsn/