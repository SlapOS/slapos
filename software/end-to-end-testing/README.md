# End To End Testing

This software release is used to run end-to-end test of SlapOS softwares on an actual SlapOS cloud such as Rapid.Space. Since it can supply softwares and request instances on an actual cloud, it needs a SlaPOS client certificate and the URLs of your tests.

## Input parameters

```
{
  "client.crt": <content of client.crt>,
  "client.key": <content of client.key>,
  "master-url": <url of SlapOS master>,
  "tests": [
  {
    "url": "<url of test1 script>",
    "md5sum": "MD5sum of test1 script"
  },
  {
    "url": "<url of test2 python script>",
    "md5sum": "MD5sum of test2 python script"
  },
  ...
  ]
}
```
Example:
(`e2e-parameters.json`)
```
{
  "client.crt": "Certificate:...-----END CERTIFICATE-----\n",

  "master-url": "https://slap.vifib.com",
  "tests": [
    {
      "url": "https://lab.nexedi.com/lu.xu/slapos/raw/feat/end-to-end-testing/software/end-to-end-testing/test_test.py",
      "md5sum": "c074373dbb4154aa924ef5781dade7a0"
    }
  ]
}
```

## Generate client certificate

Follow [How To Set Up SlapOS Client](https://handbook.rapid.space/user/rapidspace-HowTo.Setup.SlapOS.Client) to prepare `slapos-client.cfg` if you don't have one.

A convenience script `generate_parameters.py` is provided to compute these parameters in JSON format from an existing SlapOS client configuration:

```
python3 generate_parameters.py --cfg <absolute path to slapos-client.cfg> -o <output path>
```


## Adding tests

There are 3 example tests available in end-to-end testing SR:
- test_test.py
  Simple successful test and failed test
- test_kvm.py
  Request a KVM instance with published SR and verify one of the connection parameters
- test_health.py
  Request a Monitor instance with published SR and log promises output

All tests should be written in Python with a `.py` extension and should have names that start with `test_`.

Once your test is prepared, you have the option to input a URL and its corresponding md5sum as parameters. This will enable the end-to-end testing instance to automatically detect the test.

## Running tests

- In ERP5

When performing tests on a software release (SR) using the ERR5 test suite, you can use "SlapOS.SoftwareReleases.IntegrationTest". Additionally, make sure to fill in the "Slapos Parameters" field with the content of the input parameter mentioned above.

- In Theia

Using slapos.core for quick testing:
```
python3 -m venv testenv
pip install -e path/to/my/slapos.core
export SLAPOS_E2E_TEST_CLIENT_CFG=my_test_client_cfg
export SLAPOS_E2E_TEST_LOG_FILE=my_test_log_file
python -m unittest my_test_file_in_development
# edit e2e.py in path/to/my/slapos.core or the instanciated one if improvements are needed
```

1. Setup and instantiate the runner
```
slapos supply ~/srv/project/slapos/software/end-to-end-testing/software.cfg slaprunner
slapos request <e2e_instance_name> ~/srv/project/slapos/software/end-to-end-testing/software.cfg --parameters-file <e2e_parameter_json_file>
```
Your tests should be listed in <e2e_parameter_json_file> with URL and MD5sum

2. Go to instance directory and run test
```
cd ~/srv/runner/instance/slappartX
./bin/runTestSuite
```
Downloaded tests and the reusable `e2e.py` script can be found in the `~/srv/runner/instance/slappartX/var/tests/` directory.

To quickly test, you have the option to modify the test script directly here(`~/srv/runner/instance/slappartX/var/tests/`). After making the necessary changes, you can relaunch the tests by running `./bin/runTestSuite`.

## FAQ

Q1. What is the difference between `slapos-sr-testing` and `end-to-end-testing`?

- slapos-sr-testing requests SRs on a slapproxy in an SlapOSStandalone inside the slapos-sr-testing instance (same kind of thing as Theia or webrunner).

- end-to-end-testing requests SRs on the actual master, in real compute nodes (COMP-XXX). To do this it needs a slapos certificate which is passed as instance parameter to end-to-end-testing instance in the test suite.

So unlike slapos-sr-testing, end-to-end-testing does not contain the SRs it tests, it merely runs the python tests scripts (like mentioned `test_kvm.py`) and integrates with the ERP5 test suite. This also means we cannot access the files in the partition of the tested SRs, as those are on other computers. All we have access to is what a normal user requesting on panel would have access to.
