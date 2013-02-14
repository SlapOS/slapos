testing agent
=============

Testing agent simulates a normal user interacting with vifib master. It requests software release installation or software instance instiaction randomly from time to time. SlapOS clients then run these commands remotely. It is the testing agent determining whether an error occurs.

Usage
=====
Request a testing agent instance from vifib with following parameters:
<?xml version='1.0' encoding='utf-8'?>
<instance>
<parameter id="configuration">[DEFAULT]
# ConfigParser's magic section.
computer_list = ["COMP-607"]
master_url = https://slap.vifib.com/
# Note that certificates are now literally in the configuration, meaning
# you may decide to specify different ones for each test. Likewise for
# master_url.
key = -----BEGIN PRIVATE KEY-----
  MII[...]
  [...]
  -----END PRIVATE KEY-----
cert = -----BEGIN CERTIFICATE-----
  MII[...]
  [...]
  -----END CERTIFICATE-----

[agent]
# This section is special: it contains configuration.
# Does not make use of values coming from [DEFAULT] (well, it
# necessarily contains them, but they are not used).
node_title = ...
test_title = ...
project_title = ...
task_count = 2 # Number of tests to run concurrently
report_url = # report_url, find details in erp5 for details

# All other sections are individual tests, whatever they are named.
[test-apache]
# Software release URL
url = http://git.erp5.org/gitweb/slapos.git/blob_plain/HEAD:/software/apache-frontend/software.cfg
# Optional request_kw parameters: if not provided, will only test SR
# build. Depending on your slap version, it may be required to provide
# a "software_type" parameter, even if you want the default type.
request_kw = {
    "filter_kw": {"computer_guid": "..."},
    "partition_parameter_kw": {
      "domain": "example.com"
    }
  }
# All are in seconds.
max_install_duration = 3000
max_uninstall_duration = 360
max_request_duration = 700
max_destroy_duration = 360

[impossible-apache]
url = http://git.erp5.org/gitweb/slapos.git/blob_plain/HEAD:/software/apache-frontend/software.cfg
max_install_duration = 1
max_uninstall_duration = 1

[impossible-apache-2]
url = http://git.erp5.org/gitweb/slapos.git/blob_plain/HEAD:/software/apache-frontend/software.cfg
max_install_duration = 660
max_uninstall_duration = 1
</parameter>
</instance>

