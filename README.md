# NayuOS

This is a SlapOS recipe to build Chromium OS. It needs to be put in the <code>/srv/slapgrid/\<part\>/srv/runner/project/slapos/software/</code> directory.

## Requirements

*   sudo and git on the host (for now)
*   slapuser with sudo rights to execute the cros_sdk scripts (needed to access the chroot environment provided by Chromium OS)
in /etc/sudoers:
<pre><code>
\<slapuser\>       ALL= NOPASSWD: /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/clone-depot-tools/cros_sdk, /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/chromite/bin/cros_sdk, /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/chromite/bootstrap/cros_sdk, /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/chromite/scripts/cros_sdk.py, /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/chromite/scripts/cros_sdk.pyc, /srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/chromium/tools/depot_tools/cros_sdk
</code></pre>
*   the custom ebuilds of net-libs/miniupnpc, net-misc/babeld-re6stnet and net-misc/re6stnet in the custom_ebuilds directory

## Input
In the vifib parameters (softinst\<nb\>.host.vifib.net \> Services \> Parameters):

    * board / ex: peppy, swanky, ... (daisy won't work because of Mali drivers license)
    * branch / ex: release-R46-7390.B


## Output
The image will be produced in:
<code>/srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/parts/chromiumos/images/</code>
and the logs are in:
<code>/srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/var/log/cros_sources_dl.log</code> and <code>/srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/var/log/cros_build.log</code>

The script that download the sources and build is located in
<code>/srv/slapgrid/\<part\>/srv/runner/instance/\<inst_part\>/etc/run</code>