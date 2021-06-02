##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
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
import subprocess

from slapos.recipe.librecipe import GenericBaseRecipe
import socket
import struct
import os, stat
import string, random
import json
import traceback
from slapos import slap

class Recipe(GenericBaseRecipe):
  
  def __init__(self, buildout, name, options):
    """Default initialisation"""
    self.slap = slap.slap()

    # SLAP related information
    slap_connection = buildout['slap-connection']
    self.computer_id = slap_connection['computer-id']
    self.computer_partition_id = slap_connection['partition-id']
    self.server_url = slap_connection['server-url']
    self.software_release_url = slap_connection['software-release-url']
    self.key_file = slap_connection.get('key-file')
    self.cert_file = slap_connection.get('cert-file')
    self.slave_list = options['slave-instance-list']

    return GenericBaseRecipe.__init__(self, buildout, name, options)

  def getSerialFromIpv6(self, ipv6):
    prefix = ipv6.split('/')[0].lower()
    hi, lo = struct.unpack('!QQ', socket.inet_pton(socket.AF_INET6, prefix))
    ipv6_int = (hi << 64) | lo
    serial = '0x1%x' % ipv6_int

    # delete non significant part
    for part in prefix.split(':')[::-1]:
      if part:
        for i in ['0']*(4 - len(part)):
          part = i + part
        serial = serial.split(part)[0] + part
        break

    return serial

  def generateCertificate(self):
    key_file = self.options['key-file'].strip()
    cert_file = self.options['cert-file'].strip()
    dh_file = self.options['dh-file'].strip()
    if not os.path.exists(dh_file):
      dh_command = [self.options['openssl-bin'], 'dhparam', '-out',
                            '%s' % dh_file, self.options['key-size']]
      try:
        subprocess.check_call(dh_command)
      except Exception:
        if os.path.exists(dh_file):
          os.unlink(dh_file)
        raise

    if not os.path.exists(cert_file):
      serial = self.getSerialFromIpv6(self.options['ipv6-prefix'].strip())
      key_command = [self.options['openssl-bin'], 'genrsa', '-out',
                            '%s' % key_file, self.options['key-size']]

      #'-config', openssl_configuration
      cert_command = [self.options['openssl-bin'], 'req', '-nodes', '-new',
                  '-x509', '-batch', '-key', '%s' % key_file, '-set_serial',
                  '%s' % serial, '-days', '3650', '-out', '%s' % cert_file]

      try:
        subprocess.check_call(key_command)
      except Exception:
        if os.path.exists(key_file):
          os.unlink(key_file)
        raise

      try:
        subprocess.check_call(cert_command)
      except Exception:
        if os.path.exists(cert_file):
          os.unlink(cert_file)
        raise

  def generateSlaveTokenList(self, slave_instance_list, token_file):
    to_remove_dict = {}
    to_add_dict = {}
    token_dict = self.loadJsonFile(token_file)

    reference_list = [slave_instance.get('slave_reference') for slave_instance
                        in slave_instance_list]
    for reference in reference_list:
      if not reference in token_dict:
        # we generate new token
        number = reference.split('-')[1]
        new_token = number + ''.join(random.sample(string.ascii_lowercase, 20))
        token_dict[reference] = new_token
        to_add_dict[reference] = new_token

    for reference in list(token_dict):
      if not reference in reference_list:
        # This slave instance is destroyed ?
        to_remove_dict[reference] = token_dict.pop(reference)

    return token_dict, to_add_dict, to_remove_dict

  def loadJsonFile(self, path):
    if os.path.exists(path):
      with open(path, 'r') as f:
        content = f.read()
      return json.loads(content)
    else:
      return {}

  def writeFile(self, path, data):
    with open(path, 'w') as f:
      f.write(data)
    return path

  def readFile(self, path):
    if os.path.exists(path):
      with open(path, 'r') as f:
        content = f.read()
      return content
    return ''

  def genHash(self, length):
    hash_path = os.path.join(self.options['conf-dir'], '%s-hash' % length)
    if not os.path.exists(hash_path):
      pool = string.letters + string.digits
      hash_string = ''.join(random.choice(pool) for i in xrange(length))
      self.writeFile(hash_path, hash_string)
    else:
      hash_string = self.readFile(hash_path)

    return hash_string

  def install(self):
    token_save_path = os.path.join(self.options['conf-dir'], 'token.json')
    token_list_path = self.options['token-dir']

    self.generateCertificate()

    registry_url = 'http://%s:%s/' % (self.options['ipv4'], self.options['port'])
    token_dict, add_token_dict, rm_token_dict = self.generateSlaveTokenList(
                                              self.slave_list, token_save_path)

    # write request add token
    for reference in add_token_dict:
      path = os.path.join(token_list_path, '%s.add' % reference)
      if not os.path.exists(path):
        self.createFile(path, add_token_dict[reference])

    # write request remove token
    for reference in rm_token_dict:
      path = os.path.join(token_list_path, '%s.remove' % reference)
      if not os.path.exists(path):
        self.createFile(path, rm_token_dict[reference])
        # remove request add token if exists
        add_path = os.path.join(token_list_path, '%s.add' % reference)
        if os.path.exists(add_path):
          os.unlink(add_path)

    self.createFile(token_save_path, json.dumps(token_dict))

    computer_dict = dict(partition_id=self.computer_partition_id,
                        computer_guid=self.computer_id,
                        master_url=self.server_url,
                        cert_file=self.cert_file,
                        key_file=self.key_file)

    return self.createPythonScript(
        self.options['manager-wrapper'].strip(),
        __name__ + '.re6stnet.manage',
        (registry_url, token_list_path, token_save_path, computer_dict)
      )
