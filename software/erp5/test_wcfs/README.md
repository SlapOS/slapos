# Test wendelin.core v2 integration with ERP5 SR

This test suite is called by  `software/erp5/test`.

The complete logic is:
ERP5 `test.cfg` SR creates a `python` with all necessary eggs and installs a `bin` which executes this test suite.
The location of this `bin` is communicated to the outside world by publishing it as a connection parameter.
SlapOS integration test `software/erp5/test` reads the location of the script by fetching connection parameters.
It calls the script and provides the script the zurl of the ZODB storage.
The script runs the test suite and returns an exit code, 0 if the test suite succeeded and 1 if it failed.
If the exit code is 0 the unit test is passed.
