tsn-demo
========

Software release to provide required scripts to run `Time-Sensitive Networking`_ motor demo.
This is an automation of `this demo`_.


setup
=====

To allow SlapOS to setup gpio pins, you need to add the following configuration
in ``/etc/udev/rules.d/99-gpio.rules`` :

.. code-block:: shell

    SUBSYSTEM=="gpio", KERNEL=="gpiochip*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:slapsoft /sys/class/gpio/export /sys/class/gpio/unexport ; chmod 220 /sys/class/gpio/export /sys/class/gpio/unexport'"
    SUBSYSTEM=="gpio", KERNEL=="gpio*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:slapsoft /sys%p/direction /sys%p/value ; chmod 660 /sys%p/direction /sys%p/value'"


tutorial
========

`A tutorial`_ describing how to use this SR is available.

.. _Time-Sensitive Networking: https://1.ieee802.org/tsn/
.. _this demo: https://www.osie-project.eu/P-OSIE.Blog.TSN.Motor.Control.Demo
.. _A tutorial: https://www.osie-project.eu/P-OSIE.Blog.TSN.Motor.Control.Demo.Software.Release