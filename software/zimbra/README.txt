
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
    The build process creates .deb files that need to be installed and configured as root.
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
    by the makefiles. They have to be provided by the linux distribution.

        - libcloog-ppl0: CLooG is a software which generates loops for scanning Z-polyhedra.
            This library is used by GCC and implements the "graphite optimization"
            used to build libmemcached and opendkim. The optimization could probably be
            disabled and the dependency removed.

        - libncurses5-dev
            Although it is usually easy to provide a custom ncurses to a makefile/configure,
            this was not the case for heimdal, and would need changing the configure scripts.

        - gcc-multilib
            Needed to compile junixsocket without patches. It may be not needed if the skip32
            flag is provided to ant (see build.xml)

    As noted, such package dependencies can probably be removed with a little further research.


Assumption 3: scripts provided by the packaging system (preinst, postinst, /etc/init.d/*)
              will be run, as root, when necessary

    Many applications have build procedures that can also install packages in a "target" directory,
    where it can be directly configured and run.
    In the case of Zimbra, this would be a "developer build" which would not be
    configured for production purposes.
    The standard Zimbra build populates /opt/zimbra (in our case, zbuild/home) then it take parts
    and pieces of that content and creates .deb or .rpm files. Some parts (i.e. mysql) will be split
    or be part of multiple packages.

    The buildout parts that deploy Zimbra (zimbra-deploy-ldap and so on) open the .deb packages
    and extract the data.tar.gz contents, therefore 'faking' the presence of them into the system,
    but there is no way to run the control scripts as a regular user.
    Typical tasks performed by preinst and postinst scripts are:

        - set up and update symlinks: /opt/zimbra/{bdb, mysql, jdk..}
        - set up directories to hold data: log, redolog, store, index, backup..
        - creating configuration files: postfix/conf/main.cf, etc.
        - removing obsolete config files or databases: i.e. /opt/zimbra/sleepycat
        - set up /etc/sudoers for the zimbra user: i.e. in zimbra-core.postinst
        - set up /etc/pam.d and /etc/security
        - set up /etc/ld.so.conf, run ldconfig
        - set up /etc/rc*.d with the S## and K## files
        - set up crontab
        - java -client -Xshare:dump (what is this for?)
        - set up a tmpfs in /etc/fstab and mount it under amavisd/tmp
        - patch db/db.sql with the hostname of the system before initializing the database

    All of these need to be examined, reverse engineered and replicated in the buildout.cfg
    (the simplest case being the many mkdir and ln commands).

    Other tasks which we don't need to replicate are:

        - set up /etc/prelink.conf, run prelink
        - create users and groups for zimbra, postfix, postdrop
        - running zmfixperms

    New releases of Zimbra, even minor ones, add more tasks to the control files, depending on
    new components, data migrations and environment constraints.


Assumption 4: scripts, binaries, libraries, configuration files and databases will be present
              under specific filesystem locations (like /opt/zimbra/ or /etc)

    Although it is possible to specify a $ZIMBRA_HOME environment variable to
    attemp a build targeting a different directory, that is seldom used, and
    hardcoded pathnames abound in makefiles, scripts and even Java code, with
    literally thousands of references to /opt/zimbra.

    A naive approach that replaces /opt/zimbra with the desired target would break several scripts
    in ways that are not possible to predict and hard to debug.

    A layered approach has been applied:


    - when possible, replace /opt/zimbra with ${ZIMBRA_HOME} in bash
        (and /usr/local/java with JAVA_HOME)

        Pay attention to the quotes. Inside shell scripts, "$VAR" does variable
        replacement, but '$VAR' does not. Therefore, in order to replace
        '/opt/zimbra' the quoting must be changed as well: "${ZIMBRA_HOME}"
        and not '${ZIMBRA_HOME}'. Proper escaping of quotes must be applied
        in case of embedded command strings, and strings written to files that
        will later be executed.

        Make the variable mandatory and remove assignments to the old default.
        An error is returned in buildThirdParty.sh if ZIMBRA_HOME is not set up.


    - use $(ZIMBRA_HOME) in makefiles
        Be careful of using proper parens: $() and not ${}

        Makefiles will automatically use the envvar if defined, but when debugging
        we need to build individual Third Party packages, and be sure that
        environment.sh has been sourced.
        By removing the many "ZIMBRA_HOME ?= /opt/zimbra" from all the Makefiles,
        we make sure we remember to use of environment.sh


    - plain sed replacement
        Before starting the build, all remaining /opt/zimbra occurrences are replaced
        with a global

        sed 's#/opt/zimbra#${ZIMBRA_HOME}#g'

        (see buildout.cfg:[zimbra-sources-search-replace])


    - replace s/../../ with s|..|..| in bash (and m|...| in Perl)
        There are several occurences of /opt/zimbra in regular expressions, where
        it appears as \/opt\/zimbra.

        The delimiter has been changed in bash and Perl scripts, therefore
        a s/\/opt\/zimbra\/whatever/ become s|/opt/zimbra/whatever| and can be
        replaced by the sed command described above.

        Pay attention to Perl: regexps can be 'naked', therefore an expression like

            $cmdline =~ /\/opt\/zimbra\/db/

        would be changed to

            $cmdline =~ m|/opt/zimbra/db|

        As always, in bash, look the quote characters around the regexp, if present,
        and change them from ' to " where needed.


    - sed replacement for awk

        Unfortunately, awk cannot use other characters in place of the slash delimiter.
        A more complex sed substitution is performed for these cases:

            ZIMBRA_HOME_WITH_BACKSLASHES=`echo $ZIMBRA_HOME | sed "s#/#\\\\\\\\\\\\\\\\/#g"`
            SUB3="s#\\\\/opt\\\\/zimbra#$ZIMBRA_HOME_WITH_BACKSLASHES#g"


    - sed replacement for Java code

        There is also a case of '/opt/zimbra' that is built by string composition in Java.

        A file-specific substitution is applied here:

            find . -name LocalConfig.java -exec sed -i 's#= FS + "opt" + FS + "zimbra"#= "${:ZIMBRA_HOME}"#g' {} \;

        A grep search for all occurrences of 'opt' in Java sources may help to detect similar cases.



Assumption 5: processes can be run by a specific user (zimbra, postfix, postdrop) or as root

    The first issue posed by this assumption is that we need to allow the application to
    use the resources it needs. Giving permissions to regular users through linux
    capabilities is a possible approach, but only solves a part of the use cases.

    A limitation of setcap is described in
        http://stackoverflow.com/questions/9843178/linux-capabilities-setcap-seems-to-disable-ld-library-path

    The second issue is the amount of code that was written in order to report errors if the current
    user does not match, call processes through su/sudo, change file permissions, set up usernames and uids
    in configuration files, and so on. This code may be part of the build process, the configuration/deployment
    scripts, or administration scripts.

    The changes can be grouped by purpose:

      - Removing user checks
        The first thing to remove are the parts of code that abort a script when run by a different user.
        This change should generally be applied as soon as possible, so that further permission problems can be detected.

        The code often looks like

            if [ x`whoami` != xzimbra ]; then
              echo Error: must be run as zimbra user
              exit 1
            fi

        or with `id -un` in place of whoami.
        In Perl, the checks can take very different forms, which are hard to find with grep:

            ($>) and usage();


      - Removing usage of su/sudo

        This goes both ways: scripts run by root that need to run scripts as zimbra, and vice-versa.
        For the latter, Zimbra requires /etc/sudoers to be properly set up:

        %zimbra ALL=NOPASSWD:/opt/zimbra/libexec/zmstat-fd *
        %zimbra   ALL=NOPASSWD:/opt/zimbra/openldap/libexec/slapd
        %zimbra   ALL=NOPASSWD:/opt/zimbra/libexec/zmslapd
        %zimbra   ALL=NOPASSWD:/opt/zimbra/postfix/sbin/postfix, /opt/zimbra/postfix/sbin/postalias,
                               /opt/zimbra/postfix/sbin/qshape.pl, /opt/zimbra/postfix/sbin/postconf,
                               /opt/zimbra/postfix/sbin/postsuper
        %zimbra   ALL=NOPASSWD:/opt/zimbra/libexec/zmqstat,/opt/zimbra/libexec/zmmtastatus
        %zimbra ALL=NOPASSWD:/opt/zimbra/libexec/zmmailboxdmgr
        %zimbra ALL=NOPASSWD:/opt/zimbra/bin/zmcertmgr

        We have removed all the explicit calls to sudo.
        Sometimes it's as easy as removing the 'sudo' word before a command, but at times the
        subprocess behavior must be retained, so that

            $SU = "su - zimbra -c -l ";

        becomes

            $SU = "bash -c ";

        While applying this kind of change, string quoting/backquoting and escaped characters
        may need to be adjusted.


      - Configuration changes
        Users "zimbra", "postfix" and "postdrop" are referenced in the configuration files
        used by postfix, opendkim, amavis, clamd, dspam.
        Some of these files are provided as templates and need to be patched by sed replacement
        (see buildout.cfg:[zimbra-sources-search-replace]).
        The actual configuration files are written by zmconfigd.


      - Ad-hoc patches to C code
        Three patches to postfix are provided, to avoid using initgroups(3), seteuid(2),
        setgid(2) and explicit user checks.

        A patch is also needed for the mailbox wrapper (zmmailboxdmgr) to avoid the stripping
        of LD_PRELOAD from the environment variables.
        The stripping of such variable is a security need when zmmailboxdmgr runs as root,
        but we don't, so we allow it because authbind relies on it to preload libauthbind.so


      - Removed calls to chown/chmod and zmfixperms
        This required directly changing permissions of files in the repository to allow +x.


      - Granting access to IP ports lower than 1024
        This is a common requirement, and port forwarding through iptables is not always possible.
        The only solution that we found working with ipv4/ipv6, with all versions of Java and allows
        LD_PRELOAD/LD_LIBRARY_PATH usage is the authbind package.
        Versions 1.x only work with IPv4, therefore we backported 2.1.1 to Ubuntu 12.04 and provided
        it together with the buildout.cfg




[to be continued]


