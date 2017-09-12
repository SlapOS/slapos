# NayuOS

This is a SlapOS recipe to build NayuOS.

## License

GPL v2 or later

## Requirements

*   sudo on the host
*   environment variables need to be authorized to be propagated when cros_sdk calls sudo: `: Defaults        env_keep += "CROS_CACHEDIR DEPOT_TOOLS"`
*   slapuser with sudo rights to execute the cros_sdk scripts (needed to access the chroot environment provided by Chromium OS)
in /etc/sudoers (replace slapuser9 by your user, and release-R48-7647.B by the release you have chosen): `: slapuser9    ALL=NOPASSWD: /srv/slapgrid/slappart9/srv/runner/instance/slappart0/parts/chromiumos/release-R48-7647.B/chromite/bin/cros_sdk, /srv/slapgrid/slappart9/srv/runner/instance/slappart0/wrapper_bin/wrapper_cros_sdk, /bin/kill`

It's useful to have the right to kill cros_sdk processes, when needed. ;)

## Technical notes

After any change to the build process it is necessary to delete (using sudo)
the building environment at `~/srv/runner/instance/slappart0/parts/chromiumos/<TAG>`.

BEWARE that the web runner is serving images for the [official website](https://nayuos.nexedi.com).

NayuOS and ChromiumOS is "just" a version of Gentoo. Thus it uses `ebuild` packages
and anything installable in Gentoo can be installed to NayuOS too. Of course only
during OS build phase and one has to count with limited space.

### Upgrading (building new image)

Please read **Requirements** section carefully. After selecting your desired 
`release` from the list <https://chromium.googlesource.com/chromiumos/manifest/+refs>
it is **necessary** to add `sudo` rules for that release as shown there.


## Input

In the vifib parameters (softinst\<nb\>.host.vifib.net \> Services \> Parameters):

*   **board** / ex: peppy, swanky, ... Complete list of devices and board names on [chromiumOS developer guide](http://www.chromium.org/chromium-os/developer-information-for-chrome-os-devices)
*   **branch** / ex: release-R46-7390.B (you can find the release in the [Chromium OS source tree](https://chromium.googlesource.com/chromiumos/manifest/+refs))
*   **keep_cache** / yes|no (choosing "no" saves about 15Go of disk space per board, choosing "yes" will makes next build faster and less expensive in term of needed ressources because of not rebuilding everything)

//Choosing board daisy will accept all licenses for the daisy board build only, in order to use Mali drivers, see [chromium mailing list](https://groups.google.com/a/chromium.org/forum/#!topic/chromium-os-dev/Pf9ZG2itxWM)

## Output

Software release produces a build script `<instance_partition>/etc/run/cros_full_build`.

Build produces

*  Image: `<instance_partition>/parts/chromiumos/images/`
*  Compilation logs: `<instance_partition>/var/log/cros_sources_dl.log`
*  Build logs: `<instance_partition>/var/log/cros_build.log`


## External documents

*   [ `repo` command reference ](https://source.android.com/source/using-repo.html)
*   [ NayuOS official website ](https://nayuos.nexedi.com)
*   [ Board names list ](http://www.chromium.org/chromium-os/developer-information-for-chrome-os-devices)
*   [ crouton for chroot ](https://github.com/dnschneid/crouton) ([warning about verified boot](https://github.com/dnschneid/crouton/blob/2a1fc9da380650f47e2bcf37d00962bfb68c4830/installer/main.sh#L517-L536))

## Notes for possible improvements

*   [ Running virtual machines on your chromebook ](https://www.chromium.org/chromium-os/developer-information-for-chrome-os-devices/running-virtual-machines-on-your-chromebook)
*   to have a more common User Agent (the one of ChromiumOS/NayuOS is quite rare and identifies the user, see [studies of the EFF](https://panopticlick.eff.org/static/browser-uniqueness.pdf)), it seems possible to change the User-Agent flag for guest mode in the getOffTheRecord function, and adding a line (key "kUserAgent" , value "some common user agent" string). Then rebuild Chromium and [add it to NayuOS](https://www.chromium.org/chromium-os/developer-guide#TOC-Making-changes-to-the-Chromium-web-).
*   remove need of root priviledge for entering the chroot, maybe by using fakeroot in 'scripts/wrapper_sudo.in'?
*   change more options on Chromium OS "Privacy" part by default: there are [a few options](https://support.google.com/chromebook/answer/114836) which still use Google services
*   provide ChromiumOS package manager [ chromebrew ](https://skycocker.github.io/chromebrew/) by default
