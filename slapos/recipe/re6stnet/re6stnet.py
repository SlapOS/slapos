# -*- coding: utf-8 -*-
import logging
import json
import time
import slapos
from pathlib import Path
from re6st import registry

log = logging.getLogger('SLAPOS-RE6STNET')
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

def loadJsonFile(path):
  if path.exists():
    with open(path, 'r') as f:
      return json.load(f)
  return {}

def writeFile(path, data):
  with open(path, 'w') as f:
    f.write(data)

def readFile(path):
  if path.exists():
    with open(path, 'r') as f:
      content = f.read()
    return content
  return ''

def updateFile(file_path, value):
  if readFile(file_path) != value:
    writeFile(file_path, value)
    return True
  return False

def getComputerPartition(master_url, key_file, cert_file,
                         computer_guid, partition_id):
  slap = slapos.slap.slap()
  # Redeploy instance to update published information
  slap.initializeConnection(master_url, key_file, cert_file)
  return slap.registerComputerPartition(computer_guid, partition_id)

def requestAddToken(client, token_base_path):
  time.sleep(3)
  path_list = [x for x in token_base_path.iterdir() if x.suffix == '.add']

  log.info("Searching tokens to add at %s and found %s.", token_base_path, path_list)

  if not path_list:
    log.info("No new token to add. Exiting...")
    return

  for reference_key in path_list:
    request_file = token_base_path / reference_key
    token = readFile(request_file)
    log.info("Including token %s for %s", token, reference_key)
    if token :
      reference = reference_key.stem
      # email is unique as reference is also unique
      email = '%s@slapos' % reference.lower()
      try:
        result = client.addToken(email, token)
      except Exception:
        log.exception('Request add token fail for %s...', request_file)
        continue

      if result in (token, None):
        # update information
        log.info("New token added for slave instance %s. Updating file status...",
                            reference)
        status_file = (token_base_path / reference).with_suffix('.status')
        updateFile(status_file, 'TOKEN_ADDED')
        request_file.unlink()
    else:
      log.debug('Bad token. Request add token fail for %s...', request_file)

def requestRemoveToken(client, token_base_path):
  path_list = [x for x in token_base_path.iterdir() if x.suffix == '.remove']

  if not path_list:
    log.info("No token to delete. Exiting...")
    return

  for reference_key in path_list:
    request_file = token_base_path / reference_key
    token = readFile(request_file)
    if token :
      reference = reference_key.stem
      try:
        result = client.deleteToken(token)
      except Exception:
        log.exception('Request delete token fail for %s...', request_file)
        continue

      if not client.isToken(str(token)):
        # Token has been destroyed or is already used, we can proceed to revoke the certificate
        email = '%s@slapos' % reference.lower()
        try:
          cn = client.getNodePrefix(str(email))
        except Exception:
          log.exception('getNodePrefix for email %s failed', email)
          continue
        if cn:
          try:
            client.revoke(cn)
          except Exception:
            log.exception('Revoke cert with cn %s failed...', cn)
            continue


        log.info("Token deleted for slave instance %s. Clean up file status...",
                            reference)
        request_file.unlink()
        status_file = request_file.with_suffix('.status')
        status_file.unlink(missing_ok=True)
        ipv6_file = request_file.with_suffix('.ipv6')
        ipv6_file.unlink(missing_ok=True)
    else:
      log.error('Bad token. Request remove token fail for %s...', request_file)

def checkService(client, token_base_path, token_json, computer_partition):
  token_dict = loadJsonFile(token_json)
  updated = False
  if not token_dict:
    return

  # Check token status
  for slave_reference, token in token_dict.items():
    log.info("%s %s", slave_reference, token)
    status_file = (token_base_path / slave_reference).with_suffix('.status')
    if not status_file.exists():
      # This token is not added yet!
      log.info("Token %s dont exist yet." % status_file)
      continue

    if not client.isToken(str(token)):
      # Token is used to register client
      updateFile(status_file, 'TOKEN_USED')
      log.info("Token status of %s updated to 'used'.", slave_reference)

    status = readFile(status_file)
    log.info("Token %s has %s State.", status_file, status)

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
        ipv6 = client.getIPv6Address(str(email)).decode()
      except Exception:
        log.exception('Error for dump ipv6 for %s...', slave_reference)
      log.info("%s, IPV6 = %s", slave_reference, ipv6)

      try:
        ipv4 = client.getIPv4Information(str(email)).decode() or "0.0.0.0"
      except Exception:
        log.exception('Error for dump ipv4 for %s...', slave_reference)
      log.info("%s, IPV4 = %s" % (slave_reference, ipv4))

    try:
      log.info("Update parameters for %s", slave_reference)

      # Normalise the values as simple strings to be on the same format that
      # the values which come from master.
      computer_partition.setConnectionDict({'token': str(token),
                                            '1_info': str(msg),
                                            'ipv6': str(ipv6),
                                            'ipv4': str(ipv4)},
          slave_reference)
    except Exception:
      log.exception("Error while sending slave %s information",
         slave_reference)


def manage(registry_url, token_base_path, token_json,
           computer_dict, can_bang=True):
  token_base_path = Path(token_base_path)
  client = registry.RegistryClient(registry_url)

  log.info("ADD TOKEN")
  # Request Add new tokens
  requestAddToken(client, token_base_path)

  log.info("Remove TOKEN")
  # Request delete removed token
  requestRemoveToken(client, token_base_path)

  computer_partition = getComputerPartition(**computer_dict)

  log.info("Update Services")
  # check status of all token
  checkService(client, token_base_path, Path(token_json), computer_partition)

