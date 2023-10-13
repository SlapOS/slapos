Changelog
=========
Version 1.0.339 (2023-10-16)
-------------
* Lopcomm firmware update
* RRH reset (reboot) function added
* Fix cpri_tx_dbm parameter
* Print RRH IPv6 and firmware information

Version 1.0.336 (2023-09-25)
-------------

* Support on Lopcomm RRH via netconf
  - Lopcomm firmware auto-upgrade and verification
  - Up to 4T4R
  - Netconf access verification promise
  - PA output power alarm
  - Default value added for B1
* fix some bugs

Version 1.0.332 (2023-09-04)
-------------

* Add 4G Intra eNB Handover
* Add public websocket URL protected by password
* Reorganize softwares: ORS now need to use software-tdd-ors or software-fdd-ors
* Support multiple cells for BBUs

Version 1.0.330 (2023-07-19)
-------------

* Change Slice Differentiator input parameter to hexadecimal representation
* Add TDD Configurations with maximum uplink
* Modify reference power signal to improve radio link over long distances
* Add Tracking Area Code (TAC) parameter to eNB
* Publish useful values:
  - Frequency and band
  - Current TX and RX gain
  - Estimated TX power in dB and W based on https://handbook.rapid.space/rapidspace-ORS.tx.gain
  - ORS frequency range rating
  - ORS version

Version 1.0.326 (2023-06-14)
-------------

* Add DHCP for Lopcomm RU's M-plane
* Add support for FDD
* Add more parameters and tests for lopcomm RU

Version 1.0.323 (2023-05-17)
-------------

* Add support for first version of MCPTT (Mission Critical Push To Talk)

Version 1.0.321 (2023-05-05)
-------------

* Remove RRH options from ORS software releases
* Add custom TDD UL DL configuration
* Add time_to_trigger and a3_offset gNB XnAP and NGAP NR handover options

Version 1.0.320 (2023-04-26)
----------------------------

* Add support for inter gNB XnAP and NGAP NR handover

Version 1.0.317 (2023-04-18)
---------------------------

* Add support for inter gNB NR handover

Version 1.0.316 (2023-04-14)
----------------------------

* Remove enb-epc, gnb-epc and epc software types, the software types are now:
    - enb
    - gnb
    - core-network (replaces epc software type)

Version 1.0.312 (2023-03-20)
----------------------------

* Add promise to test if reception is saturated
* Add gadget from SR to display on Monitor APP
* Add IMSI in connection parameters when SIM gets attached
* Add carrier control for Lopcomm RRH

Version 1.0.308 (2023-02-09)
----------------------------

* Add support for IPv6 in UEs if available
* Use latest amarisoft version on ORS if available
* Add gnb_id_bits parameter
* Use promises from slapos.toolbox repository
* Rotate and add timestamps in enb-output.log, gnb-output.log, mme-output.log etc...
* Add support for Lopcomm RRH
* Remove UE power emission limitation
