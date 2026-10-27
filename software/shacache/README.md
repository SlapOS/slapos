# Shacache

This software release deploys ERP5 (Python 3) as a shacache and shadir
server. It is the `erp5` software release with these changes:

* The default business templates are `erp5_full_text_mroonga_catalog` and
  `networkcache_erp5`. `networkcache_erp5` installs `erp5_web_shacache` and
  `erp5_web_shadir`.
* Zope accepts request bodies up to 5GB. The default of Zope is 1GB. Use the
  `form-disk-limit` key of the `dos-protection` parameter of
  `zope-partition-dict` to change it.
* ERP5 comes from a branch that sends big files from the ZODB a bit at a time.
  The memory of Zope does not increase with the size of the file.

All the instance parameters of the `erp5` software release are available.

## Setup after the first deployment

1. In `web_site_module`, create a Web Site with the skin selection `SHACACHE`,
   and publish it. Do the same for a Web Site with the skin selection
   `SHADIR`.
2. Create a Person with an ERP5 Login for each client that uploads.
3. Give this Person an Assignment in the group `shacache` and an Assignment in
   the group `shadir`. Open the Assignments.

Clients download from `<web site URL>/<sha512>` without authentication. They
upload with a `POST` to the web site URL, with the login and password.

## Limits

Each download keeps one Zope thread busy until the end of the transfer. Set
`thread-amount` in `zope-partition-dict` for the number of downloads that can
run at the same time.
