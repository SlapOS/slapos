=========================
Contributing to Rapid.CDN
=========================

Developer documentation for the ``software/rapid-cdn`` Software Release.

Changelog (CHANGES.rst)
=======================

``CHANGES.rst`` is a functional changelog for CDN operators and users: each entry is a short, audience-tagged note (``[operator]`` / ``[user]``) about a behaviour or parameter change. Purely internal/developer changes are omitted.

The style is adapted from `Keep a Changelog <https://keepachangelog.com/en/1.1.0/>`_ and `Common Changelog <https://github.com/vweevers/common-changelog>`_, with these project-specific rules:

* Group by **audience**, not by change type: tag every entry ``[operator]`` or ``[user]``, one audience per entry. When a change affects both, write a separate ``[operator]`` entry and a ``[user]`` entry (repeating shared context is fine) so each reader follows only their own.
* Mark a breaking change with a bold ``**Breaking:**`` prefix, and list breaking entries first within their section.
* Cite the relevant merge request(s) and commit(s) as links (to lab.nexedi.com) after each entry.
* Link each version heading to its tag on lab.nexedi.com, and ``Unreleased`` to the compare against the last release.
* rapid-cdn is not Semantically Versioned: it ships with the shared, monotonic SlapOS ``1.0.<n>`` release tags, and releases with no rapid-cdn change are omitted.

Keeping the ``Unreleased`` section
----------------------------------

The top of ``CHANGES.rst`` always carries an ``Unreleased`` heading. While developing on the ``master`` branch, add your entry under ``Unreleased`` in the *same commit or merge request* as the change itself. Do **not** write a version number: the release number is not known until the release is cut.

Turning ``Unreleased`` into a version
-------------------------------------

A SlapOS Software Release is a tag of the ``1.0`` branch, named ``1.0.<latest>+1``, so the number is only fixed at release time. Neither ``update-rc`` (master → 1.0) nor ``release-sr`` (the tagging script) edits this file, and commits are only made on ``master`` — therefore the version heading is written by hand on ``master`` as the final commit before releasing:

1. Compute the next version (the same rule ``release-sr`` uses)::

     git tag | grep -E '^1\.0\.[0-9]+$' | sort -t. -k3,3n | tail -1   # latest; add 1

2. Rename ``Unreleased`` to ``1.0.<n> (YYYY-MM-DD)``, add a tag link line under it, and add a fresh, empty ``Unreleased`` heading on top. (The release table of contents is generated automatically by the ``.. contents::`` directive — no manual list to update.)
3. Commit and push to ``master``, then run ``update-rc`` and ``release-sr`` as usual; the tag freezes this file as-is.

The one condition to respect: no other ``1.0.x`` tag is created between steps 1 and 3 (the numbering is shared across all Software Releases). If one is, bump the heading to match the real tag before releasing.
