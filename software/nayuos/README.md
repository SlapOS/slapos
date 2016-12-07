# NayuOS

This is a SlapOS recipe to build NayuOS. It needs to be put in the <code>/srv/slapgrid/\<part\>/srv/runner/project/slapos/software/</code> directory. The created directory is called <code>\<nayuos_build_dirname\></code> in this documentation.

## License

GPL v2 or later

## Requirements

*   sudo on the host (for now)
*   some environment variables need to be authorized to be propagated when cros_sdk calls sudo:

: Defaults        env_keep += "CROS_CACHEDIR DEPOT_TOOLS"

*   slapuser with sudo rights to execute the cros_sdk scripts (needed to access the chroot environment provided by Chromium OS)
in /etc/sudoers (replace slapuser9 by your user, and release-R48-7647.B by the release you have chosen):

: slapuser9    ALL=NOPASSWD: /srv/slapgrid/slappart9/srv/runner/instance/slappart0/parts/chromiumos/release-R48-7647.B/chromite/bin/cros_sdk, /srv/slapgrid/slappart9/srv/runner/instance/slappart0/wrapper_bin/wrapper_cros_sdk, /bin/kill

It's useful to have the right to kill cros_sdk processes, when needed. ;)

## Input
In the vifib parameters (softinst\<nb\>.host.vifib.net \> Services \> Parameters):

*   board / ex: peppy, swanky, ... (choosing daisy will accept all licenses for the daisy board build only, in order to use Mali drivers, see [chromium mailing list](https://groups.google.com/a/chromium.org/forum/#!topic/chromium-os-dev/Pf9ZG2itxWM))
*   branch / ex: release-R46-7390.B (you can find the release in the [Chromium OS source tree](https://chromium.googlesource.com/chromiumos/manifest/+refs))
*   keep_cache / yes|no (choosing "no" saves about 15Go of disk space per board, choosing "yes" will makes next build faster and less expensive in term of needed ressources because of not rebuilding everything)


## Output
The image will be produced in:
<code>/srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/images/</code>
and the logs are in:
<code>/srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/var/log/cros_sources_dl.log</code> and <code>/srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/var/log/cros_build.log</code>

The script that download the sources and build is located in
<code>/srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/etc/run</code>

## External documents

*   [ <code>repo</code> command reference ](https://source.android.com/source/using-repo.html)
*   [ NayuOS official website ](https://www.nayuos.com)
*   [ crouton for chroot ](https://github.com/dnschneid/crouton) ([warning about verified boot](https://github.com/dnschneid/crouton/blob/2a1fc9da380650f47e2bcf37d00962bfb68c4830/installer/main.sh#L517-L536))

## Notes for possible improvements
*   [ Running virtual machines on your chromebook ](https://www.chromium.org/chromium-os/developer-information-for-chrome-os-devices/running-virtual-machines-on-your-chromebook)
*   to have a more common User Agent (the one of ChromiumOS/NayuOS is quite rare and identifies the user, see [studies of the EFF](https://panopticlick.eff.org/static/browser-uniqueness.pdf)), it seems possible to change the User-Agent flag for guest mode in the getOffTheRecord function, and adding a line (key "kUserAgent" , value "some common user agent" string). Then rebuild Chromium and [add it to NayuOS](https://www.chromium.org/chromium-os/developer-guide#TOC-Making-changes-to-the-Chromium-web-).
*   remove need of root priviledge for entering the chroot, maybe by using fakeroot in 'scripts/wrapper_sudo.in'?
*   change more options on Chromium OS "Privacy" part by default: there are [a few options](https://support.google.com/chromebook/answer/114836) which still use Google services
