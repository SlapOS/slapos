* Report, from pbs and from clone, when a backup failed
* Make sure, when a takeover is done, that "importer" script finishes to run while importer instance is changed into exporter.
* Test that, after a successful backup/takeover, another backup is possible and will be successful.

* PBSs and mirrors should monitor/replace themselves
* Report errors from backup

* If a PBS master is down and then back again, it might want to participate in the ongoing election, then.. what happens?
* If the network is partitioned (the two backups don't see each other, but each can see the slapos master) there will be two concurrent elections taking place, with two winners and two renames.

* How to ensure "synchronization" between two main instances? example: Wordpress: mysql is down, then replaced, then inconsistency between apache and the new mysql
* How to deal with big data? I.e how to have working backup/restore system of 1TB data with slow connection?
* How to be sure that elected importer contains a/ the latest data and b/ has finished to pull. We should prevent importer not having a/ and b/ to become the main.

* Should we crypt backed up data?

* If a PBS is lost, a new PBS should be created from another one, in order ot keep history

* If an election takes place and asks for a rename, but no slapgrid is running (or takes too much) then another election will take place
and ask to rename the previously selected winner, thus breaking the resiliency system.
