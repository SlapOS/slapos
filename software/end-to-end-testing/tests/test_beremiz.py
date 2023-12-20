#import configparser
#import json
#import logging
#import unittest
#import slapos.client
import time
from opcua import Client
import slapos.testing.e2e as e2e


class BeremizTest(e2e.EndToEndTestCase):
  """
  This tests check proper functioning with real instances (inside SlapOS cloud)
  of following software components:
  - Beremiz IDE / runtime
  - OSIE coupler
  """

  # XXX: move outside runner at Test Suite ?
  #computer_id = "COMP-3523" # Ubunto 20.04
  #computer_id = "COMP-4036" # Debian 10
  computer_id = "COMP-4039" # Debian 11
  #computer_id = "COMP-4042"  # Ubunto 22.04

  coupler_release = "https://lab.nexedi.com/nexedi/slapos/raw/master/software/osie-coupler/software-dev.cfg"
  runtime_release = "https://lab.nexedi.com/nexedi/slapos/raw/master/software/beremiz-runtime/software.cfg"

  @classmethod
  def setUpClass(cls):
    super().setUpClass()

    # supply needed software releases
    print("Supply software releases at %s" %cls.computer_id)
    cls.supply(cls.coupler_release, cls.computer_id, state="available")
    cls.supply(cls.runtime_release, cls.computer_id, state="available")

    # XXX: rather than sleep add check to wait for SRs compilation end
    print("Sleep for 4h.")
    time.sleep(4*3600)

    # supply / request coupler
    instance_name = time.strftime('e2e-test-coupler-%Y-%B-%d-%H:%M:%S')
    parameter_dict = {"mode":1,
                      "network_interface": "192.168.0.0"}
    cls.request(cls.coupler_release,
                instance_name,
                partition_parameter_kw=parameter_dict)
    cls.waitUntilGreen(instance_name, 180)
    connection_dict = cls.getInstanceInfos(instance_name).connection_dict
    print(connection_dict)
    cls.coupler_url_ipv6 = connection_dict.get("url-ipv6")

    # supply / request beremiz-runtime
    instance_name = time.strftime('e2e-test-beremiz-runtime-%Y-%B-%d-%H:%M:%S')
    parameter_dict = {"runtime_plc_url": "https://lab.nexedi.com/nexedi/osie/raw/master/Beremiz/beremiz_test_opc_ua/bin/beremiz_test_opc_ua.tgz"}
    cls.request(cls.runtime_release,
                instance_name,
                partition_parameter_kw=parameter_dict)
    cls.waitUntilGreen(instance_name, 180)
    connection_dict = cls.getInstanceInfos(instance_name).connection_dict
    print(connection_dict)

  def test_plc_increment_run(self):
    NUMBER_OF_CHECKS = 100
    TIMEOUT = 2
    OPC_UA_IDENTIFIER = "ns=1;s=i2c0.relay0"

    # give it some time for services(runtime & coupler) to warm up, connect and run
    time.sleep(30)

    # connect to a session at OPC-UA server
    client = Client(self.coupler_url_ipv6)

    # for now this is the only test thus we start it without a wrapper
    test_count = 1
    test_failures = 0
    expected_failures = 0
    try:
      client.connect()
      root = client.get_root_node()
      children_list = root.get_children()
      var = client.get_node(OPC_UA_IDENTIFIER)
      for i in range (0, NUMBER_OF_CHECKS):
        i2c0_relay0_before = var.get_value()
        print("\ni2c0_relay0 (before) = ", i2c0_relay0_before)
        print("Sleep for %s seconds ..." %TIMEOUT)
        time.sleep(TIMEOUT)
        i2c0_relay0_after = var.get_value()
        print("i2c0_relay0 (after) = ", i2c0_relay0_after)
        # for the wait timeout runtime should have increased the value
        if (i2c0_relay0_after <= i2c0_relay0_before):
          # counter should have been increased, mark failure
          test_failures += 1
    finally:
      client.disconnect()
    # no failures
    self.assertEqual(test_failures, 0)
