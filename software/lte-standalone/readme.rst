LTE eNodeB software release
###########################

This is a try for standalone unprivileged run of Amarisoft's LTE stack.

The successful setup consists of

  1. Ansible: compilation and installation of necessary kernel module: lte_trx_sdr
  2. Initialization run as root (either by "format" or manualy)
  3. Deployment of this Software Release.
  
Original install.sh script was replaced by software.cfg and instance.cfg to
setup the paths so that we can run more instances on one machine.


slapos.cookbook:wrapper modification
------------------------------------

This instance.cfg is using updated slapos.cookbook:wrapper with ``remove_pidfile`` 
and ``cleanup_command``. Both options add functionality to generated ``sh`` script
using ``trap`` for INT, TERM and KILL signal. 

 - ``remove_pidfile`` removes pidfile upon exit,
 - ``cleanup_command``runs arbitrary cleanup command specified by the user.


instance.cfg explained
----------------------
instance.cfg is rather complicated because Amarisoft LTE stack consists of 4 binaries

 * **lteenb** - eNodeB software is the server accepting connection from UI (user interfaces)
 * **ltemme** - base (core) network which handles orchestration of eNodeBs in case UI switches from
   one to another
 * **lteims** - no idea
 * **ltembmsgw** - no idea
 
Those binaries are started in foreground, originaly in screen. They *communicate with each other*
using ``stdin`` based on their inner state. Thus we use *named pipes* to enable the inteprocess
communication.

We don't want the binaries inside one screen because then we cannot easily control their resource
usage and we will not see them separately inside webrunner or have separate access to their services.

Every binary expects "log" command after startup. Let's show it on ``mme`` binary.

 # ``lte-mme-log`` cleans up old logs
 # ``lte-mme-socket`` opens a socket using mkfifo
 # ``lte-mme-service`` launches the actual mme binary when the socket is available
 # ``lte-mme-service-log`` writes the "log" command into mme binary when it launches

One good example is script ``lte-register-ims-with-mme`` which registers newly started ``ims``
within ``mme`` using mentioned socket.
