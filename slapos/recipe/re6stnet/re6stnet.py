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
  db = sqlite3.connect(db_path,
                       isolation_level=None,
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

  log.info("Searching tokens to add at %s and found %s." % (base_token_path, path_list))

  if not path_list:
    log.info("No new token to add. Exiting...")
    return

  client = registry.RegistryClient(registry_url)
  call_bang = False

  for reference_key in path_list:
    request_file = os.path.join(base_token_path, reference_key)
    token = readFile(request_file)
    log.info("Including token %s for %s" % (token, reference_key))
    if token :
      reference = reference_key.split('.')[0]
      # email is unique as reference is also unique
      email = '%s@slapos' % reference.lower()
      try:
        result = client.requestAddToken(email, token)
      except Exception:
        log.info('Request add token fail for %s... \n %s' % (request_file,
                    traceback.format_exc()))
        continue

      if result and result == token:
        # update information
        log.info("New token added for slave instance %s. Updating file status..." %
                            reference)
        status_file = os.path.join(base_token_path, '%s.status' % reference)
        writeFile(status_file, 'TOKEN_ADDED')
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
  path_list = [x for x in os.listdir(base_token_path) if x.endswith('.revoke')]

  for reference_key in path_list:
    reference = reference_key.split('.')[0]
    # XXX - email is always unique
    email = '%s@slapos' % reference.lower()

    if revokeByMail(args['registry_url'],
                   '%s@slapos' % reference.lower(), 
                   args['db']):
      os.unlink(os.path.join(base_token_path, reference_key))
      log.info("Certificate revoked for slave instance %s." % reference)
      return

    log.info("Failed to revoke email for %s" % reference)


#  ipv6, ipv6_prefix, ipv6_changed = dumpIPv6Network(slave_reference, db, network, ipv6_file)
# For each email SOFTINT-xxx@slapos a status should be created probably. How to deal with legacy?
def dumpIPv6Network(slave_reference, client, ipv6_file):
  email = '%s@slapos' % slave_reference.lower()
  try:
      ipv6_prefix = client.getIPv6Prefix(str(email))
      ipv6 = client.getIPv6Address(str(email))
      log.info(ipv6)
      changed = readFile(ipv6_file) != ipv6
      writeFile(ipv6_file, ipv6)
      return ipv6, ipv6_prefix, changed
  except Exception:
    log.info('XXX for %s... \n %s' % (slave_reference,
              traceback.format_exc()))

def dumpIPv4Network(ipv6_prefix, network, ipv4_file, client, peer_prefix_list):
  try:
    if int(ipv6_prefix) == 0:
      # workarround to ignore the first node
      ipv4 = "0.0.0.0"
      changed = readFile(ipv4_file) != ipv4
      writeFile(ipv4_file, ipv4)
      return ipv4, changed

    peers = []

    log.info(ipv6_prefix)
    log.info(peer_prefix_list)
    peer_list = [prefix for prefix in peer_prefix_list if prefix == ipv6_prefix ]

    if len(peer_list) == 0:
      log.info("Unable to find such prefix on database")
      ipv4 = "0.0.0.0"

    else:
      peer = peer_list[0]

      ipv4 = client.getIPv4Information(peer)
      if ipv4 is None:
         ipv4 = "0.0.0.0"


    changed = readFile(ipv4_file) != ipv4
    writeFile(ipv4_file, ipv4)
    return ipv4, changed
  except Exception:
    log.info('XXX for %s... \n %s' % (ipv6_prefix,
              traceback.format_exc()))
    return "0.0.0.0", False


def getPeerPrefixList(network):
    return [prefix for prefix in
      ctl.iterRoutes("/var/run/re6stnet/babeld.sock", network)]


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
  network = client.getNetworkBin()

  sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

  peer_prefix_list = getPeerPrefixList(network)


  # Check token status
  for slave_reference, token in token_dict.iteritems():
    log.info("%s %s" % (slave_reference, token))
    status_file = os.path.join(base_token_path, '%s.status' % slave_reference)
    ipv6_file = os.path.join(base_token_path, '%s.ipv6' % slave_reference)
    ipv4_file = os.path.join(base_token_path, '%s.ipv4' % slave_reference)
    if not os.path.exists(status_file):
      # This token is not added yet!
      log.info("Token %s dont exist yet." % status_file)
      continue

    # Better check directly on registry the state
    # if Token exist on the table or not.

    msg = readFile(status_file)
    log.info("Token %s has %s State." % (status_file, msg))
    if msg == 'TOKEN_USED':
      log.info("Dumping ipv6...")

      ipv6, ipv6_prefix, ipv6_changed = dumpIPv6Network(slave_reference, client, ipv6_file)

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

