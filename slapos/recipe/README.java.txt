java
====

    This recipe downloads and installs java in your buildout.

Buildout configuration:
-----------------------

    Add this section to your buildout configuration::

        [buildout]
        parts =
            ... your other parts ...
            java
        ...

        [java]
        recipe = slapos.cookbook:java

    By default it will fetch Java 6u25, but you might want to install from another location or another version like this::

        [java]
        recipe = slapos.cookbook:java
        download-url = ftp://location/to/self-extracting/java.bin

    Or you can install openjdk instead.

        [java]
        recipe = slapos.cookbook:java
	flavour = openjdk


Notes:
------

    This recipe only works with linux at the moment

    This recipe requires rpm2cpio and cpio to be installed on your system.

Authors:
--------

    Original author: Cedric de Saint Martin - cedric.dsm [ at ] tiolive [ dot ] com

    Inspired by : z3c.recipe.openoffice made by Jean-Francois Roche - jfroche@affinitic.be

