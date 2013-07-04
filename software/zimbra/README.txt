
The following is a detailed list of the changes made to the Zimbra sources,
and also explains parts of the buildout.cfg profile.

If you only need to build Zimbra, you may skip this file and just read INSTALL.txt



================================
Changes in the SlapOS repository
================================

The zimbra branch includes additional components:

 - components/pax
 - components/p7zip
 - components/unzip
 - components/cloog-ppl (not used at the moment)

Also, in the software/zimbra directory:

 - buildout.cfg
   tested and documented in INSTALL.txt

 - junixsocket-hooks.py
   Used to compile junixsocket.
   Before the build, it patches build.xml to point to the junit jar file.
   After the build, it copies the compiled library where needed.

 - authbind_2.1.1_amd64.deb
   Pre-compiled backport of authbind built for Ubuntu 12.04.
   Needed for IPv6, because only versions >= 2.0 support it.

 - software.cfg
 - instance.cfg
   Experimental.



================================
Changes in the Zimbra repository
================================

Perforce is the official VCS tool of the Zimbra project.
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
    This does NOT build with the conventional method, but works with buildout, and can build
    and be deployed as a regular user, with no need for root access except for some preparatory steps.
    The rest of this documentation describes the changes made to the 'authbind' branch.



Types of changes
----------------

While building or running an application as complex as Zimbra, there are many
scripts and processes that make one or more (usually all) of the following assumptions.

The order roughly reflects the level of difficulty encountered in the project,
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

    All of these needed to be examined, reverse engineered and replicated in the buildout.cfg
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


    *) when possible, replace /opt/zimbra with ${ZIMBRA_HOME} in bash
       (and /usr/local/java with JAVA_HOME)

       Pay attention to the quotes. Inside shell scripts, "$VAR" does variable
       replacement, but '$VAR' does not. Therefore, in order to replace
       '/opt/zimbra' the quoting must be changed as well: "${ZIMBRA_HOME}"
       and not '${ZIMBRA_HOME}'. Proper escaping of quotes must be applied
       in case of embedded command strings, and strings written to files that
       will later be executed.

       Make the variable mandatory and remove assignments to the old default.
       An error is returned in buildThirdParty.sh if ZIMBRA_HOME is not set up.


    *) use $(ZIMBRA_HOME) in makefiles
       Be careful of using proper parens: $() and not ${}

       Makefiles will automatically use the envvar if defined, but when debugging
       we need to build individual Third Party packages, and be sure that
       environment.sh has been sourced.
       By removing the many "ZIMBRA_HOME ?= /opt/zimbra" from all the Makefiles,
       we make sure we remember to use of environment.sh


    *) plain sed replacement
       Before starting the build, all remaining /opt/zimbra occurrences are replaced
       with a global

       sed 's#/opt/zimbra#${ZIMBRA_HOME}#g'

       (see buildout.cfg:[zimbra-sources-search-replace])


    *) replace s/../../ with s|..|..| in bash (and m|...| in Perl)
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


    *) sed replacement for awk

       Unfortunately, awk cannot use other characters in place of the slash delimiter.
       A more complex sed substitution is performed for these cases:

           ZIMBRA_HOME_WITH_BACKSLASHES=`echo $ZIMBRA_HOME | sed "s#/#\\\\\\\\\\\\\\\\/#g"`
           SUB3="s#\\\\/opt\\\\/zimbra#$ZIMBRA_HOME_WITH_BACKSLASHES#g"


    *) sed replacement for Java code

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

      *) Removing user checks
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


      *) Removing usage of su/sudo

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
         may need to be adjusted, or parens added for grouping command pipes:

            su - zimbra -c "${zimbra_home}/bin/zmprov -m -l -- ${zmprov_opts} ${key} | sed  -e 's/^${key}: //' > ${tmpfile} 2> /dev/null" 2>/dev/null && mv -f ${tmpfile} ${file} 2> /dev/null

         becomes

            ( ${zimbra_home}/bin/zmprov -m -l -- ${zmprov_opts} ${key} | sed  -e "s/^${key}::* //" > ${tmpfile} 2> /dev/null ) && mv -f ${tmpfile} ${file}


      *) Configuration changes
         Users "zimbra", "postfix" and "postdrop" are referenced in the configuration files
         used by postfix, opendkim, amavis, clamd, dspam.
         Some of these files are provided as templates and need to be patched by sed replacement
         (see buildout.cfg:[zimbra-sources-search-replace]).
         The actual configuration files are written by zmconfigd.


      *) Ad-hoc patches to C code
         Three patches to postfix are provided, to avoid using initgroups(3), seteuid(2),
         setgid(2), setsid(2) and explicit user checks.

         A patch is also needed for the mailbox wrapper (zmmailboxdmgr) to avoid the stripping
         of LD_PRELOAD from the environment variables.
         The stripping of such variable is a security need when zmmailboxdmgr runs as root,
         but we don't, so we allow it because authbind relies on it to preload libauthbind.so


      *) Removed calls to chown/chmod and zmfixperms
         This also required directly changing permissions of files in the repository to allow +x.


      *) Granting access to IP ports lower than 1024
         This is a common requirement, and port forwarding through iptables is not always possible.
         The only solution that we found that works with IPv4/IPv6, with all versions of Java and allows
         LD_PRELOAD/LD_LIBRARY_PATH usage is the authbind package.
         Versions 1.x only work with IPv4, therefore we backported 2.1.1 to Ubuntu 12.04 and provided
         it together with the buildout.cfg
         With authbind, if the application /path/to/binary needs the privilege to bind low ports,
         it must be called as

            $ authbind /path/to/binary [...options...]

         or (as seen in bin/zmmailboxdctl) as

            $ authbind --deep /path/to/binary [...options...]

         The latter form is required to grant the privilege to future subprocesses as well.

         For openldap and postfix, we still use setcap inside the buildout.
         This requires the sudo password, and could be dispensed with, now that there is support for
         authbind. But it would require some changes to the wrapper scripts, as described above.



Other context-specific changes
------------------------------

In the script buildThirdParty.sh, explicit checks for the presence of required libraries
have been removed.

The script zmsetup.pl has been modified to look in $ZIMBRA_INSTALLED_PKGS for the list
of packages to setup. This would normally go through apt-get and detect what has been installed.

Other changes not described in the previous section:

    - clamav:
      Explicitly provide bzip2 from slapos.

    - cyrus-sasl
      The build of this component is bugged, because it uses libtool provided in /usr/bin
      instead of the one provided by Zimbra.
      Our changes fix this, and also explicitly reference the aclocal file with --system-acdir
      in ThirdParty/cyrus-sasl/zimbra-cyrus-sasl-build.sh

      For the same reason, the Thirdparty/Makefile build order
      has been changed to build libtool before cyrus-sasl.

    - mysql
      Compile mysql with the embedded yaSSL library, instead of openssl.
      Also, explicitly provide ncurses from slapos.

    - nginx / postfix:
      Explicitly provide libpcre from slapos.

    - perl
      SlapOS Perl: Build with -fPIC to allow linking with OpenLDAP Perl backend.
      Zimbra perl:
            Install the Devel::Trace module to help debug.
            Use the public cpan.yahoo.com mirror by default instead of the
            inaccessible, privat one at zre-matrix.eng.vmware.com
      Changed /usr/bin/perl shebangs, to /usr/bin/env or to $PERL_BINARY with a regexp.




==================
What did we learn?
==================

Overall, the Zimbra application suite has a clean architecture, and the build
system is not hard to modify/debug if a stable snapshot is used (which was not
the case at first). The only major improvement I would suggest to the upstream
maintainers is to make it easier to incrementally build third party packages,
instead of erasing everything every time, and building 24 applications and 80 perl
modules in a single shot.

Porting to buildout has however proven cumbersome and the correctness of all the
parts in the system is still unproven. A missing symlink to a certificate could make
opendkim ineffective, a missing archiver binary might render the antivirus system
unable to open many types of attachments, and so on.
Inside bash and perl scripts, many commands fail silently, or their stdout and
stderr is redirected to /dev/null and the status code is not checked.
This is still in the best case, when the failing command is in the script we want to run.

Sometimes the effects of a failing command can only be detected much later,
when running an application that runs with the default configuration instead of
the one created from the configuration templates, because there is a Java
daemon running a Jython script that should refresh them every few minutes, but runs
into busy loops because an environment variable was not properly set up (really
happened, took a while to fix).

So if we have a non-trivial application to bring into SlapOS tomorrow, how can
we better evaluate the complexity of the task?

The following are characteristics of a software project that are easy to verify,
and can raise early warnings.


 *) The use of Perforce or other cumbersome VCS

    While I don't deny the quality of the tool when used every day, it is not
    intuitive to most developers, not transparent (and very slow) to anonymous
    read-only users, and makes it difficult to propose improvements upstream.
    There are a few Zimbra mirrors on github and similar sites, but they all
    are all one-way, outdated, only track some branches, or have collapsed commits.
    Attemps to directly use a git-p4 bridge have been disappointing, both for
    lack of familiarity and for the limitations of the anonymous access.


 *) Support for a limited number of platforms

    Linux distributions supported by ZCS 8.0.4:

        Ubuntu 10.04 (deprecated), 12.04
        SUSE Linux Enterprise Server 11
        Red Hat Enterprice / CentOS 6

    Outside of this limited list, the build scripts *do* fail (i.e. on Ubuntu 13
    or OpenSuse) and **there is no documented way** to deploy a production instance
    without going through .deb or .rpm packages.

    For Zimbra, there is code to detect the distro inside get_plat_tag.sh which is
    a starting point, but more if..else ad-hoc code in spread all over the makefiles
    and administration scripts - but we only get to test them when we think the
    build has succeeded and deployed.

    Have a look at ZimbraNative/Makefile. There is code to specifically target
    OS/X 10.4 PowerPC, 10.5 i386, 10.6, 10.7 with different compiler flags, and yet OSX
    is not officially supported. Which ones have been recently tested?

    Generally - the bigger the system, the more limited the number of platforms it can
    be reliably built with. Very often, it's not only a matter of missing phone
    support, there are technical reasons. Or simply all the developers use Ubuntu, all
    the customers use CentOS.
    It is useful to manually build an application on several distributions,
    old and new, before attempting a port to buildout. Identify where the constraints
    are, and how they can be removed.


 *) Third party libraries and applications cannot be provided separately

    Not only does Zimbra provide its own mysql/openldap/perl/etc applications as part
    of the zimbra-core*.deb, zimbra-ldap*.deb and such packages, but they
    are expected to be installed in /opt/zimbra and compiled with a given set of features.
    If the official documentation stated that you need a working mysql instance somewhere,
    and just provide authentication credentials while running zmsetup.pl, it would be much
    easier to reuse the mysql/mariadb component from SlapOS.


 *) Several toolchains are employed

    Make, cmake, GNU autoconf/autotools/libtool, ant, cpan.. all of them in the
    same project may require a lot of searches for specific flags to provide in
    obscure cases.
    This is not a big issue if the build already targets several platforms, and
    there are hooks to provide locations for the required dependencies.
    Also watch out for ancient C software that is still using plain Makfile.
    Case in point: ftp://ftp.ucsb.edu/pub/mirrors/procmail/procmail-3.22.tar.gz


 *) The deployment step is complex, long or requires a lot of interaction.

    Let's say you are building the FooBar application.
    Hopefully, the build system can also deploy, and put a working application
    in /opt/foobar.

    If the build system creates .deb or .rpm packages, or .tar packages that need
    to be installed as root, watch out for control scripts: start/stop wrappers,
    daemon scripts and cron configuration files. Any functionality there might need
    to be examined and rewritten for buildout.

    Even if the build deploys directly in /opt/foobar, a later configuration step
    might be more compex than it seems.
    Zimbra requires to run zmsetup.pl - an interactive dynamic menu and sub-menu
    application that is very easy to use - it's magic! - totalling about 12000
    lines of perl and bash, with a complexity equivalent to 24000 lines of
    Python code.
    This configuration menu is the biggest red flag we have met so far.


 *) The application can auto-update itself, install plugins and extensions

    Can the application update itself from the Internet? If so, any change we make to
    the sources could be replaced by the new version. The new version may expect
    things to be in /opt/foobar instead of /srv/slapgrid, or may rely on values in
    /etc/ld.so.conf which can't be controlled in SlapOS, and so on.

    Even for simple things like themes and plugins, try to download a few of them and
    look for hardcoded pathnames, and bash/php/python code. Browser-side JavaScript
    is usually harmless (see zimlets in Zimbra).
    Don't overlook this point. If the application can be built, but the plugins
    don't work, a customer could quickly lose interest.


 *) Installing the application changes /etc/sudoers

    This might actually be useful to detect early which binaries and scripts will need to
    be run as root, or as specific users. Try to find the reason behind this requirement
    as soon as possible. Also see if setuid/setgid binaries have been installed.






Resources
---------

The following documents have been useful to build / debug third party libraries.

 autotools tutorial
    http://www.lrde.epita.fr/~adl/dl/autotools.pdf

 openldap administrator guide
    http://www.openldap.org/doc/admin24/ 

 very detailed explanation of shared libraries
    http://www.akkadia.org/drepper/dsohowto.pdf


