
The following is a detailed list of the changes made to the Zimbra sources,
and also explains parts of the buildout.cfg profile.

If you only need to build Zimbra, you may skip this and just read INSTALL.txt



================================
Changes in the SlapOS repository
================================

The zimbra branch includes two additional components:

 - components/pax
 - components/p7zip

Also, in the software/zimbra directory:

 - buildout.cfg
   tested and documented in INSTALL.txt

 - junixsocket-hooks.py
   Used to compile junixsocket.
   Before the build, it patches build.xml to point to the junit jar file.
   After the build, it copies the compiled library where needed.

 - authbind_2.1.1_amd64.deb
   Pre-compiled backport of authbind built under Ubuntu 12.04.
   Needed for IPv6, because only versions >= 2.0 support it.

 - software.cfg
 - instance.cfg
   Experimental. Ignore them.



================================
Changes in the Zimbra repository
================================

The first problem with the official Zimbra repository has been usage of Perforce.
Since Perforce keeps no state on the client, it has poor performance and very
poor visibility for anonymous users.

We have forked the most recent release (8.0.4) and made it available at
https://git.erp5.org/gitweb/zimbra.git?js=1

Unfortunately, the 8.0.4 tag was created a few days later than the binary
release, and a few bugs had been introduced in the meantime.
This means the 8.0.4 tag from the official zimbra sources does not build without changes.
Our fork contains unofficial bug fixes in both 'vanillabuild' and 'authbind' branches.

 - vanillabuild branch
    https://git.erp5.org/gitweb/zimbra.git/shortlog/refs/heads/vanillabuild?js=1
    This is basically a fixed version of the upstream build.
    The 'vanillabuild' branch is able to build on one of the supported platforms (tested mainly with Ubutnu 12.04)
    in the default zimbra location - /opt/zimbra which should also be the $HOME of the user 'zimbra'.
    The build process creates *.deb files that need to be installed and configured as root.
    Most zimbra processes and third party components will then run as root and switch to the 'zimbra' user
    (or postfix, or postdrop, and so on).
    This build has been tested with both IPv4/IPv6, in different configurations (ldap only, mta only, store only,
    and all-in-one).

 - authbind branch
    https://git.erp5.org/gitweb/zimbra.git/shortlog/refs/heads/authbind?js=1
    This does NOT build with the conventional method, but will work with buildout.
    The rest of this documentation describes the changes made to the 'authbind' branch.
    which uses buildout, and can build and be deployed as a regular user, with no
    need for root access except for some preparatory steps.




Types of changes
----------------

While building or running an application as complex as Zimbra, there are many
scripts and processes that make one or more of the following assumptions.

This order roughly reflects the level of difficulty encountered in the project,
from the esiest to solve, to the hardest.

Assumption 1: the system can be prepared by a root user, with specific system-level
              configuration, before running the build.

    This is not considered a big issue if the required configuration
    is easily done or, better, automated.

    For Zimbra, we have reduced the steps to:

    - DNS setup (A and MX records) and /etc/hosts
    - raise maximum number of open files (ulimit -n)
    - rsyslog/syslog configuration
    - remapping ports lower than 1024 that are required by RFCs (IMAP, POP...)

    These must, unfortunately, be performed by hand (see INSTALL.txt),
    and are outside the scope of the build process itself.
    The ulimit has also been raised in the slapprepare master branch.


Assumption 2: many libraries can be provided by apt-get, rpm, zypper and so on.

    Wherever possible, changes have been made to use libraries and tools
    provided by the Zimbra build itself (better option), or by SlapOS components.
    Both building and actually running the system can require these.
    A couple of files are needed to setup environment variables,
    both while building (done automatically by buildout) and while running
    the Zimbra system or administration scripts.
    In the INSTALL.txt, you will find references to
        zbuild/environment.sh
    and
        zbuild/home/.bashrc

    These need to be executed with the '.' (source) command before any activity.

    A few packages could not be provided by zimbra or slapos, or could not be detected
    by the makefiles.





[to be continued]


