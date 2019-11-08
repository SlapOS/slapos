update-hash
===========

``update-hash`` is a development tool to automatically work with
``buildout.hash.cfg`` files.

Working with ``buildout.hash.cfg``
----------------------------------

``buildout.hash.cfg`` files are buildout-style simplified configparser files to
have a easy way to update MD5 hashes of provided files for download. They
look like::

  [section]
  md5sum = <hash>
  filename = <relative-path>

Where ``<hash>`` is an automatically calculated checksum of ``<relative-path>``.

Then ``buildout.hash.cfg`` can be included in software profile by ``extends`` of
``[buildout]`` section, and the section's ``md5sum`` and ``filename`` can be used.

Special cases of ``filename`` key
---------------------------------

In case if section recipe has special unwatned behaviour for ``filename`` field
the ``_update_hash_filename_`` key can be used like::

  [section]
  md5sum = <hash>
  _update_hash_filename_ = <relative-path>

Working with ``update-hash``
----------------------------

In order to update the ``buildout.hash.cfg`` it's enough to call ``update-hash``
while being in the file directory.
