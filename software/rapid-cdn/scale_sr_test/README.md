# Rapid.CDN error-page-manager scale test

Runs `TestErrorPageManagerScale` as its own SlapOS test suite so its long
many-slave provisioning does not inflate the main `rapid-cdn` test line.

It requests a standalone `error-page-manager` partition with a large
`shared-list` (default 200 slaves, raised with
`RAPIDCDN_TEST_EPM_SLAVE_COUNT` for manual/nightly runs) and asserts the
`/sync` manifest stays O(overrides) -- flat regardless of the slave count --
plus stalled-client and concurrency resilience at scale.

The suite reuses the main `../test` package (`ErrorPageManagerClientMixin`,
`setUpModule`, `SlapOSInstanceTestCase`), so it builds the same Rapid.CDN
software release.
