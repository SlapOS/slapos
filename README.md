# NayuOS

This is a SlapOS recipe to build NayuOS. It needs to be put in the <code>/srv/slapgrid/\<part\>/srv/runner/project/slapos/software/</code> directory. The created directory is called <code>\<nayuos_build_dirname\></code> in this documentation.

## License

GPL v2 or later

## Requirements

*   sudo and git on the host (for now)
*   slapuser with sudo rights to execute the cros_sdk scripts (needed to access the chroot environment provided by Chromium OS)
in /etc/sudoers:
<pre><code>
\<slapuser\>       ALL= NOPASSWD: /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/clone-depot-tools/cros_sdk, /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/\<release\>/chromite/bin/cros_sdk, /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/\<release\>/chromite/bootstrap/cros_sdk, /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/\<release\>/chromite/scripts/cros_sdk.py, /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/\<release\>/chromite/scripts/cros_sdk.pyc, /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/\<release\>/chromium/tools/depot_tools/cros_sdk
</code></pre>
*   the custom ebuilds (such as net-libs/miniupnpc, net-misc/babeld-re6stnet, net-misc/re6stnet) in the nayuos-ebuilds directory. There is a [repo](https://lab.nexedi.com/nexedi/nayuos-ebuilds) for this purpose. It should be located into: <code>/srv/slapgrid/\<part\>/ srv/runner/project/slapos/software/\<nayuos_build_dirname\>/</code>.

## Input
In the vifib parameters (softinst\<nb\>.host.vifib.net \> Services \> Parameters):

*   board / ex: peppy, swanky, ... (choosing daisy will accept all licenses for the daisy board build only, in order to use Mali drivers, see [chromium mailing list](https://groups.google.com/a/chromium.org/forum/#!topic/chromium-os-dev/Pf9ZG2itxWM))
*   branch / ex: release-R46-7390.B
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
*   [ NayuOS official website ](https://www.nayuos.org)
*   [ crouton for chroot ](https://github.com/dnschneid/crouton) ([warning about verified boot](https://github.com/dnschneid/crouton/blob/2a1fc9da380650f47e2bcf37d00962bfb68c4830/installer/main.sh#L517-L536))

## Notes for possible improvements
*   [ Running virtual machines on your chromebook ](https://www.chromium.org/chromium-os/developer-information-for-chrome-os-devices/running-virtual-machines-on-your-chromebook)

*   to have a more common User Agent (the one of ChromiumOS/NayuOS is quite rare and identifies the user, see [studies of the EFF](https://panopticlick.eff.org/static/browser-uniqueness.pdf)), it seems possible to change the User-Agent flag for guest mode in the getOffTheRecord function, and adding a line (key "kUserAgent" , value "some common user agent" string). Then rebuild Chromium and [add it to NayuOS](https://www.chromium.org/chromium-os/developer-guide#TOC-Making-changes-to-the-Chromium-web-).
