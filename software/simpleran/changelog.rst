Changelog
=========

Version 1.0.412 (2025-05-02)
-------------

* Fix published websocket URL missing "/websocket"

Version 1.0.409 (2025-04-07)
-------------

**SIM Cards:**

* Use MSIN and PLMN instead of IMSI in sim parameters
* Auto-fill IMPI and IMPU based on PLMN and MSIN
* Support Amarisoft default SIM / eSIM profile

**eNB / gNB:**

* Re-organize connection parameters names
* Limit all log sizes and improve log rotation
* Control TX power directly in dBm instead of using tx_gain
* Set frequency by inputing frequency directly instead of earfcn / nr_arfcn
* Fix 8UL 1DL mamimum uplink configuration
* Fix TX power offset: this is important for UE's to correctly adjust their power based on what they receive

Version 1.0.399 (2025-02-20)
-------------

* Publish SSB NR ARFCN
* Fix SSB NR ARFCN computation, affects band N79
* Fix bug affecting N77 ORS

Version 1.0.390 (2025-01-21)
-------------

* Fix integration with our KPI calculation and storage platform (update to 1.0.390+ is necessary for KPI computation)

Version 1.0.384 (2024-12-16)
-------------

* Add promise to check if GPS is synchronized when enabled

Version 1.0.383 (2024-12-11)
-------------

* Amarisoft version is now required to be 2024-11-21 for this version of the software release
* Support handover between 4G and 5G
* Generate unique values on ORS for the following parameters:
  - eNB ID
  - gNB ID
  - Cell ID
  - Physical Cell ID
  - Root Sequence Index
* Add PDN list parameter in core-network
* Allow to configure multiple iperf3 servers
* Publish MAC address

Version 1.0.379 (2024-10-09)
-------------

* Give access to Amarisoft GUI: add proxy to make Amarisoft websocket API accessible through a public SSL Websocket URL protected by a password

Version 1.0.371 (2024-10-09)
-------------

* rename ors-amarisoft to simpleran

**UE simulator:**

* add UE mode for ORS (experimental)

**eNB / gNB changes:**

* add compatibility with our KPI calculation and storage platform
* support setting source S1AP address and port
* display current frequency and band
* add promise testing if frequency is out of bounds (ORS only)
* fix eNB configuration for 1.4MHz bandwidth
* change default RX gain to 25
* add useful information in eNB / gNB logs: host ID, FPGA version and kernel version
* keep old eNB / gNB radio logs

**Core Network changes:**

* support external HSS (S6), tested only for LTE
* add multicast and broadcast
* display the list of IMSI in the UE database

Version 1.0.361 (2024-05-29)
-------------

* Support BBU controlling multiple RUs with one or more CPRI boards
* Code refactorization (to support BBUs with multiple RUs)
* Support IMS for Amarisoft >= 2024-05-02, which is needed for 5G support on some phones
* Add high UL TDD config (TDD CONFIG 4, supported on more UEs than the maximum UL TDD config)
* Add fixed-ips option for core network

Version 1.0.344 (2023-11-03)
-------------

* Set dpc_snr_target to 25 for PUSCH also

Version 1.0.341 (2023-10-20)
-------------

* Publish amarisoft version and license expiration information
* Add network name parameter

Version 1.0.340 (2023-10-20)
-------------

* Update RRH firmware and reset

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
