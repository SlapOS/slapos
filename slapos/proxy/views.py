from flask import g, Flask, request, abort
import xml_marshaller
from lxml import etree
from slapos.slap.slap import Computer, ComputerPartition, SoftwareRelease, SoftwareInstance
import sqlite3

app = Flask(__name__)
DB_VERSION = app.open_resource('schema.sql').readline().strip().split(':')[1]

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

def dict2xml(dictionnary):
  instance = etree.Element('instance')
  for parameter_id, parameter_value in dictionnary.iteritems():
    # cast everything to string
    parameter_value = str(parameter_value)
    etree.SubElement(instance, "parameter",
                     attrib={'id':parameter_id}).text = parameter_value
  return etree.tostring(instance, pretty_print=True,
                                xml_declaration=True, encoding='utf-8')

def partitiondict2partition(partition):
  slap_partition = ComputerPartition(app.config['computer_id'],
      partition['reference'])
  slap_partition._requested_state = 'started'
  if partition['software_release']:
    slap_partition._need_modification = 1
  else:
    slap_partition._need_modification = 0
  slap_partition._parameter_dict = xml2dict(partition['xml'])
  address_list = []
  for address in execute_db('partition_network', 'SELECT * FROM %s WHERE partition_reference=?', [partition['reference']]):
    address_list.append((address['reference'], address['address']))
  slap_partition._parameter_dict['ip_list'] = address_list
  slap_partition._parameter_dict['slap_software_type'] = partition['software_type']
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
  schema = schema.read() % dict(version = DB_VERSION)
  g.db.cursor().executescript(schema)
  g.db.commit()

@app.after_request
def after_request(response):
  g.db.commit()
  g.db.close()
  return response

@app.route('/getComputerInformation', methods=['GET'])
def getComputerInformation():
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
    raise UnauthorizedError, "Only accept request for: %s" % \
                             app.config['computer_id']

@app.route('/setComputerPartitionConnectionXml', methods=['POST'])
def setComputerPartitionConnectionXml():
  computer_id = request.form['computer_id']
  computer_partition_id = request.form['computer_partition_id']
  connection_xml = request.form['connection_xml']
  connection_dict = xml_marshaller.xml_marshaller.loads(
                                              connection_xml.encode())
  connection_xml = dict2xml(connection_dict)
  query = 'UPDATE %s SET connection_xml=? WHERE reference=?'
  argument_list = [connection_xml, computer_partition_id.encode()]
  execute_db('partition', query, argument_list)
  return 'done'

@app.route('/buildingSoftwareRelease', methods=['POST'])
def buildingSoftwareRelease():
  return 'Ignored'

@app.route('/availableSoftwareRelease', methods=['POST'])
def availableSoftwareRelease():
  computer_id = request.form['computer_id']
  url = request.form['url']
  return 'Ignored'

@app.route('/softwareReleaseError', methods=['POST'])
def softwareReleaseError():
  return 'Ignored'

@app.route('/buildingComputerPartition', methods=['POST'])
def buildingComputerPartition():
  computer_id = request.form['computer_id']
  computer_partition_id = request.form['computer_partition_id']
  return 'Ignored'

@app.route('/availableComputerPartition', methods=['POST'])
def availableComputerPartition():
  computer_id = request.form['computer_id']
  computer_partition_id = request.form['computer_partition_id']
  return 'Ignored'

@app.route('/softwareInstanceError', methods=['POST'])
def softwareInstanceError():
  computer_id = request.form['computer_id']
  computer_partition_id = request.form['computer_partition_id']
  error_log = request.form['error_log']
  return 'Ignored'

@app.route('/startedComputerPartition', methods=['POST'])
def startedComputerPartition():
  computer_id = request.form['computer_id']
  computer_partition_id = request.form['computer_partition_id']
  return 'Ignored'

@app.route('/stoppedComputerPartition', methods=['POST'])
def stoppedComputerPartition():
  computer_id = request.form['computer_id']
  computer_partition_id = request.form['computer_partition_id']
  return 'Ignored'

@app.route('/destroyedComputerPartition', methods=['POST'])
def destroyedComputerPartition():
  computer_id = request.form['computer_id']
  computer_partition_id = request.form['computer_partition_id']
  return 'Ignored'

@app.route('/requestComputerPartition', methods=['POST'])
def requestComputerPartition():
  software_release = request.form['software_release'].encode()
  # some supported parameters
  software_type = request.form.get('software_type', 'RootSoftwareInstance'
      ).encode()
  partition_reference = request.form.get('partition_reference', '').encode()
  partition_id = request.form.get('computer_partition_id', '').encode()
  partition_parameter_kw = request.form.get('partition_parameter_xml', None)
  if partition_parameter_kw:
    partition_parameter_kw = xml_marshaller.xml_marshaller.loads(
                                              partition_parameter_kw.encode())
  else:
    partition_parameter_kw = {}
  instance_xml = dict2xml(partition_parameter_kw)
  args = []
  a = args.append
  q = 'SELECT * FROM %s WHERE software_release=?'
  a(software_release)
  if software_type:
    q += ' AND software_type=?'
    a(software_type)
  if partition_reference:
    q += ' AND partition_reference=?'
    a(partition_reference)
  if partition_id:
    q += ' AND requested_by=?'
    a(partition_id)
  partition = execute_db('partition', q, args, one=True)
  if partition is None:
    partition = execute_db('partition',
        'SELECT * FROM %s WHERE slap_state="free"', (), one=True)
    if partition is None:
      app.logger.warning('No more free computer partition')
      abort(408)
  args = []
  a = args.append
  q = 'UPDATE %s SET software_release=?, slap_state="busy"'
  a(software_release)
  if software_type:
    q += ' ,software_type=?'
    a(software_type)
  if partition_reference:
    q += ' ,partition_reference=?'
    a(partition_reference)
  if partition_id:
    q += ' ,requested_by=?'
    a(partition_id)
  if instance_xml:
    q+= ' ,xml=?'
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
  return xml_marshaller.xml_marshaller.dumps(SoftwareInstance(**dict(
    xml=partition['xml'],
    connection_xml=partition['connection_xml'],
    slap_computer_id=app.config['computer_id'],
    slap_computer_partition_id=partition['reference'],
    slap_software_release_url=partition['software_release'],
    slap_server_url='slap_server_url',
    slap_software_type=partition['software_type'],
    slave_id_list=[],
    ip_list=address_list
    )))
  abort(408)
  computer_id = request.form.get('computer_id')
  computer_partition_id = request.form.get('computer_partition_id')
  software_type = request.form.get('software_type')
  partition_reference = request.form.get('partition_reference')
  shared_xml = request.form.get('shared_xml')
  partition_parameter_xml = request.form.get('partition_parameter_xml')
  filter_xml = request.form.get('filter_xml')
  raise NotImplementedError

@app.route('/useComputer', methods=['POST'])
def useComputer():
  computer_id = request.form['computer_id']
  use_string = request.form['use_string']
  return 'Ignored'

@app.route('/loadComputerConfigurationFromXML', methods=['POST'])
def loadComputerConfigurationFromXML():
  xml = request.form['xml']
  computer_dict = xml_marshaller.xml_marshaller.loads(str(xml))
  if app.config['computer_id'] == computer_dict['reference']:
    args = []
    a = args.append
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
    raise UnauthorizedError, "Only accept request for: %s" % \
                             app.config['computer_id']

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
    raise UnauthorizedError, "Only accept request for: %s" % \
                             app.config['computer_id']

@app.route('/supplySupply', methods=['POST'])
def supplySupply():
  url = request.form['url']
  computer_id = request.form['computer_id']
  if app.config['computer_id'] == computer_id:
    execute_db('software', 'INSERT OR REPLACE INTO %s VALUES(?)', [url])
  else:
    raise UnauthorizedError, "Only accept request for: %s" % \
                             app.config['computer_id']
  return '%r added' % url
