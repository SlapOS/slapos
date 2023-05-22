##############################################################################
#
# Copyright (c) 2022 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import ipaddress
import json
import os
import socket
import struct
import subprocess
import time

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

MAIN_SCRIPT_NAME = 'main.js'
'''
  0. positionArray
    0.1 latitude
    0.2 longitude
    0.3 absolute altitude
    0.4 relative altitude
  1. speedArray
    1.1 yaw angle
    1.2 air speed
    1.3 climb rate
  2. message
'''
MONITORED_ITEM_NB = 3
OPC_UA_PORT = 4840
OPC_UA_NET_IF = 'lo'
MCAST_GRP = 'ff15::1111'
USER_SCRIPT_NAME = 'user.js'

# OPC UA Pub/Sub related constants
VERSION = 1
PUBLISHER_ID_ENABLED = True
GROUP_HEADER_ENABLED = True
PAYLOAD_HEADER_ENABLED = True
EXTENDED_FLAGS1_ENABLED = True

PUBLISHER_ID_TYPE = 1 #UInt16
DATA_SET_CLASS_ID_ENABLED = False
SECURITY_ENABLED = False
NETWORK_MESSAGE_TIMESTAMP_ENABLED = False
PICOSECONDS_ENABLED = False
EXTENDED_FLAGS2_ENABLED = False

PUBLISHER_ID = 0

WRITER_GROUP_ID_ENABLED = True
GROUP_VERSION_ENABLED = False
NETWORK_MESSAGE_NUMBER_ENABLED = False
SEQUENCE_NUMBER_ENABLED = False

WRITER_GROUP_ID = 1

DATASET_PAYLOAD_HEADER_COUNT = 1
DATA_SET_WRITER_ID = (1,)

DATA_SET_MESSAGE_VALIDE = 1
FIELD_ENCODING = 0 #UA_FIELDENCODING_VARIANT
DATA_SET_MESSAGE_SEQUENCE_NR_ENABLED = False
STATUS_ENABLED = False
CONFIG_VERSION_MAJOR_VERSION_ENABLED = True
CONFIG_VERSION_MINOR_VERSION_ENABLED = True
MESSAGE_HEADER_FLAGS2_ENABLED = True

DATA_SET_MESSAGE_TYPE = 0 #UA_DATASETMESSAGE_DATAKEYFRAME
DATA_SET_MESSAGE_TIMESTAMP_ENABLED = True
PICO_SECONDS_INCLUDED = False

UA_DATETIME_SEC = 10000000
UA_DATETIME_UNIX_EPOCH = 11644473600 * UA_DATETIME_SEC

CONFIG_VERSION_MAJOR_VERSION = 1690792766
CONFIG_VERSION_MINOR_VERSION = 1690781976

POSITION_ARRAY_TYPE = 11 #double
POSITION_ARRAY_VALUES = (45.64, 14.25, 686.61, 91.24)

SPEED_ARRAY_TYPE = 10 #float
SPEED_ARRAY_VALUES = (-72.419998, 15.93, -0.015)

STRING_TYPE = 12
TEST_MESSAGE = b'{"content":"{\\"next_checkpoint\\":1}","dest_id":-1}'

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class JSDroneTestCase(SlapOSInstanceTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      '_': json.dumps({
        'droneGuidList': [cls.slap._computer_id],
        'netIf': OPC_UA_NET_IF,
        'subscriberGuidList': [cls.slap._computer_id],
      })
    }

  def get_partition(self, partition_id):
    software_url = self.getSoftwareURL()
    for computer_partition in self.slap.computer.getComputerPartitionList():
      if computer_partition.getId() == partition_id:
        return computer_partition
    raise Exception("Partition %s not found" % partition_id)

  def setUp(self):
    super().setUp()
    subscriber_partition = self.get_partition('JSDroneTestCase-2')
    instance_path = json.loads(
      subscriber_partition.getConnectionParameterDict()['_'])['instance-path']
    quickjs_bin = os.path.join(instance_path, 'bin', 'qjs')
    script_dir = os.path.join(instance_path, 'etc')
    self.qjs_process = subprocess.Popen(
      [
        quickjs_bin,
        os.path.join(script_dir, MAIN_SCRIPT_NAME),
        os.path.join(script_dir, USER_SCRIPT_NAME),
      ],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
    )
    time.sleep(0.1)

  def tearDown(self):
    if self.qjs_process.returncode == None:
      self.qjs_process.kill()
      self.qjs_process.communicate()
    super().tearDown()

  def ua_networkMessage_encodeHeader(self):
    ua_byte1 = int(VERSION)
    ua_byte1 |= int(PUBLISHER_ID_ENABLED) << 4
    ua_byte1 |= int(GROUP_HEADER_ENABLED) << 5
    ua_byte1 |= int(PAYLOAD_HEADER_ENABLED) << 6
    ua_byte1 |= int(EXTENDED_FLAGS1_ENABLED) << 7

    ua_byte2 = PUBLISHER_ID_TYPE
    ua_byte2 |= int(DATA_SET_CLASS_ID_ENABLED) << 3
    ua_byte2 |= int(SECURITY_ENABLED) << 4
    ua_byte2 |= int(NETWORK_MESSAGE_TIMESTAMP_ENABLED) << 5
    ua_byte2 |= int(PICOSECONDS_ENABLED) << 6
    ua_byte2 |= int(EXTENDED_FLAGS2_ENABLED) << 7

    return struct.pack('BBH', ua_byte1, ua_byte2, PUBLISHER_ID)

  def ua_groupHeader_encode(self):
    ua_byte = int(WRITER_GROUP_ID_ENABLED)
    ua_byte |= int(GROUP_VERSION_ENABLED) << 1
    ua_byte |= int(NETWORK_MESSAGE_NUMBER_ENABLED) << 2
    ua_byte |= int(SEQUENCE_NUMBER_ENABLED) << 3

    return struct.pack('B', ua_byte) + struct.pack('H', WRITER_GROUP_ID)

  def ua_payloadHeader_encode(self):
    header = struct.pack('B', DATASET_PAYLOAD_HEADER_COUNT)
    for data_set_writer_id in DATA_SET_WRITER_ID:
      header += struct.pack('H', data_set_writer_id)
    return header

  def ua_networkMessage_encodeHeaders(self):
    headers = self.ua_networkMessage_encodeHeader()
    headers += self.ua_groupHeader_encode()
    headers += self.ua_payloadHeader_encode()
    return headers

  def ua_dataSetMessageHeader_encode(self):
    ua_byte1 = int(DATA_SET_MESSAGE_VALIDE)
    ua_byte1 |= FIELD_ENCODING << 1
    ua_byte1 |= int(DATA_SET_CLASS_ID_ENABLED) << 3
    ua_byte1 |= int(STATUS_ENABLED) << 4
    ua_byte1 |= int(CONFIG_VERSION_MAJOR_VERSION_ENABLED) << 5
    ua_byte1 |= int(CONFIG_VERSION_MINOR_VERSION_ENABLED) << 6
    ua_byte1 |= int(MESSAGE_HEADER_FLAGS2_ENABLED) << 7

    ua_byte2 = DATA_SET_MESSAGE_TYPE
    ua_byte2 |= int(DATA_SET_MESSAGE_TIMESTAMP_ENABLED) << 4
    ua_byte2 |= int(PICO_SECONDS_INCLUDED) << 5

    header = struct.pack('BB', ua_byte1, ua_byte2)
    ua_datetime = time.time() * UA_DATETIME_SEC + UA_DATETIME_UNIX_EPOCH

    return header + struct.pack('qII', int(ua_datetime), CONFIG_VERSION_MAJOR_VERSION, CONFIG_VERSION_MINOR_VERSION)

  def ua_array_encode(self, type_id, struct_type, values):
    encoding_mask = type_id
    encoding_mask += 1 << 7 # is an array
    ua_array = struct.pack('B', encoding_mask)
    ua_array += struct.pack('I', len(values))
    for value in values:
      ua_array += struct.pack(struct_type, value)
    return ua_array

  def ua_dataSetMessage_encode(self):
    data_set_message = self.ua_dataSetMessageHeader_encode()
    data_set_message += struct.pack('H', MONITORED_ITEM_NB)
    data_set_message += self.ua_array_encode(
      POSITION_ARRAY_TYPE,
      'd',
      POSITION_ARRAY_VALUES,
    )
    data_set_message += self.ua_array_encode(
      SPEED_ARRAY_TYPE,
      'f',
      SPEED_ARRAY_VALUES,
    )
    data_set_message += struct.pack('B', STRING_TYPE)
    data_set_message += struct.pack('I', len(TEST_MESSAGE))
    data_set_message += TEST_MESSAGE
    return data_set_message

  def send_ua_networkMessage(self):
    ua_message = self.ua_networkMessage_encodeHeaders()
    ua_message += self.ua_dataSetMessage_encode()
    with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
      s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
      s.sendto(ua_message, ('::1', OPC_UA_PORT))

  def test_requested_instances(self):
    connection_parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()['_'])
    self.assertEqual(connection_parameter_dict['drone-id-list'], [0])
    self.assertEqual(connection_parameter_dict['subscriber-id-list'], [1])

  def test_subscriber_instance_parameter_dict(self):
    self.assertEqual(
      json.loads(self.get_partition('JSDroneTestCase-2').getInstanceParameterDict()['_']),
      {
        'autopilotIp': '192.168.27.1',
        'autopilotPort': 7909,
        'numberOfDrone': 1,
        'numberOfSubscriber': 1,
        'id': 1,
        'isASimulation': False,
        'isADrone': False,
        'flightScript': 'https://lab.nexedi.com/nexedi/flight-scripts/raw/master/subscribe.js',
        'netIf': OPC_UA_NET_IF,
        'multicastIp': MCAST_GRP
      }
    )

  def net_if_name_to_index(self, name):
    with open('/sys/class/net/%s/ifindex' % name) as f:
      index = int(f.readline())
    return index

  def test_joined_multicast_grp(self):
    expected_string = '%s    %s              %s     1 00000004 0\n' % (
      self.net_if_name_to_index(OPC_UA_NET_IF),
      OPC_UA_NET_IF,
      ipaddress.IPv6Address(MCAST_GRP).exploded.replace(':', ''),
    )
    with open('/proc/net/igmp6') as f:
      self.assertIn(expected_string, f.readlines())

  def test_pubsub_subscription(self):
    self.send_ua_networkMessage()
    time.sleep(0.1)
    outs, _ = self.qjs_process.communicate(b'q\n', timeout=15)
    decoded_out = outs.decode()
    for line in (
      'Subscription 0 | MonitoredItem %s' % MONITORED_ITEM_NB,
      'Received position of drone 0: %f° %f° %fm %fm' % POSITION_ARRAY_VALUES,
      'Received speed of drone 0: %f° %fm/s %fm/s' % SPEED_ARRAY_VALUES,
      'Received message for drone 0: %s' % TEST_MESSAGE.decode(),
    ):
      self.assertIn(line, decoded_out)
