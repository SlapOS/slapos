# -*- coding: utf-8 -*-
# vim: set et sts=2:
##############################################################################
#
# Copyright (c) 2010, 2011, 2012 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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

from lxml import etree
import sqlite3
from slapos.slap.slap import Computer, ComputerPartition, \
    SoftwareRelease, SoftwareInstance, NotFoundError
from slapos.proxy.db_version import DB_VERSION

from flask import g, Flask, request, abort
import xml_marshaller
app = Flask(__name__)


class UnauthorizedError(Exception):
  pass


def xml2dict(xml):
  result_dict = {}
  if xml is not None and xml != '':
    tree = etree.fromstring(xml.encode('utf-8'))
    for element in tree.iter(tag=etree.Element):
      if element.tag == 'parameter':
        key = element.get('id')
        value = result_dict.get(key, None)
        if value is not None:
          value = value + ' ' + element.text
        else:
          value = element.text
        result_dict[key] = value
  return result_dict


def dict2xml(dictionary):
  instance = etree.Element('instance')
  for parameter_id, parameter_value in dictionary.iteritems():
    # cast everything to string
    parameter_value = str(parameter_value)
    etree.SubElement(instance, "parameter",
                     attrib={'id': parameter_id}).text = parameter_value
  return etree.tostring(instance,
                        pretty_print=True,
                        xml_declaration=True,
                        encoding='utf-8')


def partitiondict2partition(partition):
  slap_partition = ComputerPartition(app.config['computer_id'],
      partition['reference'])
  slap_partition._software_release_document = None
  slap_partition._requested_state = 'destroyed'
  slap_partition._need_modification = 0
  slap_partition._instance_guid = partition['reference']

  if partition['software_release']:
    slap_partition._need_modification = 1
    slap_partition._requested_state = partition['requested_state']
    slap_partition._parameter_dict = xml2dict(partition['xml'])
    address_list = []
    for address in execute_db('partition_network',
                              'SELECT * FROM %s WHERE partition_reference=?',
                              [partition['reference']]):
      address_list.append((address['reference'], address['address']))
    slap_partition._parameter_dict['ip_list'] = address_list
    slap_partition._parameter_dict['slap_software_type'] = \
        partition['software_type']
    if partition['slave_instance_list'] is not None:
      slap_partition._parameter_dict['slave_instance_list'] = \
          xml_marshaller.xml_marshaller.loads(partition['slave_instance_list'])
    slap_partition._connection_dict = xml2dict(partition['connection_xml'])
    slap_partition._software_release_document = SoftwareRelease(
      software_release=partition['software_release'],
      computer_guid=app.config['computer_id'])

  return slap_partition


def execute_db(table, query, args=(), one=False):
  try:
    cur = g.db.execute(query % (table + DB_VERSION,), args)
  except:
    app.logger.error('There was some issue during processing query %r on table %r with args %r' % (query, table, args))
    raise
  rv = [dict((cur.description[idx][0], value)
    for idx, value in enumerate(row)) for row in cur.fetchall()]
  return (rv[0] if rv else None) if one else rv


def connect_db():
  return sqlite3.connect(app.config['DATABASE_URI'])


@app.before_request
def before_request():
  g.db = connect_db()
  schema = app.open_resource('schema.sql')
  schema = schema.read() % dict(version=DB_VERSION)
  g.db.cursor().executescript(schema)
  g.db.commit()


@app.after_request
def after_request(response):
  g.db.commit()
  g.db.close()
  return response

@app.route('/getComputerInformation', methods=['GET'])
def getComputerInformation():
  # Kept only for backward compatiblity
  return getFullComputerInformation()

@app.route('/getFullComputerInformation', methods=['GET'])
def getFullComputerInformation():
  computer_id = request.args['computer_id']
  if app.config['computer_id'] == computer_id:
    slap_computer = Computer(computer_id)
    slap_computer._software_release_list = []
    for sr in execute_db('software', 'select * from %s'):
      slap_computer._software_release_list.append(SoftwareRelease(
        software_release=sr['url'], computer_guid=computer_id))
    slap_computer._computer_partition_list = []
    for partition in execute_db('partition', 'SELECT * FROM %s'):
      slap_computer._computer_partition_list.append(partitiondict2partition(
        partition))
    return xml_marshaller.xml_marshaller.dumps(slap_computer)
  else:
    raise NotFoundError('Only accept request for: %s' % app.config['computer_id'])

@app.route('/setComputerPartitionConnectionXml', methods=['POST'])
def setComputerPartitionConnectionXml():
  slave_reference = request.form['slave_reference'].encode()
  computer_partition_id = request.form['computer_partition_id']
  connection_xml = request.form['connection_xml']
  connection_dict = xml_marshaller.xml_marshaller.loads(
                                            connection_xml.encode())
  connection_xml = dict2xml(connection_dict)
  if slave_reference == 'None':
    query = 'UPDATE %s SET connection_xml=? WHERE reference=?'
    argument_list = [connection_xml, computer_partition_id.encode()]
    execute_db('partition', query, argument_list)
    return 'done'
  else:
    query = 'UPDATE %s SET connection_xml=? , hosted_by=? WHERE reference=?'
    argument_list = [connection_xml, computer_partition_id.encode(),
                     slave_reference]
    execute_db('slave', query, argument_list)
    return 'done'

@app.route('/buildingSoftwareRelease', methods=['POST'])
def buildingSoftwareRelease():
  return 'Ignored'

@app.route('/availableSoftwareRelease', methods=['POST'])
def availableSoftwareRelease():
  return 'Ignored'

@app.route('/softwareReleaseError', methods=['POST'])
def softwareReleaseError():
  return 'Ignored'

@app.route('/buildingComputerPartition', methods=['POST'])
def buildingComputerPartition():
  return 'Ignored'

@app.route('/availableComputerPartition', methods=['POST'])
def availableComputerPartition():
  return 'Ignored'

@app.route('/softwareInstanceError', methods=['POST'])
def softwareInstanceError():
  return 'Ignored'

@app.route('/softwareInstanceBang', methods=['POST'])
def softwareInstanceBang():
  return 'Ignored'

@app.route('/startedComputerPartition', methods=['POST'])
def startedComputerPartition():
  return 'Ignored'

@app.route('/stoppedComputerPartition', methods=['POST'])
def stoppedComputerPartition():
  return 'Ignored'

@app.route('/destroyedComputerPartition', methods=['POST'])
def destroyedComputerPartition():
  return 'Ignored'

@app.route('/useComputer', methods=['POST'])
def useComputer():
  return 'Ignored'

@app.route('/loadComputerConfigurationFromXML', methods=['POST'])
def loadComputerConfigurationFromXML():
  xml = request.form['xml']
  computer_dict = xml_marshaller.xml_marshaller.loads(str(xml))
  if app.config['computer_id'] == computer_dict['reference']:
    execute_db('computer', 'INSERT OR REPLACE INTO %s values(:address, :netmask)',
        computer_dict)
    for partition in computer_dict['partition_list']:

      execute_db('partition', 'INSERT OR IGNORE INTO %s (reference) values(:reference)', partition)
      execute_db('partition_network', 'DELETE FROM %s WHERE partition_reference = ?', [partition['reference']])
      for address in partition['address_list']:
        address['reference'] = partition['tap']['name']
        address['partition_reference'] = partition['reference']
        execute_db('partition_network', 'INSERT OR REPLACE INTO %s (reference, partition_reference, address, netmask) values(:reference, :partition_reference, :addr, :netmask)', address)

    return 'done'
  else:
    raise UnauthorizedError('Only accept request for: %s' % app.config['computer_id'])

@app.route('/registerComputerPartition', methods=['GET'])
def registerComputerPartition():
  computer_reference = request.args['computer_reference']
  computer_partition_reference = request.args['computer_partition_reference']
  if app.config['computer_id'] == computer_reference:
    partition = execute_db('partition', 'SELECT * FROM %s WHERE reference=?',
      [computer_partition_reference.encode()], one=True)
    if partition is None:
      raise UnauthorizedError
    return xml_marshaller.xml_marshaller.dumps(
        partitiondict2partition(partition))
  else:
    raise UnauthorizedError('Only accept request for: %s' % app.config['computer_id'])

@app.route('/supplySupply', methods=['POST'])
def supplySupply():
  url = request.form['url']
  computer_id = request.form['computer_id']
  if app.config['computer_id'] == computer_id:
    if request.form['state'] == 'destroyed':
      execute_db('software', 'DELETE FROM %s WHERE url = ?', [url])
    else:
      execute_db('software', 'INSERT OR REPLACE INTO %s VALUES(?)', [url])
  else:
    raise UnauthorizedError('Only accept request for: %s' % app.config['computer_id'])
  return '%r added' % url


@app.route('/requestComputerPartition', methods=['POST'])
def requestComputerPartition():
  shared_xml = request.form.get('shared_xml')
  share = xml_marshaller.xml_marshaller.loads(shared_xml)
  if not share:
    return request_not_shared()
  else:
    return request_slave()


@app.route('/softwareInstanceRename', methods=['POST'])
def softwareInstanceRename():
  new_name = request.form['new_name'].encode()
  computer_partition_id = request.form['computer_partition_id'].encode()

  q = 'UPDATE %s SET partition_reference = ? WHERE reference = ?'
  execute_db('partition', q, [new_name, computer_partition_id])
  return 'done'


def request_not_shared():
  software_release = request.form['software_release'].encode()
  # some supported parameters
  software_type = request.form.get('software_type').encode()
  partition_reference = request.form.get('partition_reference', '').encode()
  partition_id = request.form.get('computer_partition_id', '').encode()
  partition_parameter_kw = request.form.get('partition_parameter_xml', None)
  requested_state = xml_marshaller.xml_marshaller.loads(request.form.get('state'))
  if partition_parameter_kw:
    partition_parameter_kw = xml_marshaller.xml_marshaller.loads(
                                              partition_parameter_kw.encode())
  else:
    partition_parameter_kw = {}

  instance_xml = dict2xml(partition_parameter_kw)
  args = []
  a = args.append
  q = 'SELECT * FROM %s WHERE partition_reference=?'
  a(partition_reference)

  partition = execute_db('partition', q, args, one=True)

  args = []
  a = args.append
  q = 'UPDATE %s SET slap_state="busy"'

  if requested_state:
    q += ', requested_state=?'
    a(requested_state)

  # If partition doesn't exist: create it and insert parameters
  if partition is None:
    partition = execute_db('partition',
        'SELECT * FROM %s WHERE slap_state="free"', (), one=True)
    if partition is None:
      app.logger.warning('No more free computer partition')
      abort(404)
    q += ' ,software_release=?'
    a(software_release)
    if partition_reference:
      q += ' ,partition_reference=?'
      a(partition_reference)
    if partition_id:
      q += ' ,requested_by=?'
      a(partition_id)
    if not software_type:
      software_type = 'RootSoftwareInstance'

  #
  # XXX change software_type when requested
  #
  if software_type:
    q += ' ,software_type=?'
    a(software_type)

  # Else: only update partition_parameter_kw
  if instance_xml:
    q += ' ,xml=?'
    a(instance_xml)
  q += ' WHERE reference=?'
  a(partition['reference'].encode())
  execute_db('partition', q, args)
  args = []
  partition = execute_db('partition', 'SELECT * FROM %s WHERE reference=?',
      [partition['reference'].encode()], one=True)
  address_list = []
  for address in execute_db('partition_network', 'SELECT * FROM %s WHERE partition_reference=?', [partition['reference']]):
    address_list.append((address['reference'], address['address']))

  # XXX it should be ComputerPartition, not a SoftwareInstance
  software_instance = SoftwareInstance(xml=partition['xml'],
                                       connection_xml=partition['connection_xml'],
                                       slap_computer_id=app.config['computer_id'],
                                       slap_computer_partition_id=partition['reference'],
                                       slap_software_release_url=partition['software_release'],
                                       slap_server_url='slap_server_url',
                                       slap_software_type=partition['software_type'],
                                       slave_instance_list=partition['slave_instance_list'],
                                       instance_guid=partition['reference'],
                                       ip_list=address_list)

  return xml_marshaller.xml_marshaller.dumps(software_instance)


def request_slave():
  """
  Function to organise link between slave and master.
  Slave information are stored in places:
  1. slave table having information such as slave reference,
      connection information to slave (given by slave master),
      hosted_by and asked_by reference.
  2. A dictionary in slave_instance_list of selected slave master
      in which are stored slave_reference, software_type, slave_title and
      partition_parameter_kw stored as individual keys.
  """
  software_release = request.form['software_release'].encode()
  # some supported parameters
  software_type = request.form.get('software_type').encode()
  partition_reference = request.form.get('partition_reference', '').encode()
  partition_id = request.form.get('computer_partition_id', '').encode()
  # Contain slave parameters to be given to slave master
  partition_parameter_kw = request.form.get('partition_parameter_xml', None)
  if partition_parameter_kw:
    partition_parameter_kw = xml_marshaller.xml_marshaller.loads(
                                              partition_parameter_kw.encode())
  else:
    partition_parameter_kw = {}

  filter_kw = xml_marshaller.xml_marshaller.loads(request.form.get('filter_xml').encode())

  instance_xml = dict2xml(partition_parameter_kw)
  # We will search for a master corresponding to request
  args = []
  a = args.append
  q = 'SELECT * FROM %s WHERE software_release=?'
  a(software_release)
  if software_type:
    q += ' AND software_type=?'
    a(software_type)
  if 'instance_guid' in filter_kw:
    q += ' AND reference=?'
    a(filter_kw['instance_guid'])

  partition = execute_db('partition', q, args, one=True)
  if partition is None:
    app.logger.warning('No partition corresponding to slave request: %s' % args)
    abort(404)

  # We set slave dictionary as described in docstring
  new_slave = {}
  slave_reference = partition_id + '_' + partition_reference
  new_slave['slave_title'] = slave_reference
  new_slave['slap_software_type'] = software_type
  new_slave['slave_reference'] = slave_reference

  for key in partition_parameter_kw:
    if partition_parameter_kw[key] is not None:
      new_slave[key] = partition_parameter_kw[key]

  # Add slave to partition slave_list if not present else replace information
  slave_instance_list = partition['slave_instance_list']
  if slave_instance_list is None:
    slave_instance_list = []
  else:
    slave_instance_list = xml_marshaller.xml_marshaller.loads(slave_instance_list)
    for x in slave_instance_list:
      if x['slave_reference'] == slave_reference:
        slave_instance_list.remove(x)

  slave_instance_list.append(new_slave)

  # Update slave_instance_list in database
  args = []
  a = args.append
  q = 'UPDATE %s SET slave_instance_list=?'
  a(xml_marshaller.xml_marshaller.dumps(slave_instance_list))
  q += ' WHERE reference=?'
  a(partition['reference'].encode())
  execute_db('partition', q, args)
  args = []
  partition = execute_db('partition', 'SELECT * FROM %s WHERE reference=?',
      [partition['reference'].encode()], one=True)

  # Add slave to slave table if not there
  slave = execute_db('slave', 'SELECT * FROM %s WHERE reference=?',
                     [slave_reference], one=True)
  if slave is None:
    execute_db('slave',
               'INSERT OR IGNORE INTO %s (reference,asked_by,hosted_by) values(:reference,:asked_by,:hosted_by)',
               [slave_reference, partition_id, partition['reference']])
    slave = execute_db('slave', 'SELECT * FROM %s WHERE reference=?',
                       [slave_reference], one=True)

  address_list = []
  for address in execute_db('partition_network',
                            'SELECT * FROM %s WHERE partition_reference=?',
                            [partition['reference']]):
    address_list.append((address['reference'], address['address']))

  # XXX it should be ComputerPartition, not a SoftwareInstance
  software_instance = SoftwareInstance(_connection_dict=xml2dict(slave['connection_xml']),
                                       xml=instance_xml,
                                       slap_computer_id=app.config['computer_id'],
                                       slap_computer_partition_id=slave['hosted_by'],
                                       slap_software_release_url=partition['software_release'],
                                       slap_server_url='slap_server_url',
                                       slap_software_type=partition['software_type'],
                                       ip_list=address_list)

  return xml_marshaller.xml_marshaller.dumps(software_instance)


@app.route('/getSoftwareReleaseListFromSoftwareProduct', methods=['GET'])
def getSoftwareReleaseListFromSoftwareProduct():
  software_product_reference = request.args.get('software_product_reference')
  software_release_url = request.args.get('software_release_url')

  if software_release_url:
    assert(software_product_reference is None)
    raise NotImplementedError('software_release_url parameter is not supported yet.')
  else:
    assert(software_product_reference is not None)
    if app.config['software_product_list'].has_key(software_product_reference):
      software_release_url_list =\
          [app.config['software_product_list'][software_product_reference]]
    else:
      software_release_url_list =[]
    return xml_marshaller.xml_marshaller.dumps(software_release_url_list)
