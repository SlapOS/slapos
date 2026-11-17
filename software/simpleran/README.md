# Simpleran software release

How to deploy from scratch

  1. Install ors playbook
  2. Deploy this SR

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

## External dependencies for ORS

Simpleran SR needs:

| Path                               | Use                      | How to remove (if possible )             |
|------------------------------------|--------------------------|------------------------------------------|
| /opt/amarisoft/init-sdr            | Init SDR driver          |                                          |
| /opt/amarisoft/get-amarisoft-info  | Get amarisoft info       |                                          |
| /opt/amarisoft/rm-tmp-lte          | Remove files in /tmp     | Configure amarisoft to disable this lock |
| /opt/amarisoft/init-enb            | Set performance governor | Do it in playbook                        |
| /opt/amarisoft/init-ue             |                          | Do it in playbook                        |
| /opt/amarisoft/init-mme            |                          | Do it in playbook                        |
| /opt/sdr/get-sdr-info              | Get SDR info             |                                          |
| /opt/simpleran/format-ims          | Format IMS slaptun       | Do it in slapformat                      |
