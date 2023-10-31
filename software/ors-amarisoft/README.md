# ORS Amarisoft software release

How to deploy from scratch

  1. Install Amarisoft binaries in /opt/amarisoft/v20XX-XX-XX with folders:
     * enb: needs to containt libraries from trx_sdr
     * trx_sdr
     * mme
  2. Install ors playbook
  3. Deploy this SR

## Generated buildout configurations and json input schemas

XXX update

 * instance-ue-input-schema.json

Since there are multiple ors-amarisoft softwares releases and software types, the following files are
generated with jinja2 templates with the render-templates script before being pushed to gitlab:

 * instance-tdd-enb-input-schema.json
 * instance-fdd-enb-input-schema.json
 * software-fdd.cfg
 * software-tdd.cfg.json
 * instance-tdd-gnb-input-schema.json
 * test/testFDD.py
 * test/testTDD.py
 * software-tdd.cfg
 * instance-fdd-gnb-input-schema.json
 * software-fdd.cfg.json

These files should not be modified directly, and the render-templates scripts should be run along
with update-hash before each commit.

## Services

We run 2 binaries from Amarisoft LTE stack:

 * **lteenb** - eNodeB software is the server accepting connection from UI (user interfaces)
 * **ltemme** - Mobile Management Entity in other words core network which handles orchestration of 
   eNodeBs in case UI switches from one to another
 
Those binaries are started in foreground, originaly in screen. We don't want the binaries inside one
screen because then we cannot easily control their resource usage. Thus we make 2 on-watch services.

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
