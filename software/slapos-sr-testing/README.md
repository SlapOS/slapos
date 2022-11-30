# SlapOS Software Release tests

This software release is used to run integration test of slapos softwares.

The approach is to use python unittest runner to run tests.

The `python` used in this command will be a `zc.recipe.egg` interpreter with
all eggs pre-installed by this software release.

The results of this test suite running on Nexedi ERP5 are published as `SlapOS.SoftwareReleases.IntegrationTest-Master`.

## Running test locally

Here's an example session of how a developer could use this software release in
slaprunner to develop a slapos profile, in the example `helloworld`, make
changes to the code, run tests and publish changes.

```bash
# install this software release and request an instance
SR=https://lab.nexedi.com/nexedi/slapos/raw/1.0/software/slapos-sr-testing/software.cfg
COMP=slaprunner
INSTANCE_NAME=$COMP

slapos supply $SR $COMP
slapos node software
slapos request --node=computer_guid=$COMP $INSTANCE_NAME $SR
slapos node instance

# note the `environment-script` published value
slapos request --node=computer_guid=$COMP $INSTANCE_NAME $SR
# and load this script to set environment variables
source ( environment-script from step above )

# The source code is a git clone working copy on the instance
cd ~/srv/runner/instance/slappartXXX/software_release/parts/slapos-repository/

# change directory to the directory containing test for this software
cd ./software/helloworld/test/
# make changes to test code or profile

# run test for helloworld software release (with debugging features activated)
SLAPOS_TEST_DEBUG=1 python_for_test -m unittest discover -v
```

## Environment variables

The `environment-script` set all variables except `SLAPOS_TEST_DEBUG`, `SLAPOS_TEST_VERBOSE`, `SLAPOS_TEST_SKIP_SOFTWARE_CHECK` and `SLAPOS_TEST_SKIP_SOFTWARE_REBUILD` for you, but for reference, here is the list of variables which control the test runner:

| Variable | Description |
| --- | --- |
| `SLAPOS_TEST_VERBOSE` | If set to 1, debugging output will be printed on console. This also adjust the log level of python process running tests. When running on test nodes, this is not set, so keep this difference in mind if test rely on python logger |
| `SLAPOS_TEST_DEBUG` | If set to 1, `slapos node instance` and `slapos node software` will run with `--buildout-debug` flag, which will invoke python debugger on error. |
| `SLAPOS_TEST_SKIP_SOFTWARE_CHECK` | If set to 1, software checks will not be performed. This can be used to speed up running tests locally, as checking software is an expensive operation. |
| `SLAPOS_TEST_SKIP_SOFTWARE_REBUILD` | If set to 1, software will not be rebuilt before running the test. The default is to use `slapos node software --all`, which unconditionally rebuild all softwares and to use `slapos node software`, which installs the software only if it's not yet available when the environment variable is set to 1. |
| `SLAPOS_TEST_IPV6` | ipv6 used by this instance. Usually you want to use a global address here to be able to connect to this instance. |
| `SLAPOS_TEST_IPV4` | ipv4 used by this instance. |
| `SLAPOS_TEST_WORKING_DIR` | Path to use as a working directory to hold the standalone SlapOS. |
| `SLAPOS_TEST_SHARED_PART_LIST` | A `:` separated of paths to look for already installed shared parts. The SlapOS used in the test will not write in these, but will use a dedicated directory in `$SLAPOS_TEST_WORKING_DIR` |
| `SLAPOS_TEST_LOG_DIRECTORY` | If set, slapos testing will save the instance and/or software files in there in case of failure. Mostly used in testnodes to be able to debug afterward. |


## Frequently Asked Questions

### Where to find docs about the testing framework ?

Please refer to the docstrings from `slapos.testing` module, from `slapos.core` package.

This uses python unittest module from standard library, especially the setup hooks:
 - `setUpModule` installs the software and perform some static checks
 - `setUpClass` creates an instance
 - `setUp` can be used to initialise each test

### Can I run slapos commands to debug ?

The standalone slapos is created in `$SLAPOS_TEST_WORKING_DIR`. In this directory you will have a `bin/slapos` that you can run to start or stop services.
It's fine to use this command during development, but to programmatically interact with the environment within the test, the recommended approach is to use supervisor XML-RPC API.

### How to use a development version of `slapos.cookbook` ?

This test simply install the profile from `../software.cfg`, so it will use the `slapos.cookbook` egg used by this profile. During development, you can set a `${buildout:develop}` to point to a working copy of `slapos.cookbook` repository.
To use a development version of `slapos.cookbook` on test nodes, you can try using `slapos-cookbook-develop` part.

### Test pass locally but fail on test nodes, what can I do ?

At the end of the test, a snapshot of the slapos instances is created. Sometimes examining the log files can help understanding what went wrong.

Most of the time, problems are because on test nodes paths are very long. One advanced technique to reproduce the problem in your development environment is to set `SLAPOS_TEST_WORKING_DIR` environment variable to a path with the same length as the ones on test nodes.
One way to make instances uses a slightly shorter path is to define `__partition_reference__` class attribute, so that the instances uses this as prefix instead of the class name.

### Can I run only specific test ?

Yes, please refer to python unittest documentation. For example, you can use `python_for_test -m unittest -v test_module.TestClass.test_function` to run only test function.
