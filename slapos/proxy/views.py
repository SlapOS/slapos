# -*- coding: utf-8 -*-
# vim: set et sts=2:
##############################################################################
#
# Copyright (c) 2010, 2011, 2012, 2013, 2014 Vifib SARL and Contributors.
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
import random
import string
from slapos.slap.slap import Computer, ComputerPartition, \
    SoftwareRelease, SoftwareInstance, NotFoundError
from slapos.proxy.db_version import DB_VERSION
import slapos.slap
from slapos.util import sqlite_connect

from flask import g, Flask, request, abort
import xml_marshaller
from xml_marshaller.xml_marshaller import loads
from xml_marshaller.xml_marshaller import dumps

app = Flask(__name__)

EMPTY_DICT_XML = dumps({})

class UnauthorizedError(Exception):
  pass


# cast everything to string, utf-8 encoded
def to_str(v):
  if isinstance(v, str):
    return v
  if not isinstance(v, unicode):
    v = unicode(v)
  return v.encode('utf-8')


def xml2dict(xml):
  result_dict = {}
  if xml is not None and xml != '':
    tree = etree.fromstring(to_str(xml))
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
    parameter_value = unicode(parameter_value)
    etree.SubElement(instance, "parameter",
                     attrib={'id': parameter_id}).text = parameter_value
  return etree.tostring(instance,
                        pretty_print=True,
                        xml_declaration=True,
                        encoding='utf-8')


def partitiondict2partition(partition):
  for key, value in partition.iteritems():
    if type(value) is unicode:
      partition[key] = value.encode()
  slap_partition = ComputerPartition(partition['computer_reference'],
      partition['reference'])
  slap_partition._software_release_document = None
  slap_partition._requested_state = 'destroyed'
  slap_partition._need_modification = 0
  slap_partition._instance_guid = '%s-%s' % (partition['computer_reference'], partition['reference'])

  root_partition = getRootPartition(partition['reference'])

  if partition['software_release']:
    slap_partition._need_modification = 1
    slap_partition._requested_state = partition['requested_state']
    slap_partition._parameter_dict = xml2dict(partition['xml'])
    address_list = []
    full_address_list = []
    for address in execute_db('partition_network',
                              'SELECT * FROM %s WHERE partition_reference=? AND computer_reference=?',
                              [partition['reference'], partition['computer_reference']]):
      address_list.append((address['reference'], address['address']))
    slap_partition._parameter_dict['ip_list'] = address_list
    slap_partition._parameter_dict['full_address_list'] = full_address_list
    slap_partition._parameter_dict['slap_software_type'] = \
        partition['software_type']
    slap_partition._parameter_dict['instance_title'] = \
        partition['partition_reference']
    slap_partition._parameter_dict['root_instance_title'] = \
        root_partition['partition_reference']
    if partition['slave_instance_list'] is not None:
      slap_partition._parameter_dict['slave_instance_list'] = \
          xml_marshaller.xml_marshaller.loads(partition['slave_instance_list'])
    else:
      slap_partition._parameter_dict['slave_instance_list'] = []
    slap_partition._connection_dict = xml2dict(partition['connection_xml'])
    slap_partition._software_release_document = SoftwareRelease(
      software_release=partition['software_release'],
      computer_guid=partition['computer_reference'])

  return slap_partition


def execute_db(table, query, args=(), one=False, db_version=None, log=False, db=None):
  if not db:
    db = g.db
  if not db_version:
    db_version = DB_VERSION
  query = query % (table + db_version,)
  if log:
    print query
  try:
    cur = db.execute(query, args)
  except:
    app.logger.error('There was some issue during processing query %r on table %r with args %r' % (query, table, args))
    raise
  rv = [dict((cur.description[idx][0], value)
    for idx, value in enumerate(row)) for row in cur.fetchall()]
  return (rv[0] if rv else None) if one else rv


def connect_db():
  return sqlite_connect(app.config['DATABASE_URI'])

def _getTableList():
  return g.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY Name").fetchall()

def _getCurrentDatabaseSchemaVersion():
  """
  Return version of database schema.
  As there is no actual definition of version, analyse
  name of all tables (containing version) and take the
  highest version (as several versions can live in the db).
  """
  # XXX: define an actual version and proper migration/repair procedure.
  version = -1
  for table_name in _getTableList():
    try:
      table_version = int(table_name[0][-2:])
    except ValueError:
      table_version = int(table_name[0][-1:])
    if table_version > version:
      version = table_version
  return str(version)

def _upgradeDatabaseIfNeeded():
  """
  Analyses current database compared to defined schema,
  and adapt tables/data it if needed.
  """
  current_schema_version = _getCurrentDatabaseSchemaVersion()
  # If version of current database is not old, do nothing
  if current_schema_version == DB_VERSION:
    return

  schema = app.open_resource('schema.sql')
  schema = schema.read() % dict(version=DB_VERSION, computer=app.config['computer_id'])
  g.db.cursor().executescript(schema)
  g.db.commit()

  if current_schema_version == '-1':
    return

  # Migrate all data to new tables
  app.logger.info('Old schema detected: Migrating old tables...')
  app.logger.info('Note that old tables are not alterated.')
  for table in ('software', 'computer', 'partition', 'slave', 'partition_network'):
    for row in execute_db(table, 'SELECT * from %s', db_version=current_schema_version):
      columns = ', '.join(row.keys())
      placeholders = ':'+', :'.join(row.keys())
      query = 'INSERT INTO %s (%s) VALUES (%s)' % ('%s', columns, placeholders)
      execute_db(table, query, row, log=True)

  g.db.commit()

is_schema_already_executed = False
@app.before_request
def before_request():
  g.db = connect_db()
  global is_schema_already_executed
  if not is_schema_already_executed:
    _upgradeDatabaseIfNeeded()
    is_schema_already_executed = True


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
  computer_list = execute_db('computer', 'SELECT * FROM %s WHERE reference=?', [computer_id])
  if len(computer_list) != 1:
    # Backward compatibility
    if computer_id != app.config['computer_id']:
      raise NotFoundError('%s is not registered.' % computer_id)
  slap_computer = Computer(computer_id)
  slap_computer._software_release_list = []
  for sr in execute_db('software', 'select * from %s WHERE computer_reference=?', [computer_id]):
    slap_computer._software_release_list.append(SoftwareRelease(
      software_release=sr['url'], computer_guid=computer_id))
  slap_computer._computer_partition_list = []
  for partition in execute_db('partition', 'SELECT * FROM %s WHERE computer_reference=?', [computer_id]):
    slap_computer._computer_partition_list.append(partitiondict2partition(
      partition))
  return xml_marshaller.xml_marshaller.dumps(slap_computer)

@app.route('/setComputerPartitionConnectionXml', methods=['POST'])
def setComputerPartitionConnectionXml():
  slave_reference = request.form.get('slave_reference', None)
  computer_partition_id = request.form['computer_partition_id'].encode()
  computer_id = request.form['computer_id'].encode()
  connection_xml = request.form['connection_xml'].encode()
  connection_dict = xml_marshaller.xml_marshaller.loads(
                                            connection_xml)
  connection_xml = dict2xml(connection_dict)
  if not slave_reference or slave_reference == 'None':
    query = 'UPDATE %s SET connection_xml=? WHERE reference=? AND computer_reference=?'
    argument_list = [connection_xml, computer_partition_id, computer_id]
    execute_db('partition', query, argument_list)
    return 'done'
  else:
    slave_reference = slave_reference.encode()
    query = 'UPDATE %s SET connection_xml=? , hosted_by=? WHERE reference=?'
    argument_list = [connection_xml, computer_partition_id, slave_reference]
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
  execute_db('computer', 'INSERT OR REPLACE INTO %s values(:reference, :address, :netmask)',
             computer_dict)
  for partition in computer_dict['partition_list']:
    partition['computer_reference'] = computer_dict['reference']
    execute_db('partition', 'INSERT OR IGNORE INTO %s (reference, computer_reference) values(:reference, :computer_reference)', partition)
    execute_db('partition_network', 'DELETE FROM %s WHERE partition_reference = ? AND computer_reference = ?',
               [partition['reference'], partition['computer_reference']])
    for address in partition['address_list']:
      address['reference'] = partition['tap']['name']
      address['partition_reference'] = partition['reference']
      address['computer_reference'] = partition['computer_reference']
      execute_db('partition_network', 'INSERT OR REPLACE INTO %s (reference, partition_reference, computer_reference, address, netmask) values(:reference, :partition_reference, :computer_reference, :addr, :netmask)', address)

  return 'done'

@app.route('/registerComputerPartition', methods=['GET'])
def registerComputerPartition():
  computer_reference = request.args['computer_reference'].encode()
  computer_partition_reference = request.args['computer_partition_reference'].encode()
  partition = execute_db('partition', 'SELECT * FROM %s WHERE reference=? and computer_reference=?',
      [computer_partition_reference, computer_reference], one=True)
  if partition is None:
    raise UnauthorizedError
  return xml_marshaller.xml_marshaller.dumps(
      partitiondict2partition(partition))

@app.route('/supplySupply', methods=['POST'])
def supplySupply():
  url = request.form['url']
  computer_id = request.form['computer_id']
  if request.form['state'] == 'destroyed':
    execute_db('software', 'DELETE FROM %s WHERE url = ? AND computer_reference=?',
               [url, computer_id])
  else:
    execute_db('software', 'INSERT OR REPLACE INTO %s VALUES(?, ?)', [url, computer_id])
  return '%r added' % url


@app.route('/requestComputerPartition', methods=['POST'])
def requestComputerPartition():
  parsed_request_dict = parseRequestComputerPartitionForm(request.form)

  # Is it a slave instance?
  slave = loads(request.form.get('shared_xml', EMPTY_DICT_XML).encode())

  # Check first if instance is already allocated
  if slave:
    # XXX: change schema to include a simple "partition_reference" which
    # is name of the instance. Then, no need to do complex search here.
    slave_reference = parsed_request_dict['partition_id'] + '_' + parsed_request_dict['partition_reference']
    requested_computer_id = parsed_request_dict['filter_kw'].get('computer_guid', app.config['computer_id'])
    matching_partition = getAllocatedSlaveInstance(slave_reference, requested_computer_id)
  else:
    matching_partition = getAllocatedInstance(parsed_request_dict['partition_reference'])

  if matching_partition:
    # Then the instance is already allocated, just update it
    # XXX: split request and request slave into different update/allocate functions and simplify.
    # By default, ALWAYS request instance on default computer
    parsed_request_dict['filter_kw'].setdefault('computer_guid', app.config['computer_id'])
    if slave:
      software_instance = requestSlave(**parsed_request_dict)
    else:
      software_instance = requestNotSlave(**parsed_request_dict)
  else:
    # Instance is not yet allocated: try to do it.
    external_master_url = isRequestToBeForwardedToExternalMaster(parsed_request_dict)
    if external_master_url:
      return forwardRequestToExternalMaster(external_master_url, request.form)
    # XXX add support for automatic deployment on specific node depending on available SR and partitions on each Node.
    # Note: It only deploys on default node if SLA not specified
    # XXX: split request and request slave into different update/allocate functions and simplify.

    # By default, ALWAYS request instance on default computer
    parsed_request_dict['filter_kw'].setdefault('computer_guid', app.config['computer_id'])
    if slave:
      software_instance = requestSlave(**parsed_request_dict)
    else:
      software_instance = requestNotSlave(**parsed_request_dict)

  return dumps(software_instance)

def parseRequestComputerPartitionForm(form):
  """
  Parse without intelligence a form from a request(), return it.
  """
  parsed_dict = {}
  parsed_dict['software_release'] = form['software_release'].encode()
  parsed_dict['software_type'] = form.get('software_type').encode()
  parsed_dict['partition_reference'] = form.get('partition_reference', '').encode()
  parsed_dict['partition_id'] = form.get('computer_partition_id', '').encode()
  parsed_dict['partition_parameter_kw'] = loads(form.get('partition_parameter_xml', EMPTY_DICT_XML).encode())
  parsed_dict['filter_kw'] = loads(form.get('filter_xml', EMPTY_DICT_XML).encode())
  # Note: currently ignored for slave instance (slave instances
  # are always started).
  parsed_dict['requested_state'] = loads(form.get('state').encode())

  return parsed_dict

run_id = ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])
def checkIfMasterIsCurrentMaster(master_url):
  """
  Because there are several ways to contact this server, we can't easily check
  in a request() if master_url is ourself or not. So we contact master_url,
  and if it returns an ID we know: it is ourself
  """
  # Dumb way: compare with listening host/port
  host = request.host
  port = request.environ['SERVER_PORT']
  if master_url == 'http://%s:%s/' % (host, port):
    return True

  # Hack way: call ourself
  slap = slapos.slap.slap()
  slap.initializeConnection(master_url)
  try:
    master_run_id = slap._connection_helper.GET('/getRunId')
  except:
    return False
  if master_run_id == run_id:
    return True
  return False

@app.route('/getRunId', methods=['GET'])
def getRunId():
  return run_id

def checkMasterUrl(master_url):
  """
  Check if master_url doesn't represent ourself, and check if it is whitelisted
  in multimaster configuration.
  """
  if not master_url:
    return False

  if checkIfMasterIsCurrentMaster(master_url):
    # master_url is current server: don't forward
    return False

  master_entry = app.config.get('multimaster').get(master_url, None)
  # Check if this master is known
  if not master_entry:
    # Check if it is ourself
    if not master_url.startswith('https') and checkIfMasterIsCurrentMaster(master_url):
      return False
    app.logger.warning('External SlapOS Master URL %s is not listed in multimaster list.' % master_url)
    abort(404)

  return True

def isRequestToBeForwardedToExternalMaster(parsed_request_dict):
    """
    Check if we HAVE TO forward the request.
    Several cases:
     * The request specifies a master_url in filter_kw
     * The software_release of the request is in a automatic forward list
    """
    master_url = parsed_request_dict['filter_kw'].get('master_url')

    if checkMasterUrl(master_url):
      # Don't allocate the instance locally, but forward to specified master
      return master_url

    software_release = parsed_request_dict['software_release']
    for mutimaster_url, mutimaster_entry in app.config.get('multimaster').iteritems():
      if software_release in mutimaster_entry['software_release_list']:
        # Don't allocate the instance locally, but forward to specified master
        return mutimaster_url
    return None

def forwardRequestToExternalMaster(master_url, request_form):
  """
  Forward instance request to external SlapOS Master.
  """
  master_entry = app.config.get('multimaster').get(master_url, {})
  key_file = master_entry.get('key')
  cert_file = master_entry.get('cert')
  if master_url.startswith('https') and (not key_file or not cert_file):
    app.logger.warning('External master %s configuration did not specify key or certificate.' % master_url)
    abort(404)
  if master_url.startswith('https') and not master_url.startswith('https') and (key_file or cert_file):
    app.logger.warning('External master %s configurqtion specifies key or certificate but is using plain http.' % master_url)
    abort(404)

  slap = slapos.slap.slap()
  if key_file:
    slap.initializeConnection(master_url, key_file=key_file, cert_file=cert_file)
  else:
    slap.initializeConnection(master_url)

  partition_reference = request_form['partition_reference'].encode()
  # Store in database
  execute_db('forwarded_partition_request', 'INSERT OR REPLACE INTO %s values(:partition_reference, :master_url)',
             {'partition_reference':partition_reference, 'master_url': master_url})

  new_request_form = request_form.copy()
  filter_kw = loads(new_request_form['filter_xml'].encode())
  filter_kw['source_instance_id'] = partition_reference
  new_request_form['filter_xml'] = dumps(filter_kw)

  xml = slap._connection_helper.POST('/requestComputerPartition', data=new_request_form)
  if type(xml) is unicode:
    xml = str(xml)
    xml.encode('utf-8')
  partition = loads(xml)

  # XXX move to other end
  partition._master_url = master_url

  return dumps(partition)

def getAllocatedInstance(partition_reference):
  """
  Look for existence of instance, if so return the
  corresponding partition dict, else return None
  """
  args = []
  a = args.append
  table = 'partition'
  q = 'SELECT * FROM %s WHERE partition_reference=?'
  a(partition_reference)
  return execute_db(table, q, args, one=True)

def getAllocatedSlaveInstance(slave_reference, requested_computer_id):
  """
  Look for existence of instance, if so return the
  corresponding partition dict, else return None
  """
  args = []
  a = args.append
  # XXX: Scope currently depends on instance which requests slave.
  # Meaning that two different instances requesting the same slave will
  # result in two different allocated slaves.
  table = 'slave'
  q = 'SELECT * FROM %s WHERE reference=? and computer_reference=?'
  a(slave_reference)
  a(requested_computer_id)
  # XXX: check there is only one result
  return execute_db(table, q, args, one=True)

def getRootPartition(reference):
  """Climb the partitions tree up by 'requested_by' link to get the root partition."""
  p = 'SELECT * FROM %s WHERE reference=?'
  partition = execute_db('partition', p, [reference], one=True)
  if partition is None:
    app.logger.warning("Nonexisting partition \"{}\". Known are\n{!s}".format(
      reference, execute_db("partition", "select reference, requested_by from %s")))
    return None

  parent_partition = execute_db('partition', p, [partition['requested_by']], one=True)
  while (parent_partition is not None and
         parent_partition['requested_by'] and
         parent_partition['requested_by'] != reference):
    partition = parent_partition
    reference = parent_partition['requested_by']
    parent_partition = execute_db('partition', p, [reference], one=True)

  return partition

def requestNotSlave(software_release, software_type, partition_reference, partition_id, partition_parameter_kw, filter_kw, requested_state):
  instance_xml = dict2xml(partition_parameter_kw)
  requested_computer_id = filter_kw['computer_guid']

  instance_xml = dict2xml(partition_parameter_kw)
  args = []
  a = args.append
  q = 'SELECT * FROM %s WHERE partition_reference=?'
  a(partition_reference)

  partition = execute_db('partition', q, args, one=True)

  args = []
  a = args.append
  q = 'UPDATE %s SET slap_state="busy"'

  if partition is None:
    partition = execute_db('partition',
        'SELECT * FROM %s WHERE slap_state="free" and computer_reference=?',
        [requested_computer_id], one=True)
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
  else:
    # XXX Check if software_release should be updated
    if partition['software_release'].encode() != software_release:
      q += ' ,software_release=?'
      a(software_release)
    if partition['requested_by']:
      root_partition = getRootPartition(partition['requested_by'])
      if root_partition and root_partition['requested_state'] != "started":
        # propagate parent state to child
        # child can be stopped or destroyed while parent is started
        requested_state = root_partition['requested_state']

  if requested_state:
    q += ', requested_state=?'
    a(requested_state)

  #
  # XXX change software_type when requested
  #
  if software_type:
    q += ' ,software_type=?'
    a(software_type)

  # Else: only update partition parameters
  if instance_xml:
    q += ' ,xml=?'
    a(instance_xml)
  q += ' WHERE reference=? AND computer_reference=?'
  a(partition['reference'].encode())
  a(partition['computer_reference'].encode())

  execute_db('partition', q, args)
  args = []
  partition = execute_db('partition', 'SELECT * FROM %s WHERE reference=? and computer_reference=?',
      [partition['reference'].encode(), partition['computer_reference'].encode()], one=True)
  address_list = []
  for address in execute_db('partition_network', 'SELECT * FROM %s WHERE partition_reference=?', [partition['reference']]):
    address_list.append((address['reference'], address['address']))

  if not requested_state:
    requested_state = 'started'
  # XXX it should be ComputerPartition, not a SoftwareInstance
  software_instance = SoftwareInstance(_connection_dict=xml2dict(partition['connection_xml']),
                                       _parameter_dict=xml2dict(partition['xml']),
                                       connection_xml=partition['connection_xml'],
                                       slap_computer_id=partition['computer_reference'].encode(),
                                       slap_computer_partition_id=partition['reference'],
                                       slap_software_release_url=partition['software_release'],
                                       slap_server_url='slap_server_url',
                                       slap_software_type=partition['software_type'],
                                       _instance_guid='%s-%s' % (partition['computer_reference'].encode(), partition['reference']),
                                       _requested_state=requested_state,
                                       ip_list=address_list)
  return software_instance


def requestSlave(software_release, software_type, partition_reference, partition_id, partition_parameter_kw, filter_kw, requested_state):
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
  requested_computer_id = filter_kw['computer_guid']
  instance_xml = dict2xml(partition_parameter_kw)

  # We will search for a master corresponding to request
  args = []
  a = args.append
  q = 'SELECT * FROM %s WHERE software_release=? and computer_reference=?'
  a(software_release)
  a(requested_computer_id)
  if software_type:
    q += ' AND software_type=?'
    a(software_type)
  if 'instance_guid' in filter_kw:
    q += ' AND reference=?'
    # instance_guid should be like: %s-%s % (requested_computer_id, partition_id)
    # But code is convoluted here, so we check
    instance_guid = filter_kw['instance_guid']
    if instance_guid.startswith(requested_computer_id):
      a(instance_guid[len(requested_computer_id) + 1:])
    else:
      a(instance_guid)

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
    slave_instance_list = xml_marshaller.xml_marshaller.loads(slave_instance_list.encode())
    for x in slave_instance_list:
      if x['slave_reference'] == slave_reference:
        slave_instance_list.remove(x)

  slave_instance_list.append(new_slave)

  # Update slave_instance_list in database
  args = []
  a = args.append
  q = 'UPDATE %s SET slave_instance_list=?'
  a(xml_marshaller.xml_marshaller.dumps(slave_instance_list))
  q += ' WHERE reference=? and computer_reference=?'
  a(partition['reference'].encode())
  a(requested_computer_id)
  execute_db('partition', q, args)
  args = []
  partition = execute_db('partition', 'SELECT * FROM %s WHERE reference=? and computer_reference=?',
      [partition['reference'].encode(), requested_computer_id], one=True)

  # Add slave to slave table if not there
  slave = execute_db('slave', 'SELECT * FROM %s WHERE reference=? and computer_reference=?',
                     [slave_reference, requested_computer_id], one=True)
  if slave is None:
    execute_db('slave',
               'INSERT OR IGNORE INTO %s (reference,computer_reference,asked_by,hosted_by) values(:reference,:computer_reference,:asked_by,:hosted_by)',
               [slave_reference, requested_computer_id, partition_id, partition['reference']])
    slave = execute_db('slave', 'SELECT * FROM %s WHERE reference=? and computer_reference=?',
                       [slave_reference, requested_computer_id], one=True)

  address_list = []
  for address in execute_db('partition_network',
                            'SELECT * FROM %s WHERE partition_reference=? and computer_reference=?',
                            [partition['reference'], partition['computer_reference']]):
    address_list.append((address['reference'], address['address']))

  # XXX it should be ComputerPartition, not a SoftwareInstance
  software_instance = SoftwareInstance(_connection_dict=xml2dict(slave['connection_xml']),
                                       _parameter_dict=xml2dict(instance_xml),
                                       slap_computer_id=partition['computer_reference'],
                                       slap_computer_partition_id=slave['hosted_by'],
                                       slap_software_release_url=partition['software_release'],
                                       slap_server_url='slap_server_url',
                                       slap_software_type=partition['software_type'],
                                       ip_list=address_list)

  return software_instance

@app.route('/softwareInstanceRename', methods=['POST'])
def softwareInstanceRename():
  new_name = request.form['new_name'].encode()
  computer_partition_id = request.form['computer_partition_id'].encode()
  computer_id = request.form['computer_id'].encode()

  q = 'UPDATE %s SET partition_reference = ? WHERE reference = ? AND computer_reference = ?'
  execute_db('partition', q, [new_name, computer_partition_id, computer_id])
  return 'done'

@app.route('/getComputerPartitionStatus', methods=['GET'])
def getComputerPartitionStatus():
  return xml_marshaller.xml_marshaller.dumps('Not implemented.')

@app.route('/computerBang', methods=['POST'])
def computerBang():
  return xml_marshaller.xml_marshaller.dumps('')

@app.route('/getComputerPartitionCertificate', methods=['GET'])
def getComputerPartitionCertificate():
  # proxy does not use partition certificate, but client calls this.
  return xml_marshaller.xml_marshaller.dumps({'certificate': '', 'key': ''})

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
      software_release_url_list = []
    return xml_marshaller.xml_marshaller.dumps(software_release_url_list)

