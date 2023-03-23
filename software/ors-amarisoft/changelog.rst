Changelog
=========

Version 1.0.317 (2023-04-18)
-------------

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

