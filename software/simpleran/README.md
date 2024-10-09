# ORS Amarisoft software release

How to deploy from scratch

  1. Install Amarisoft binaries in /opt/amarisoft/v20XX-XX-XX with folders:
     * enb: needs to contain libraries from trx_sdr
     * trx_sdr
     * mme: needs to contain libraries from libs folder
  2. Install ors playbook
  3. Deploy this SR

## Services

We run 3 binaries from Amarisoft LTE stack:

 * **lteenb** - eNodeB software is the server accepting connection from UI (user interfaces)
 * **ltemme** - Mobile Management Entity in other words core network which handles orchestration of 
   eNodeBs in case UI switches from one to another
 * **lteims** - IP Multimedia Subsystem, for support of VoNR / VoLTE (only for amarisoft > 2024-05-02)
 
Those binaries are started in foreground, originaly in screen. We don't want the binaries inside one
screen because then we cannot easily control their resource usage. Thus we make 3 on-watch services.

### ENB / GNB

Is the eNodeB (4G) or gNodeB (5G). This binary handles the radio protocols and sends and receives
IQ samples to trx_sdr driver.

### MME

Is the core network.  This binary keep track of UEs and to which eNodeB they are currently connected.
It reroutes traffic when UE switches between eNodeBs.
MME also serves as a service bus thus all services must register within MME. 

## Gotchas!

**trx_sdr.so** provided from archive MUST be placed next to `lteenb` binary. This library is the
only one which does not follow standard `ld` path resolution.

**rf_driver** has to be compiled and installed. Inside trx_sdr/kernel folder issue `# make` to compile the
kernel module, and then `# ./init.sh` to create devices `/dev/sdr<N>` and insert compiled module.
