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

def updateFile(file_path, value):
  if readFile(file_path) != value:
    writeFile(file_path, value)
    return True
  return False

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
        updateFile(status_file, 'TOKEN_ADDED')
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
      except httplib.NOTFOUND:
        # Token is alread removed.
        result = True
      except Exception:
        log.debug('Request delete token fail for %s... \n %s' % (request_file,
                    traceback.format_exc()))
        continue
      else:
        # certificate is invalidated, it will be revoked
        writeFile(os.path.join(base_token_path, '%s.revoke' % reference), '')

      if result in (True, 'True'):
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

def checkService(args, can_bang=True):
  base_token_path = args['token_base_path']
  token_dict = loadJsonFile(args['token_json'])

  if not token_dict:
    return

  call_bang = False
  client = registry.RegistryClient(args['registry_url'])

  # Check token status
  for slave_reference, token in token_dict.iteritems():
    log.info("%s %s" % (slave_reference, token))
    status_file = os.path.join(base_token_path, '%s.status' % slave_reference)
    if not os.path.exists(status_file):
      # This token is not added yet!
      log.info("Token %s dont exist yet." % status_file)
      continue

    if not client.isValidToken(str(token)):
      # Token is used to register client
      call_bang = True
      updateFile(status_file, 'TOKEN_USED')
      log.info("Token status of %s updated to 'used'." % slave_reference)

    msg = readFile(status_file)
    log.info("Token %s has %s State." % (status_file, msg))

    if msg == 'TOKEN_USED':
      try:
        log.info("Dumping ipv6...")
        email = '%s@slapos' % slave_reference.lower()
        try:
          ipv6 = client.getIPv6Address(str(email))
          ipv6_file = os.path.join(base_token_path, '%s.ipv6' % slave_reference)
          ipv6_changed = updateFile(ipv6_file, ipv6)
        except Exception:
          log.info('Error for dump ipv6 for %s... \n %s' % (slave_reference,
                                          traceback.format_exc()))
          continue

        log.info("%s, IPV6 = %s" % (slave_reference, ipv6))
        log.info("Dumping ipv4...")
        try:
          ipv4 = "0.0.0.0"
          ipv6_prefix = client.getIPv6Prefix(str(email))
          if not int(ipv6_prefix) == 0:
            if client.isPeer(ipv6_prefix):
              ipv4 = client.getIPv4Information(ipv6_prefix)
              log.info("Found ipv4: %s" % ipv4)

          ipv4_file = os.path.join(base_token_path, '%s.ipv4' % slave_reference)
          ipv4_changed = updateFile(ipv4_file, ipv4)
        except Exception:
          log.info('Error for dump ipv4 for %s... \n %s' % (slave_reference,
                                          traceback.format_exc()))
          continue

        log.info("%s, IPV4 = %s, IPV6_PREFIX = %s" % (slave_reference, ipv4, ipv6_prefix))

      except IOError:
        log.debug('Error when writing in file %s. Could not update status of %s...' %
          (status_file, slave_reference))

      if ipv4_changed or ipv6_changed:
        call_bang = True

  if call_bang and can_bang:
    bang(args)

def manage(args):
  # Request Add new tokens
  requestAddToken(args)

  # Request delete removed token
  requestRemoveToken(args)

  # check status of all token
  checkService(args)

