proxy
=====

Implement minimalist SlapOS Master server without any security, designed to work
only from localhost with one SlapOS Node (a.k.a Computer).

It implements (or should implement) the SLAP API, as currently implemented in
the SlapOS Master (see slaptool.py in Master).

The only behavioral difference from the SlapOS Master is:

When the proxy doesn't find any free partition (and/or in case of slave
instance, any compatible master instance), it will throw a NotFoundError (404).
