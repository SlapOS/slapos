Upgrade tests for the slapproxy software release

Deploys a slapproxy instance with a released software release, populates its
database through the nested proxy it serves (a normal instance and a shared
one), then requests the same instance on the software release of the
checkout and asserts that the proxy keeps running and that the previously
created data, and the ability to create new data, survive the database
schema migration.

Bump `old_software_release_url` in `test.py` as releases advance; the
comment next to it explains which older release is used and why.
