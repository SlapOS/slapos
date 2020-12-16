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
import os
import hashlib
from six.moves import configparser
import tempfile

from slapos.recipe.librecipe import GenericBaseRecipe
from slapos.util import str2bytes
from .certificate_authority import popenCommunicate

class Recipe(GenericBaseRecipe):

  def setPath(self):
    self.ca_dir = self.options['ca-dir']
    self.request_directory = self.options['requests-directory']
    self.ca_private = self.options['ca-private']
    self.ca_certs = self.options['ca-certs']
    self.ca_newcerts = self.options['ca-newcerts']
    self.ca_key_ext = '.key'
    self.ca_crt_ext = '.crt'

  def install(self):
    ca_country_code = self.options.get('country-code', 'XX')
    ca_email = self.options.get('email', 'xx@example.com')
    # XXX-BBB: State by mistake has been configured as string "('State',)"
    #          string, so keep this for backward compatibility of existing
    #          automatically setup CAs
    ca_state = self.options.get('state', "('State',)")
    ca_city = self.options.get('city', 'City')
    ca_company = self.options.get('company', 'Company')

    self.setPath()

    config = dict(ca_dir=self.ca_dir, request_dir=self.request_directory)

    for f in ['crlnumber', 'serial']:
      if not os.path.exists(os.path.join(self.ca_dir, f)):
        open(os.path.join(self.ca_dir, f), 'w').write('01')
    if not os.path.exists(os.path.join(self.ca_dir, 'index.txt')):
      open(os.path.join(self.ca_dir, 'index.txt'), 'w').write('')
    openssl_configuration = os.path.join(self.ca_dir, 'openssl.cnf')
    config.update(
        working_directory=self.ca_dir,
        country_code=ca_country_code,
        state=ca_state,
        city=ca_city,
        company=ca_company,
        email_address=ca_email,
    )
    self.createFile(openssl_configuration, self.substituteTemplate(
      self.getTemplateFilename('openssl.cnf.ca.in'), config))

    return self.createPythonScript(
      self.options['wrapper'],
      __name__ + '.certificate_authority.runCertificateAuthority',
      (os.path.join(self.ca_private, 'cakey.pem'),
       os.path.join(self.ca_dir, 'cacert.pem'),
       self.options['openssl-binary'],
       openssl_configuration,
       self.request_directory)
    )

class Request(Recipe):

  def setPath(self):
    self.request_directory = self.options['requests-directory']
    self.ca_private = self.options['ca-private']
    self.ca_certs = self.options['ca-certs']
    self.ca_key_ext = '.key'
    self.ca_crt_ext = '.crt'

  def _options(self, options):
    if 'name' not in options:
      options['name'] = self.name

  def install(self):
    self.setPath()

    key_file = self.options['key-file']
    cert_file = self.options['cert-file']

    key_content = self.options.get('key-content', None)
    cert_content = self.options.get('cert-content', None)
    request_needed = True

    name = self.options['name']
    hash_ = hashlib.sha512(str2bytes(name)).hexdigest()
    key = os.path.join(self.ca_private, hash_ + self.ca_key_ext)
    certificate = os.path.join(self.ca_certs, hash_ + self.ca_crt_ext)

    # XXX Ugly hack to quickly provide custom certificate/key to everyone using the recipe
    if key_content and cert_content:
      self._checkCertificateKeyConsistency(key_content, cert_content)
      open(key, 'w').write(key_content)
      open(certificate, 'w').write(cert_content)
      request_needed = False
    else:
      parser = configparser.RawConfigParser()
      parser.add_section('certificate')
      parser.set('certificate', 'name', name)
      parser.set('certificate', 'key_file', key)
      parser.set('certificate', 'certificate_file', certificate)
      parser.write(open(os.path.join(self.request_directory, hash_), 'w'))

    for link in [key_file, cert_file]:
      if os.path.islink(link):
        os.unlink(link)
      elif os.path.exists(link):
        raise OSError("%r file should be a symbolic link." % link)

    os.symlink(key, key_file)
    os.symlink(certificate, cert_file)

    path_list = [key_file, cert_file]
    if request_needed:
      wrapper = self.createWrapper(
        self.options['wrapper'],
        (self.options['executable'],),
        wait_list=(certificate, key),
      )
      path_list.append(wrapper)

    return path_list

  def _checkCertificateKeyConsistency(self, key, certificate):
    openssl_binary = self.options.get('openssl-binary', 'openssl')

    # Simple test if the user/certificates are readable and don't raise
    popenCommunicate((openssl_binary, 'x509', '-noout', '-text'), certificate)
    popenCommunicate((openssl_binary, 'rsa', '-noout', '-text'), key)

    # Check if the key and certificate match
    modulus_cert = popenCommunicate((openssl_binary, 'x509', '-noout', '-modulus'), certificate)
    modulus_key = popenCommunicate((openssl_binary, 'rsa', '-noout', '-modulus'), key)
    if modulus_cert != modulus_key:
      raise ValueError("The key and certificate provided don't patch each other. Please check your parameters")
