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

Updating hash automatically when editing files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to update the ``buildout.hash.cfg`` one just need to call ``update-hash`` while being in the directory containing the file.

To automate this one step further, a simple solution is to use a file watcher program to run ``update-hash`` every time a file is modified. For example, using `watchexec <https://github.com/watchexec/watchexec/>`_, the command to run is ``watchexec -i 'buildout.hash.cfg*' update-hash``.

Another possibility is to use a git pre-commit hook, that you can install either by following the instructions present in ``update-hash`` script itself to install manually, or by running ``npm install`` from the root of slapos repository, which will install all commit hooks defined in ``package.json``.


Solving git merge conflicts
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When merging branches or rebasing commits, conflicts in ``buildout.hash.cfg`` happen when the same file managed by update hash have been modified on both sides.

A companion tool is ``update-hash-mergetool``, that can be configued as a merge tool for git, then running ``git mergetool`` will automatically run ``update-hash`` to resolve conflicts within ``buildout.hash.cfg`` files.
The installation instructions can be found in the ``update-hash-mergetool`` script.
