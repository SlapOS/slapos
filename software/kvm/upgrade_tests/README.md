Upgrade tests for KVM software release

Deploys the standalone, resilient and cluster instances with a released KVM
software release, then requests them on the software release of the checkout and
asserts that they keep running and that the needed migrations happened.

Bump `old_software_release_url` in `test.py` as releases advance; the comment
next to it explains which older releases were tried and why they are not used.

The virtual machines need a tap interface, so the suite skips itself on a node
which does not create them (`create_tap`), like a Theia runner: qemu refuses to
start when it is given an empty tap interface name.
