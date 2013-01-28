# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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


import base64
import ConfigParser
from getpass import getpass
import logging
from optparse import OptionParser, Option
import os
import shutil
import sys
import tempfile
import urllib2


class SlapError(Exception):
  """
  Slap error
  """
  def __init__(self, message):
    self.msg = message

class UsageError(SlapError):
  pass

class ExecError(SlapError):
  pass

class Parser(OptionParser):
  """
  Parse all arguments.
  """
  def __init__(self, usage=None, version=None):
    """
    Initialize all options possibles.
    """
    OptionParser.__init__(self, usage=usage, version=version,
                          option_list=[
      Option("--interface-name",
             help="Interface name to access internet",
             default='eth0',
             type=str),
      Option("--master-url",
             help="URL of vifib master",
             default='https://slap.vifib.com',
             type=str),
      Option("--master-url-web",
             help="URL of vifib master webservice to register certificates",
             default='https://www.vifib.net',
             type=str),
      Option("--partition-number",
             help="Number of partition on computer",
             default='10',
             type=int),
      Option("--ipv4-local-network",
             help="Base of ipv4 local network",
             default='10.0.0.0/16',
             type=str),
      Option("--ipv6-interface",
             help="Interface name to get ipv6",
             default='',
             type=str),
      Option("--login",
             help="User login on Vifib master webservice",
             default=None,
             type=str),
      Option("--password",
             help="User password on Vifib master webservice",
             default=None,
             type=str),
      Option("-t", "--create-tap",
             help="""Will trigger creation of one virtual "tap" interface per \
Partition and attach it to primary interface. Requires primary interface to be \
 a bridge. defaults to false. Needed to host virtual machines.""",
             default=False,
             action="store_true"),
      Option("-n", "--dry-run",
             help="Simulate the execution steps",
             default=False,
             action="store_true"),
   ])

  def check_args(self):
    """
    Check arguments
    """
    (options, args) = self.parse_args()
    if len(args) != 1:
      self.error("Incorrect number of arguments")
    node_name = args[0]

    if options.password != None and options.login == None :
      self.error("Please enter your login with your password")


    return options, node_name


def get_login():
  """Get user id and encode it for basic identification"""
  login = raw_input("Vifib Login: ")
  password = getpass()
  identification = base64.encodestring('%s:%s' % (login, password))[:-1]
  return identification


def check_login(identification, master_url_web):
  """Check if logged correctly on vifib"""
  request = urllib2.Request(master_url_web)
  # Prepare header for basic authentification
  authheader =  "Basic %s" % identification
  request.add_header("Authorization", authheader)
  home_page_url = urllib2.urlopen(request).read()
  if 'Logout' in home_page_url:
    return 1
  else : return 0
  

def get_certificates(identification, node_name, master_url_web):
  """Download certificates on vifib master"""
  register_server_url = '/'.join([master_url_web, ("add-a-server/WebSection_registerNewComputer?dialog_id=WebSection_viewServerInformationDialog&dialog_method=WebSection_registerNewComputer&title={}&object_path=/erp5/web_site_module/hosting/add-a-server&update_method=&cancel_url=https%3A//www.vifib.net/add-a-server/WebSection_viewServerInformationDialog&Base_callDialogMethod=&field_your_title=Essai1&dialog_category=None&form_id=view".format(node_name))])
  request = urllib2.Request(register_server_url)
  # Prepare header for basic authentification
  authheader =  "Basic %s" % identification
  request.add_header("Authorization", authheader)  
  url = urllib2.urlopen(request)  
  page = url.read()
  return page


def parse_certificates(source):
  """Parse html gotten from vifib to make certificate and key files"""
  c_start = source.find("Certificate:")
  c_end = source.find("</textarea>", c_start)
  k_start = source.find("-----BEGIN PRIVATE KEY-----")
  k_end = source.find("</textarea>", k_start)
  return [source[c_start:c_end], source[k_start:k_end]]


def get_computer_name(certificate):
  """Parse certificate to get computer name and return it"""
  k = certificate.find("COMP-")
  i = certificate.find("/email", k)
  return certificate[k:i]

def save_former_config(config):
  """Save former configuration if found"""
  # Check for config file in /etc/opt/slapos/
  if os.path.exists('/etc/opt/slapos/slapos.cfg'):
    former_slapos_configuration = '/etc/opt/slapos'
  else : former_slapos_configuration = 0
  if former_slapos_configuration:
    saved_slapos_configuration = former_slapos_configuration + '.old'
    while True:
      if os.path.exists(saved_slapos_configuration):
        print "Slapos configuration detected in %s" % saved_slapos_configuration
        if saved_slapos_configuration[len(saved_slapos_configuration) - 1] != 'd' :
          saved_slapos_configuration = saved_slapos_configuration[:len(saved_slapos_configuration) - 1] \
              + str(int(saved_slapos_configuration[len(saved_slapos_configuration) - 1]) + 1 )
        else :
          saved_slapos_configuration += ".1"
      else: break
    config.logger.info("Former slapos configuration detected in %s moving to %s" % (former_slapos_configuration, saved_slapos_configuration))
    shutil.move(former_slapos_configuration, saved_slapos_configuration)

def get_slapos_conf_example():
  """
  Get slapos.cfg.example and return its path
  """
  register_server_url = "http://git.erp5.org/gitweb/slapos.core.git/blob_plain/HEAD:/slapos.cfg.example"
  request = urllib2.Request(register_server_url)
  url = urllib2.urlopen(request)  
  page = url.read()
  _, path = tempfile.mkstemp()
  slapos_cfg_example = open(path,'w')
  slapos_cfg_example.write(page)
  slapos_cfg_example.close()
  return path


def slapconfig(config):
  """Base Function to configure slapos in /etc/opt/slapos"""
  dry_run = config.dry_run
  # Create slapos configuration directory if needed
  slap_configuration_directory = os.path.normpath(config.slapos_configuration)

  if not os.path.exists(slap_configuration_directory):
    config.logger.info ("Creating directory: %s" % slap_configuration_directory)
    if not dry_run:
      os.mkdir(slap_configuration_directory, 0711)

  user_certificate_repository_path = os.path.join(slap_configuration_directory,'ssl')
  if not os.path.exists(user_certificate_repository_path):
    config.logger.info ("Creating directory: %s" % user_certificate_repository_path)
    if not dry_run:
      os.mkdir(user_certificate_repository_path, 0711)

  key_file = os.path.join(user_certificate_repository_path, 'key') 
  cert_file = os.path.join(user_certificate_repository_path, 'certificate')
  for (src, dst) in [(config.key, key_file), (config.certificate,
      cert_file)]:
    config.logger.info ("Copying to %r, and setting minimum privileges" % dst)
    if not dry_run:
      destination = open(dst,'w')
      destination.write(''.join(src))
      destination.close()
      os.chmod(dst, 0600)
      os.chown(dst, 0, 0)

  certificate_repository_path = os.path.join(slap_configuration_directory, 'ssl', 'partition_pki')
  if not os.path.exists(certificate_repository_path):
    config.logger.info ("Creating directory: %s" % certificate_repository_path)
    if not dry_run:
      os.mkdir(certificate_repository_path, 0711)
  
  # Put slapos configuration file
  slap_configuration_file_location = os.path.join(slap_configuration_directory,
                                                  'slapos.cfg')
  config.logger.info ("Creating slap configuration: %s"
                      % slap_configuration_file_location)

  # Get example configuration file
  slapos_cfg_example = get_slapos_conf_example()
  configuration_example_parser = ConfigParser.RawConfigParser()
  configuration_example_parser.read(slapos_cfg_example)  
  os.remove(slapos_cfg_example)

  # prepare slapos section
  slaposconfig = dict(
    computer_id=config.computer_id, master_url=config.master_url,
    key_file=key_file, cert_file=cert_file,
    certificate_repository_path=certificate_repository_path)
  for key in slaposconfig:
    configuration_example_parser.set('slapos', key, slaposconfig[key])

  # prepare slapformat
  slapformatconfig = dict(
    interface_name=config.interface_name,
    ipv4_local_network=config.ipv4_local_network,
    partition_amount=config.partition_number,
    create_tap=config.create_tap
    )
  for key in slapformatconfig :
    configuration_example_parser.set('slapformat', key, slapformatconfig[key])

  if not config.ipv6_interface == '':
    configuration_example_parser.set('slapformat',
                                     'ipv6_interface',
                                     config.ipv6_interface)

  if not dry_run:
    slap_configuration_file = open(slap_configuration_file_location, "w")
    configuration_example_parser.write(slap_configuration_file)

  config.logger.info ("SlapOS configuration: DONE")


# Class containing all parameters needed for configuration
class Config:
  def setConfig(self, option_dict, node_name):
    """
    Set options given by parameters.
    """
    # Set options parameters
    for option, value in option_dict.__dict__.items():
      setattr(self, option, value)
    self.node_name = node_name

    # Define logger for register
    self.logger = logging.getLogger('Register')
    self.logger.setLevel(logging.DEBUG)
    # create console handler and set level to debug
    self.ch = logging.StreamHandler()
    self.ch.setLevel(logging.INFO)
    # create formatter
    self.formatter = logging.Formatter('%(levelname)s - %(message)s')
    # add formatter to ch
    self.ch.setFormatter(self.formatter)
    # add ch to logger
    self.logger.addHandler(self.ch)

  def COMPConfig(self, slapos_configuration, computer_id, certificate, key):
    self.slapos_configuration = slapos_configuration
    self.computer_id = computer_id
    self.certificate = certificate
    self.key = key

  def displayUserConfig(self):
    self.logger.debug("Computer Name: %s" % self.node_name)
    self.logger.debug("Master URL: %s" % self.master_url)
    self.logger.debug("Number of partition: %s" % self.partition_number)
    self.logger.debug("Interface Name: %s" % self.interface_name)
    self.logger.debug("Ipv4 sub network: %s" % self.ipv4_local_network)
    self.logger.debug("Ipv6 Interface: %s" %self.ipv6_interface)

def register(config):
  """Register new computer on VIFIB and generate slapos.cfg"""
  # Get User identification and check them
  if config.login == None :
    while True :
      print ("Please enter your Vifib login")
      user_id = get_login()
      if check_login(user_id, config.master_url_web):
        break
      config.logger.warning ("Wrong login/password")
  else:
    if config.password == None :
      config.password = getpass()
    user_id = base64.encodestring('%s:%s' % (config.login, config.password))[:-1]
    if not check_login(user_id, config.master_url_web):
      config.logger.error ("Wrong login/password")
      return 1

  # Get source code of page having certificate and key
  certificate_key = get_certificates(user_id, config.node_name, config.master_url_web)
  # Parse certificate and key and get computer id
  certificate_key = parse_certificates(certificate_key)
  certificate = certificate_key[0]
  key = certificate_key[1]
  COMP = get_computer_name(certificate)
  # Getting configuration parameters
  slapos_configuration = '/etc/opt/slapos/'
  config.COMPConfig(slapos_configuration=slapos_configuration,
                   computer_id=COMP,
                   certificate = certificate,
                   key = key
                   )
  # Save former configuration
  if not config.dry_run:
    save_former_config(config)
  # Prepare Slapos Configuration
  slapconfig(config)

  print "Node has successfully been configured as %s." % COMP
  return 0

def main():
  "Run default configuration."
  usage = "usage: slapos node %s NODE_NAME [options] " % sys.argv[0]
  try:
    # Parse arguments
    config = Config()
    config.setConfig(*Parser(usage=usage).check_args())
    return_code = register(config)
  except UsageError, err:
    print >> sys.stderr, err.msg
    print >> sys.stderr, "For help use --help"
    return_code = 16
  except ExecError, err:
    print >> sys.stderr, err.msg
    return_code = 16
  except SystemExit, err:
    # Catch exception raise by optparse
    return_code = err

  sys.exit(return_code)
