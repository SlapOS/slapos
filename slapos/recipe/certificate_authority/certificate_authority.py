from __future__ import print_function

import os
import subprocess
import time
from six.moves import configparser
import uuid


def popenCommunicate(command_list, input=None):
  subprocess_kw = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True)
  if input is not None:
    subprocess_kw.update(stdin=subprocess.PIPE)
  popen = subprocess.Popen(command_list, **subprocess_kw)
  result = popen.communicate(input)[0]
  if popen.returncode is None:
    popen.kill()
  if popen.returncode != 0:
    raise ValueError('Issue during calling %r, result was:\n%s' % (
      command_list, result))
  return result


class CertificateAuthority:
  def __init__(self, key, certificate, openssl_binary,
      openssl_configuration, request_dir):
    self.key = key
    self.certificate = certificate
    self.openssl_binary = openssl_binary
    self.openssl_configuration = openssl_configuration
    self.request_dir = request_dir

  def checkAuthority(self):
    file_list = [ self.key, self.certificate ]
    ca_ready = True
    for f in file_list:
      if not os.path.exists(f):
        ca_ready = False
        break
    if ca_ready:
      return
    for f in file_list:
      if os.path.exists(f):
        os.unlink(f)
    try:
      # no CA, let us create new one
      popenCommunicate([self.openssl_binary, 'req', '-nodes', '-config',
          self.openssl_configuration, '-new', '-x509', '-extensions',
          'v3_ca', '-keyout', self.key, '-out', self.certificate,
          '-days', '10950'], 'Certificate Authority %s\n' % uuid.uuid1())
    except:
      try:
        for f in file_list:
          if os.path.exists(f):
            os.unlink(f)
      except:
        # do not raise during cleanup
        pass
      raise

  def _checkCertificate(self, common_name, key, certificate):
    file_list = [key, certificate]
    ready = True
    for f in file_list:
      if not os.path.exists(f):
        ready = False
        break
    if ready:
      return False
    for f in file_list:
      if os.path.exists(f):
        os.unlink(f)
    csr = certificate + '.csr'
    try:
      popenCommunicate([self.openssl_binary, 'req', '-config',
        self.openssl_configuration, '-nodes', '-new', '-keyout',
        key, '-out', csr, '-days', '3650'],
        common_name + '\n')
      try:
        popenCommunicate([self.openssl_binary, 'ca', '-batch', '-config',
          self.openssl_configuration, '-out', certificate,
          '-infiles', csr])
      finally:
        if os.path.exists(csr):
          os.unlink(csr)
    except:
      try:
        for f in file_list:
          if os.path.exists(f):
            os.unlink(f)
      except:
        # do not raise during cleanup
        pass
      raise
    else:
      return True

  def checkRequestDir(self):
    for request_file in os.listdir(self.request_dir):
      parser = configparser.RawConfigParser()
      parser.readfp(open(os.path.join(self.request_dir, request_file), 'r'))
      if self._checkCertificate(parser.get('certificate', 'name'),
          parser.get('certificate', 'key_file'), parser.get('certificate',
            'certificate_file')):
        print('Created certificate %r' % parser.get('certificate', 'name'))

def runCertificateAuthority(*args):
  ca = CertificateAuthority(*args)
  while True:
    ca.checkAuthority()
    ca.checkRequestDir()
    # XXX
    # Antoine: I really don't like that at all. It wastes useful CPU time.
    #          I think it would be a greater idea to use pyinotify
    #          <http://pyinotify.sourceforge.net/>
    #          Or we could use select() with socket as well.
    time.sleep(60)
    # end XXX
