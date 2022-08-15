============
Edge testing
============

``edgetest`` is a special software type of monitor software release used for website monitoring by using bots.

It uses `surykatka <https://lab.nexedi.com/nexedi/surykatka>`_ and `check_surykatka_json <https://lab.nexedi.com/nexedi/slapos.toolbox/blob/master/slapos/promise/plugin/check_surykatka_json.py>`_ to monitor websites.

``surykatka`` provides a bot to query list of hosts and a JSON reporting system.

``check_surykatka_json`` is used in promises to provide monitoring information about the websites.

In order to monitor an url one need to:

 * request a monitor software release with ``edgetest`` software type, configured as described in ``instance-edgetest-input-schema.json``,
 * request a slave to monitor with ``edgetest`` software type, configured as described in ``instance-edgetest-slave-input-schema.json``.
