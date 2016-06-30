mkdirectory
===========

mkdirectory loops on its options and create the directory joined

.. Note::

   Use a slash ``/`` as directory separator. Don't use system dependent separator.
   The slash will be parsed and replace by the operating system right separator.

   Only use relative directory to the buildout root directory.

The created directory won't be added to path list.
