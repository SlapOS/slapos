Upgrade tests for KVM software release

Deploys the standalone, resilient and cluster instances with a released KVM
software release, then requests them on the software release of the checkout and
asserts that they keep running and that the needed migrations happened.

Bump `old_software_release_url` in `test.py` as releases advance.
