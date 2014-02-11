Watermarking Software Release
=============================

This Software Release is used by Hexaglobe to deploy their video "watermarking"
system.

This is basically just an nginx daemon compiled with a few custom modules and with
a custom configuration, and an "administration" nginx daemon.

This Software Release also supports some early version of the "edge" support
(i.e you request an instance of hexaglobe-watermarking, with "edge" software-type,
and this instance will itself request many instances of watermakring over the world, in a
"computing CDN" style).

