# -*- coding: utf-8 -*-
import httplib
import logging
import json
import os
import time
import slapos
import traceback
import logging
from re6st import  registry

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

def getComputerPartition(server_url, key_file, cert_file, computer_guid, partition_id):
  slap = slapos.slap.slap()

  # Redeploy instance to update published information
  slap.initializeConnection(server_url,
                            key_file,
                            cert_file)

  return slap.registerComputerPartition(computer_guid=computer_guid,
                                             partition_id=partition_id)

def requestAddToken(client, base_token_path):
  time.sleep(3)
  path_list = [x for x in os.listdir(base_token_path) if x.endswith('.add')]

  log.info("Searching tokens to add at %s and found %s." % (base_token_path, path_list))

  if not path_list:
    log.info("No new token to add. Exiting...")
    return

  for reference_key in path_list:
    request_file = os.path.join(base_token_path, reference_key)
    token = readFile(request_file)
    log.info("Including token %s for %s" % (token, reference_key))
    if token :
      reference = reference_key.split('.')[0]
      # email is unique as reference is also unique
      email = '%s@slapos' % reference.lower()
      try:
        result = client.addToken(email, token)
      except Exception:
        log.info('Request add token fail for %s... \n %s' % (request_file,
                    traceback.format_exc()))
        continue

      if result in (token, None):
        # update information
        log.info("New token added for slave instance %s. Updating file status..." %
                            reference)
        status_file = os.path.join(base_token_path, '%s.status' % reference)
        updateFile(status_file, 'TOKEN_ADDED')
        os.unlink(request_file)
    else:
      log.debug('Bad token. Request add token fail for %s...' % request_file)

def requestRemoveToken(client, base_token_path):
  path_list = [x for x in os.listdir(base_token_path) if x.endswith('.remove')]

  if not path_list:
    log.info("No token to delete. Exiting...")
    return

  for reference_key in path_list:
    request_file = os.path.join(base_token_path, reference_key)
    token = readFile(request_file)
    if token :
      reference = reference_key.split('.')[0]
      try:
        result = client.deleteToken(token)
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

    if revokeByMail(args['registry_url'],
                   '%s@slapos' % reference.lower(),
                   args['db']):
      os.unlink(os.path.join(base_token_path, reference_key))
      log.info("Certificate revoked for slave instance %s." % reference)
      return

    log.info("Failed to revoke email for %s" % reference)

def checkService(client, base_token_path, token_json, computer_partition):
  token_dict = loadJsonFile(token_json)
  updated = False
  if not token_dict:
    return

  # Check token status
  for slave_reference, token in token_dict.iteritems():
    log.info("%s %s" % (slave_reference, token))
    status_file = os.path.join(base_token_path, '%s.status' % slave_reference)
    if not os.path.exists(status_file):
      # This token is not added yet!
      log.info("Token %s dont exist yet." % status_file)
      continue

    if not client.isToken(str(token)):
      # Token is used to register client
      updateFile(status_file, 'TOKEN_USED')
      log.info("Token status of %s updated to 'used'." % slave_reference)

    status = readFile(status_file)
    log.info("Token %s has %s State." % (status_file, status))

    ipv6 = "::"
    ipv4 = "0.0.0.0"
    msg = status
    if status == 'TOKEN_ADDED':
      msg = 'Token is ready for use'
    elif status == 'TOKEN_USED':
      msg = 'Token not available, it has been used to generate re6stnet certificate.'

    email = '%s@slapos' % slave_reference.lower()
    if status == 'TOKEN_USED':
      try:
        ipv6 = client.getIPv6Address(str(email))
      except Exception:
        log.info('Error for dump ipv6 for %s... \n %s' % (slave_reference,
                                        traceback.format_exc()))

      log.info("%s, IPV6 = %s" % (slave_reference, ipv6))
      try:
        ipv4 = client.getIPv4Information(str(email)) or "0.0.0.0"
      except Exception:
        log.info('Error for dump ipv4 for %s... \n %s' % (slave_reference,
                                        traceback.format_exc()))

      log.info("%s, IPV4 = %s" % (slave_reference, ipv4))

    try:
      log.info("Update parameters for %s" % slave_reference)

      # Normalise the values as simple strings to be on the same format that
      # the values which come from master.
      computer_partition.setConnectionDict({'token': str(token),
                                            '1_info': str(msg),
                                            'ipv6': str(ipv6),
                                            'ipv4': str(ipv4)},
          slave_reference)
    except Exception:
      log.fatal("Error while sending slave %s informations: %s",
         slave_reference, traceback.format_exc())


def manage(args, can_bang=True):

  computer_guid = args['computer_id']
  partition_id = args['partition_id']
  server_url = args['server_url']
  key_file = args['key_file']
  cert_file = args['cert_file']

  client = registry.RegistryClient(args['registry_url'])
  base_token_path = args['token_base_path']
  token_json = args['token_json']

  log.info("ADD TOKEN")
  # Request Add new tokens
  requestAddToken(client, base_token_path)

  log.info("Remove TOKEN")
  # Request delete removed token
  requestRemoveToken(client, base_token_path)

  computer_partition = getComputerPartition(server_url, key_file,
                              cert_file, computer_guid, partition_id)

  log.info("Update Services")
  # check status of all token
  checkService(client, base_token_path,
            token_json, computer_partition)

