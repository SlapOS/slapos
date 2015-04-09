# -*- coding: utf-8 -*-
import logging
import json
import os
import time
import sqlite3
import slapos
import traceback

from re6st import registry, x509
from OpenSSL import crypto

log = logging.getLogger('SLAPOS-RE6STNET')
logging.basicConfig(level=logging.DEBUG)

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

  # Check token status
  for slave_reference, token in token_dict.iteritems():
    status_file = os.path.join(base_token_path, '%s.status' % slave_reference)
    if not os.path.exists(status_file):
      # This token is not added yet!
      continue

    msg = readFile(status_file)
    if msg == 'TOKEN_USED':
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
        time.sleep(1)
        writeFile(status_file, 'TOKEN_USED')
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

