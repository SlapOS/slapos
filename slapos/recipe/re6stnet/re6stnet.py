# -*- coding: utf-8 -*-
import logging
import json
import os
import time
import sqlite3
import slapos
import traceback
import logging
import socket
import select
from re6st import tunnel, ctl, registry, utils, x509
from OpenSSL import crypto


log = logging.getLogger('SLAPOS-RE6STNET')
logging.basicConfig(level=logging.INFO)

logging.trace = logging.debug 

class iterRoutes(object):

    _waiting = True

    def __new__(cls, control_socket, network):
        self = object.__new__(cls)
        c = ctl.Babel(control_socket, self, network)
        c.request_dump()
        while self._waiting:
            args = {}, {}, ()
            c.select(*args)
            utils.select(*args)
        return (prefix
            for neigh_routes in c.neighbours.itervalues()
            for prefix in neigh_routes[1]
            if prefix)

    def babel_dump(self):
        self._waiting = False

def loadJsonFile(path):
  if os.path.exists(path):
    with open(path, 'r') as f:
      content = f.read()
      return json.loads(content)
  else:
    return {}

def writeFile(path, data):
  with open(path, 'w') as f:
    f.write(data)

def readFile(path):
  if os.path.exists(path):
    with open(path, 'r') as f:
      content = f.read()
    return content
  return ''

def getDb(db_path):
  db = sqlite3.connect(db_path, isolation_level=None,
                                                  check_same_thread=False)
  db.text_factory = str

  return db.cursor()

def bang(args):
  computer_guid = args['computer_id']
  partition_id = args['partition_id']
  slap = slapos.slap.slap()

  # Redeploy instance to update published information
  slap.initializeConnection(args['server_url'], args['key_file'],
                                                          args['cert_file'])
  partition = slap.registerComputerPartition(computer_guid=computer_guid,
                                                   partition_id=partition_id)
  partition.bang(message='Published parameters changed!')
  log.info("Bang with message 'parameters changed'...")


def requestAddToken(args, can_bang=True):

  time.sleep(3)
  registry_url = args['registry_url']
  base_token_path = args['token_base_path']
  path_list = [x for x in os.listdir(base_token_path) if x.endswith('.add')]

  if not path_list:
    log.info("No new token to add. Exiting...")
    return

  client = registry.RegistryClient(registry_url)
  call_bang = False

  for reference_key in path_list:
    request_file = os.path.join(base_token_path, reference_key)
    token = readFile(request_file)
    if token :
      reference = reference_key.split('.')[0]
      # email is unique as reference is also unique
      email = '%s@slapos' % reference.lower()
      try:
        result = client.requestAddToken(token, email)
      except Exception:
        log.debug('Request add token fail for %s... \n %s' % (request_file,
                    traceback.format_exc()))
        continue
      if result and result == token:
        # update information
        log.info("New token added for slave instance %s. Updating file status..." %
                            reference)
        writeFile(os.path.join(base_token_path, '%s.status' % reference),
                    'TOKEN_ADDED')
        os.unlink(request_file)
        call_bang = True
    else:
      log.debug('Bad token. Request add token fail for %s...' % request_file)

  if can_bang and call_bang:
    bang(args)

def requestRemoveToken(args):
  base_token_path = args['token_base_path']
  path_list = [x for x in os.listdir(base_token_path) if x.endswith('.remove')]

  if not path_list:
    log.info("No token to delete. Exiting...")
    return

  client = registry.RegistryClient(args['registry_url'])
  for reference_key in path_list:
    request_file = os.path.join(base_token_path, reference_key)
    token = readFile(request_file)
    if token :
      reference = reference_key.split('.')[0]
      try:
        result = client.requestDeleteToken(token)
      except Exception:
        log.debug('Request delete token fail for %s... \n %s' % (request_file,
                    traceback.format_exc()))
        continue
      else:
        # certificate is invalidated, it will be revoked
        writeFile(os.path.join(base_token_path, '%s.revoke' % reference), '')
      if result == 'True':
        # update information
        log.info("Token deleted for slave instance %s. Clean up file status..." %
                            reference)
      if result in ['True', 'False']:
        os.unlink(request_file)
        status_file = os.path.join(base_token_path, '%s.status' % reference)
        if os.path.exists(status_file):
          os.unlink(status_file)
        ipv6_file = os.path.join(base_token_path, '%s.ipv6' % reference)
        if os.path.exists(ipv6_file):
          os.unlink(ipv6_file)

    else:
      log.debug('Bad token. Request add token fail for %s...' % request_file)

def requestRevoqueCertificate(args):

  base_token_path = args['token_base_path']
  db = getDb(args['db'])
  path_list = [x for x in os.listdir(base_token_path) if x.endswith('.revoke')]
  client = registry.RegistryClient(args['registry_url'])

  for reference_key in path_list:
    reference = reference_key.split('.')[0]
    # XXX - email is always unique
    email = '%s@slapos' % reference.lower()
    cert_string = ''
    try:
      cert_string, = db.execute("SELECT cert FROM cert WHERE email = ?",
          (email,)).next()
    except StopIteration:
      # Certificate was not generated yet !!!
      pass

    try:
      if cert_string:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_string)
        cn = x509.subnetFromCert(cert)
        result = client.revoke(str(cn))
        time.sleep(2)
    except Exception:
      log.debug('Request revoke certificate fail for %s... \n %s' % (reference,
                  traceback.format_exc()))
      continue
    else:
      os.unlink(os.path.join(base_token_path, reference_key))
      log.info("Certificate revoked for slave instance %s." % reference)


def dumpIPv6Network(slave_reference, db, network, ipv6_file):
  email = '%s@slapos' % slave_reference.lower()

  try:
    cert_string, = db.execute("SELECT cert FROM cert WHERE email = ?",
        (email,)).next()
  except StopIteration:
    # Certificate was not generated yet !!!
    pass

  try:
    if cert_string:
      cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_string)
      cn = x509.subnetFromCert(cert)
      subnet = network + utils.binFromSubnet(cn)
      ipv6 = utils.ipFromBin(subnet)
      changed = readFile(ipv6_file) != ipv6
      writeFile(ipv6_file, ipv6)
      return ipv6, utils.binFromSubnet(cn), changed
  except Exception:
    log.debug('XXX for %s... \n %s' % (slave_reference,
              traceback.format_exc()))

def sendto(sock, prefix, code):
  return sock.sendto("%s\0%c" % (prefix, code), ('::1', tunnel.PORT))      

def recv(sock, code):
  try:
    prefix, msg = sock.recv(1<<16).split('\0', 1)
    int(prefix, 2)
  except ValueError:
    pass
  else:
    if msg and ord(msg[0]) == code:
      return prefix, msg[1:]
  return None, None

def dumpIPv4Network(ipv6_prefix, network, ipv4_file, sock, peer_prefix_list):
  try:

    if ipv6_prefix == "00000000000000000000000000000000":
      # workarround to ignore the first node
      ipv4 = "0.0.0.0"
      changed = readFile(ipv4_file) != ipv4
      writeFile(ipv4_file, ipv4)
      return ipv4, changed

    peers = []

    peer_list = [prefix for prefix in peer_prefix_list if prefix == ipv6_prefix ]

    if len(peer_list) == 0:
      raise ValueError("Unable to find such prefix on database")

    peer = peer_list[0]

    sendto(sock, peer, 1)
    s = sock,
    timeout = 15 
    end = timeout + time.time()

    while select.select(s, (), (), timeout)[0]:
      prefix, msg = recv(sock, 1)
      if prefix == peer:
        break

      timeout = max(0, end - time.time())
    else:
     logging.info("Timeout while querying address for %s/%s", int(peer, 2), len(peer))
     msg = ""

    if "," in msg:
      ipv4 = msg.split(',')[0]
    else:
      ipv4 = "0.0.0.0"
    changed = readFile(ipv4_file) != ipv4
    writeFile(ipv4_file, ipv4)
    return ipv4, changed
  except Exception:
    log.info('XXX for %s... \n %s' % (ipv6_prefix,
              traceback.format_exc()))
    return "0.0.0.0", False

def checkService(args, can_bang=True):
  base_token_path = args['token_base_path']
  token_dict = loadJsonFile(args['token_json'])

  if not token_dict:
    return

  db = getDb(args['db'])
  call_bang = False

  computer_guid = args['computer_id']
  partition_id = args['partition_id']
  slap = slapos.slap.slap()
  client = registry.RegistryClient(args['registry_url'])
  ca = client.getCa()
  network = x509.networkFromCa(crypto.load_certificate(crypto.FILETYPE_PEM, ca))

  sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

  peer_prefix_list = [prefix for prefix in
    iterRoutes("/var/run/re6stnet/babeld.sock", network)]


  # Check token status
  for slave_reference, token in token_dict.iteritems():
    status_file = os.path.join(base_token_path, '%s.status' % slave_reference)
    ipv6_file = os.path.join(base_token_path, '%s.ipv6' % slave_reference)
    ipv4_file = os.path.join(base_token_path, '%s.ipv4' % slave_reference)
    if not os.path.exists(status_file):
      # This token is not added yet!
      log.info("Token %s dont exist yet." % status_file)
      continue

    msg = readFile(status_file)
    log.info("Token %s has %s State." % (status_file, msg))
    if msg == 'TOKEN_USED':
      log.info("Dumping ipv6...")
      ipv6, ipv6_prefix, ipv6_changed = dumpIPv6Network(slave_reference, db, network, ipv6_file)
      log.info("%s, IPV6 = %s, IPV6_PREFIX = %s" % (slave_reference, ipv6, ipv6_prefix))
      _, ipv4_changed = dumpIPv4Network(ipv6_prefix, network, ipv4_file, sock, peer_prefix_list)
      if ipv4_changed or ipv6_changed:
        call_bang = True
      continue

    # Check if token is not in the database
    status = False
    try:
        token_found, = db.execute("SELECT token FROM token WHERE token = ?",
            (token,)).next()
        if token_found == token:
          status = True
    except StopIteration:
        pass
    if not status:
      # Token is used to register client
      call_bang = True
      try:
        writeFile(status_file, 'TOKEN_USED')
        dumpIPv6Network(slave_reference, db, network, ipv6_file)
        dumpIPv4Network(ipv6_prefix, network, ipv4_file, sock, peer_prefix_list)
        log.info("Token status of %s updated to 'used'." % slave_reference)
      except IOError:
        # XXX- this file should always exists
        log.debug('Error when writing in file %s. Clould not update status of %s...' %
                              (status_file, slave_reference))

  if call_bang and can_bang:
    bang(args)

def manage(args):
  # Request Add new tokens
  requestAddToken(args)

  # Request delete removed token
  requestRemoveToken(args)

  # check status of all token
  checkService(args)

