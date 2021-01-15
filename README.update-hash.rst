update-hash
===========

``update-hash`` is a tool to assist software release developers in the management of ``buildout.hash.cfg`` files.

A lot of recipes which uses hashing for referenced files. Updating the hash results in part uninstallation and installation, which is desired behaviour, as the file might have to be redownloaded. By using ``update-hash`` with ``buildout.hash.cfg`` the developer does not have to do the calculations and updates manually, just calling the tool is enough.

Generally each Buildout profile which references some file shall use this approach to improve development process and minimise risk of using incorrect data from such entires.

Working with ``buildout.hash.cfg``
----------------------------------

``buildout.hash.cfg`` files are buildout-style simplified configparser files to have a easy way to update MD5 hashes of provided files for download. They look like::

  [section]
  md5sum = <hash>
  filename = <relative-path>

Where ``<hash>`` is an automatically calculated checksum of ``<relative-path>``.

Then ``buildout.hash.cfg`` can be included in software profile by ``extends`` of ``[buildout]`` section, and the section's ``md5sum`` and ``filename`` can be used.

Special cases of ``filename`` key
---------------------------------

In case if section recipe has special unwanted behaviour for ``filename`` field the ``_update_hash_filename_`` key can be used like::

  [section]
  md5sum = <hash>
  _update_hash_filename_ = <relative-path>

Working with ``update-hash``
----------------------------

In order to update the ``buildout.hash.cfg`` one just need to call ``update-hash`` while being in the directory containing the file.
