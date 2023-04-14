# ORS Amarisoft software release

How to deploy from scratch

  1. Compile and install kernel module lte_trx_sdr by `# cd trx_sdr*/kernel/ && make && sh init.sh`
  2. Make sure to have "create_tun = True" in /etc/opt/slapos/slapos.cfg
  3. Install ors playbook
  4. Deploy this SR

## Generated buildout configurations and json input schemas

Since there are many ors-amarisoft softwares releases and software types, the following files are
generated with jinja2 templates with the render-templates script before being pushed to gitlab:

 * instance-tdd1900-enb-input-schema.json
 * instance-tdd1900-gnb-input-schema.json
 * instance-tdd2600-enb-input-schema.json
 * instance-tdd2600-gnb-input-schema.json
 * instance-tdd3500-enb-input-schema.json
 * instance-tdd3500-gnb-input-schema.json
 * instance-tdd3700-enb-input-schema.json
 * instance-tdd3700-gnb-input-schema.json
 * software-tdd1900.cfg
 * software-tdd1900.cfg.json
 * software-tdd2600.cfg
 * software-tdd2600.cfg.json
 * software-tdd3500.cfg
 * software-tdd3500.cfg.json
 * software-tdd3700.cfg
 * software-tdd3700.cfg.json

These files should not be modified directly, and the render-templates scripts should be run along
with update-hash before each commit.

## Services

instance.cfg is rather complicated because Amarisoft LTE stack consists of 4 binaries

 * **lteenb** - eNodeB software is the server accepting connection from UI (user interfaces)
 * **ltemme** - Mobile Management Entity in other words core network which handles orchestration of 
   eNodeBs in case UI switches from one to another
 * **lteims** - IP Multimedia System is another protocol such as LTE but designed for services over 
   IP. Please read http://www.differencebetween.com/difference-between-lte-and-vs-ims-2/
 * **ltembmsgw** - Multimedia Broadcast Multicast Services (Gateway) is technology which broadcast
   the same multimedia content into multiple IP addresses at once to save bandwidth.
 
Those binaries are started in foreground, originaly in screen. We don't want the binaries inside one
screen because then we cannot easily control their resource usage. Thus we make 4 on-watch services.


### MME

Is the core network.  This binary keep track of UEs and to which eNodeB they are currently connected.
It reroutes traffic when UE switches between eNodeBs.
MME also serves as a service bus thus all services must register within MME. 


### IMS

Service connected into MME bus. IMS handles circuit-ish services over IP whereas LTE would have
failed because it is intended as data-over-IP service.


### MBMSGW

MBMS Gateway is a standalone component connected to BMSC (Broadcast Multicast Service Centre), server 
supporting streaming content from providers, which is another component inside our core network not
provided by Amarisoft.
MBMS Gateway is connected to MME which then manages MBMS sessions.

## Gotchas!

**trx_sdr.so** provided from archive MUST be placed next to `lteenb` binary. This library is the
only one which does not follow standard `ld` path resolution.

**rf_driver** has to be compiled and installed. Inside trx_sdr/kernel folder issue `# make` to compile the
kernel module, and then `# ./init.sh` to create devices `/dev/sdr<N>` and insert compiled module.
