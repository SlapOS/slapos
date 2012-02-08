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
import logging
import os
import sys
import pkg_resources
import warnings
if sys.version_info < (2, 6):
  warnings.warn('Used python version (%s) is old and have problems with'
      ' IPv6 connections' % sys.version.split('\n')[0])
import socket
import subprocess
import traceback
import time
#from time import strftime

from SlapObject import Software, Partition, WrongPermissionError, \
    PathDoesNotExistError
import argparse
import ConfigParser
from utils import updateFile
from utils import createPrivateDirectory
from utils import setRunning
from utils import setFinished
from utils import getSoftwareUrlHash
from slapos import slap
from slapos.slap import NotFoundError
from slapos.slap.slap import ServerError
from utils import dropPrivileges
from utils import SlapPopen
from svcbackend import launchSupervisord
import tempfile
from time import strftime
import StringIO
from lxml import etree


MANDATORY_PARAMETER_LIST = [
    'computer_id',
    'instance_root',
    'master_url',
    'software_root',
]


def parseArgumentTupleAndReturnSlapgridObject(*argument_tuple):
  """Parses arguments either from command line, from method parameters or from
     config file. Then returns a new instance of slapgrid.Slapgrid with those
     parameters. Also returns the options dict and unused variable list, and
     configures logger.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument("--instance-root",
                    help="The instance root directory location.")
  parser.add_argument("--software-root",
                    help="The software_root directory location.")
  parser.add_argument("--master-url",
                    help="The master server URL. Mandatory.")
  parser.add_argument("--computer-id",
                    help="The computer id defined in the server.")
  parser.add_argument("--supervisord-socket",
                    help="The socket supervisor will use.")
  parser.add_argument("--supervisord-configuration-path",
                    help="The location where supervisord configuration " \
                           "will be stored.")
  parser.add_argument("--usage-report-periodicity",
                    type=int, default="24",
                    help="The periodicity of usage report sends, in hours.")
  parser.add_argument("--buildout", help="Location of buildout binary.",
                    default=None)
  parser.add_argument("--pidfile",
                    help="The location where pidfile will be created.")
  parser.add_argument("--logfile",
                    help="The location where slapgrid logfile will be " \
                           "created.")
  parser.add_argument("--key_file", help="SSL Authorisation key file.")
  parser.add_argument("--cert_file",
      help="SSL Authorisation certificate file.")
  parser.add_argument("--signature_private_key_file", help="Signature private key file.")
  parser.add_argument("--master_ca_file", help="Root certificate of SlapOS "
      "master key.")
  parser.add_argument("--certificate_repository_path",
      help="Path to directory where downloaded certificates would be stored.")
  parser.add_argument("-c", "--console", action="store_true", default=False,
      help="Enables console output and live output from subcommands.")
  parser.add_argument("-v", "--verbose", action="store_true", default=False,
      help="Be verbose.")
  parser.add_argument("--promise-timeout",
                      type=int, default=3,
                      help="Promise timeout in seconds.")
  parser.add_argument("configuration_file", nargs=1, type=argparse.FileType(),
      help="SlapOS configuration file.")

  # Parses arguments
  if argument_tuple == ():
    # No arguments given to entry point : we parse sys.argv.
    argument_option_instance = parser.parse_args()
  else:
    argument_option_instance = \
      parser.parse_args(list(argument_tuple))
  # Parses arguments from config file, if needed, then merge previous arguments
  option_dict = {}
  configuration_file = argument_option_instance.configuration_file[0]
  # Loads config (if config specified)
  slapgrid_configuration = ConfigParser.SafeConfigParser()
  slapgrid_configuration.readfp(configuration_file)
  # Merges the two dictionnaries
  option_dict = dict(slapgrid_configuration.items("slapos"))
  if slapgrid_configuration.has_section("networkcache"):
    option_dict.update(dict(slapgrid_configuration.items("networkcache")))
  for argument_key, argument_value in vars(argument_option_instance
      ).iteritems():
    if argument_value is not None:
      option_dict.update({argument_key: argument_value})
  # Configures logger.
  #XXX: We need to configure it as soon as possible, so I do it here.
  logger_format = '%(asctime)s %(name)-18s: %(levelname)-8s %(message)s'
  if option_dict['verbose']:
    level = logging.DEBUG
  else:
    level = logging.INFO
  if option_dict.get('logfile'):
    logging.basicConfig(filename=option_dict['logfile'],
      format=logger_format, level=level)
  if option_dict['console']:
    logging.basicConfig(level=level)
  missing_mandatory_parameter_list = []
  for mandatory_parameter in MANDATORY_PARAMETER_LIST:
    if not mandatory_parameter in option_dict:
      missing_mandatory_parameter_list.append(mandatory_parameter)

  repository_required = False
  if 'key_file' in option_dict:
    repository_required = True
    if not 'cert_file' in option_dict:
      missing_mandatory_parameter_list.append('cert_file')
  if 'cert_file' in option_dict:
    repository_required = True
    if not 'key_file' in option_dict:
      missing_mandatory_parameter_list.append('key_file')
  if repository_required:
    if 'certificate_repository_path' not in option_dict:
      missing_mandatory_parameter_list.append('certificate_repository_path')

  if len(missing_mandatory_parameter_list) > 0:
    parser.error('Missing mandatory parameters:\n%s' % '\n'.join(
      missing_mandatory_parameter_list))

  key_file = option_dict.get('key_file')
  cert_file = option_dict.get('cert_file')
  master_ca_file = option_dict.get('master_ca_file')
  signature_private_key_file = option_dict.get('signature_private_key_file')

  mandatory_file_list = [key_file, cert_file, master_ca_file]
  # signature_private_key_file is not mandatory, we must be able to run
  # slapgrid scripts without this parameter.
  if signature_private_key_file:
    mandatory_file_list.append(signature_private_key_file)

  for k in ['shacache-cert-file', 'shacache-key-file', 'shadir-cert-file',
      'shadir-key-file']:
    mandatory_file_list.append(option_dict.get(k, None))

  for f in mandatory_file_list:
    if f is not None:
      if not os.path.exists(f):
        parser.error('File %r does not exists.' % f)

  certificate_repository_path = option_dict.get('certificate_repository_path')
  if certificate_repository_path is not None:
    if not os.path.isdir(certificate_repository_path):
      parser.error('Directory %r does not exists' %
          certificate_repository_path)

  # Supervisord configuration location
  if not option_dict.get('supervisord_configuration_path'):
    option_dict['supervisord_configuration_path'] = \
      os.path.join(option_dict['instance_root'], 'etc', 'supervisord.conf')
  # Supervisord socket
  if not option_dict.get('supervisord_socket'):
    option_dict['supervisord_socket'] = \
      os.path.join(option_dict['instance_root'], 'supervisord.socket')

  signature_certificate_list_string = \
    option_dict.get('signature-certificate-list', None)
  if signature_certificate_list_string is not None:
    cert_marker = "-----BEGIN CERTIFICATE-----"
    signature_certificate_list = [cert_marker + '\n' + q.strip() \
      for q in signature_certificate_list_string.split(cert_marker) \
        if q.strip()]
  else:
    signature_certificate_list = None

  # Returning new Slapgrid instance and options
  return ([Slapgrid(software_root=option_dict['software_root'],
            instance_root=option_dict['instance_root'],
            master_url=option_dict['master_url'],
            computer_id=option_dict['computer_id'],
            supervisord_socket=option_dict['supervisord_socket'],
            supervisord_configuration_path=option_dict[
              'supervisord_configuration_path'],
            usage_report_periodicity=option_dict['usage_report_periodicity'],
            key_file=key_file,
            cert_file=cert_file,
            master_ca_file=master_ca_file,
            certificate_repository_path=certificate_repository_path,
            signature_private_key_file=signature_private_key_file,
            signature_certificate_list=signature_certificate_list,
            download_binary_cache_url=\
              option_dict.get('download-binary-cache-url', None),
            upload_binary_cache_url=\
              option_dict.get('upload-binary-cache-url', None),
            upload_cache_url=option_dict.get('upload-cache-url', None),
            download_binary_dir_url=\
              option_dict.get('download-binary-dir-url', None),
            upload_binary_dir_url=\
              option_dict.get('upload-binary-dir-url', None),
            upload_dir_url=option_dict.get('upload-dir-url', None),
            console=option_dict['console'],
            buildout=option_dict.get('buildout'),
            promise_timeout=option_dict['promise_timeout'],
            shacache_cert_file=option_dict.get('shacache-cert-file', None),
            shacache_key_file=option_dict.get('shacache-key-file', None),
            shadir_cert_file=option_dict.get('shadir-cert-file', None),
            shadir_key_file=option_dict.get('shadir-key-file', None),
            ),
          option_dict])


def realRun(argument_tuple, method_list):
  clean_run = True
  slapgrid_object, option_dict = \
      parseArgumentTupleAndReturnSlapgridObject(*argument_tuple)
  pidfile = option_dict.get('pidfile')
  if pidfile:
    setRunning(pidfile)
  try:
    for method in method_list:
      if not getattr(slapgrid_object, method)():
        clean_run = False
  finally:
    if pidfile:
      setFinished(pidfile)
  if clean_run:
    sys.exit(0)
  else:
    sys.exit(1)


def run(*argument_tuple):
  """Hooks for generic entry point to proces Software Releases (sr),
     Computer Partitions (cp) and Usage Reports (ur)
     Will run one by one each task (sr, cp, ur). If specified,
     will run in the user wanted order.
  """
  realRun(argument_tuple, ['processSoftwareReleaseList',
    'processComputerPartitionList', 'agregateAndSendUsage'])


def runSoftwareRelease(*argument_tuple):
  """Hook for entry point to process Software Releases only
  """
  realRun(argument_tuple, ['processSoftwareReleaseList'])


def runComputerPartition(*argument_tuple):
  """Hook for entry point to process Computer Partitions only
  """
  realRun(argument_tuple, ['processComputerPartitionList'])


def runUsageReport(*argument_tuple):
  """Hook for entry point to process Usage Reports only
  """
  realRun(argument_tuple, ['agregateAndSendUsage'])


class Slapgrid(object):
  """ Main class for SlapGrid. Fetches and processes informations from master
  server and pushes usage information to master server.
  """

  class PromiseError(Exception):
    pass

  def __init__(self,
               software_root,
               instance_root,
               master_url,
               computer_id,
               supervisord_socket,
               supervisord_configuration_path,
               usage_report_periodicity,
               buildout,
               key_file=None,
               cert_file=None,
               signature_private_key_file=None,
               signature_certificate_list=None,
               download_binary_cache_url=None,
               upload_binary_cache_url=None,
               upload_cache_url=None,
               download_binary_dir_url=None,
               upload_binary_dir_url=None,
               upload_dir_url=None,
               master_ca_file=None,
               certificate_repository_path=None,
               console=False,
               promise_timeout=3,
               shacache_cert_file=None,
               shacache_key_file=None,
               shadir_cert_file=None,
               shadir_key_file=None):
    """Makes easy initialisation of class parameters"""
    # Parses arguments
    self.software_root = os.path.abspath(software_root)
    self.instance_root = os.path.abspath(instance_root)
    self.master_url = master_url
    self.computer_id = computer_id
    self.supervisord_socket = supervisord_socket
    self.supervisord_configuration_path = supervisord_configuration_path
    self.usage_report_periodicity = usage_report_periodicity
    self.key_file = key_file
    self.cert_file = cert_file
    self.master_ca_file = master_ca_file
    self.certificate_repository_path = certificate_repository_path
    self.signature_private_key_file = signature_private_key_file
    self.signature_certificate_list = signature_certificate_list
    self.download_binary_cache_url = download_binary_cache_url
    self.upload_binary_cache_url = upload_binary_cache_url
    self.upload_cache_url = upload_cache_url
    self.download_binary_dir_url = download_binary_dir_url
    self.upload_binary_dir_url = upload_binary_dir_url
    self.upload_dir_url = upload_dir_url
    self.shacache_cert_file = shacache_cert_file
    self.shacache_key_file = shacache_key_file
    self.shadir_cert_file = shadir_cert_file
    self.shadir_key_file = shadir_key_file
    # Configures logger
    self.logger = logging.getLogger('Slapgrid')
    # Creates objects from slap module
    self.slap = slap.slap()
    self.slap.initializeConnection(self.master_url, key_file=self.key_file,
        cert_file=self.cert_file, master_ca_file=self.master_ca_file)
    self.computer = self.slap.registerComputer(self.computer_id)
    # Defines all needed paths
    self.instance_etc_directory = os.path.join(self.instance_root, 'etc')
    self.supervisord_configuration_directory = \
        os.path.join(self.instance_etc_directory, 'supervisord.conf.d')
    self.console = console
    self.buildout = buildout
    self.promise_timeout = promise_timeout

  def checkEnvironmentAndCreateStructure(self):
    """Checks for software_root and instance_root existence, then creates
       needed files and directories.
    """
    # Checks for software_root and instance_root existence
    if not os.path.isdir(self.software_root):
      error = "%s does not exist." % self.software_root
      raise OSError(error)
    if not os.path.isdir(self.instance_root):
      error = "%s does not exist." % self.instance_root
      raise OSError(error)
    # Creates everything needed
    try:
      # Creates instance_root structure
      createPrivateDirectory(self.instance_etc_directory)
      createPrivateDirectory(os.path.join(self.instance_root, 'var'))
      createPrivateDirectory(os.path.join(self.instance_root, 'var', 'log'))
      createPrivateDirectory(os.path.join(self.instance_root, 'var', 'run'))
      createPrivateDirectory(self.supervisord_configuration_directory)
      # Creates supervisord configuration
      updateFile(self.supervisord_configuration_path,
        pkg_resources.resource_stream(__name__,
          'templates/supervisord.conf.in').read() % dict(
            supervisord_configuration_directory=self.supervisord_configuration_directory,
            supervisord_socket=os.path.abspath(self.supervisord_socket),
            supervisord_loglevel='info',
            supervisord_logfile=os.path.abspath(os.path.join(
              self.instance_root, 'var', 'log', 'supervisord.log')),
            supervisord_logfile_maxbytes='50MB',
            supervisord_nodaemon='false',
            supervisord_pidfile=os.path.abspath(os.path.join(
              self.instance_root, 'var', 'run', 'supervisord.pid')),
            supervisord_logfile_backups='10',
          ))
    except (WrongPermissionError, PathDoesNotExistError) as error:
      raise error

  def getComputerPartitionList(self):
    try:
      computer_partition_list = self.computer.getComputerPartitionList()
    except socket.error as error:
      self.logger.fatal(error)
      raise
    return computer_partition_list

  def processSoftwareReleaseList(self):
    """Will process each Software Release.
    """
    self.checkEnvironmentAndCreateStructure()
    logger = logging.getLogger('SoftwareReleases')
    logger.info("Processing software releases...")
    clean_run = True
    for software_release in self.computer.getSoftwareReleaseList():
      try:
        software_release.building()
        software_release_uri = software_release.getURI()
        Software(url=software_release_uri, software_root=self.software_root,
            console=self.console, buildout=self.buildout,
            signature_private_key_file=self.signature_private_key_file,
            signature_certificate_list=self.signature_certificate_list,
            download_binary_cache_url=self.download_binary_cache_url,
            upload_binary_cache_url=self.upload_binary_cache_url,
            upload_cache_url=self.upload_cache_url,
            download_binary_dir_url=self.download_binary_dir_url,
            upload_binary_dir_url=self.upload_binary_dir_url,
            upload_dir_url=self.upload_dir_url,
            shacache_cert_file=self.shacache_cert_file,
            shacache_key_file=self.shacache_key_file,
            shadir_cert_file=self.shadir_cert_file,
            shadir_key_file=self.shadir_key_file).install()
      except (SystemExit, KeyboardInterrupt):
        exception = traceback.format_exc()
        software_release.error(exception)
        raise
      except Exception:
        exception = traceback.format_exc()
        logger.error(exception)
        software_release.error(exception)
        clean_run = False
      else:
        software_release.available()
    logger.info("Finished software releases...")
    return clean_run

  def _launchSupervisord(self):
    launchSupervisord(self.supervisord_socket,
        self.supervisord_configuration_path)

  def _checkPromises(self, computer_partition):
    self.logger.info("Checking promises...")
    instance_path = os.path.join(self.instance_root,
        computer_partition.getId())

    uid, gid = None, None
    stat_info = os.stat(instance_path)

    #stat sys call to get statistics informations
    uid = stat_info.st_uid
    gid = stat_info.st_gid

    promise_present = False
    # Get the list of promises
    promise_dir = os.path.join(instance_path, 'etc', 'promise')
    if os.path.exists(promise_dir) and os.path.isdir(promise_dir):
      cwd = instance_path
      promises_list = os.listdir(promise_dir)

      # Check whether every promise is kept
      for promise in promises_list:
        promise_present = True

        command = [os.path.join(promise_dir, promise)]

        promise = os.path.basename(command[0])
        self.logger.info("Checking promise %r.", promise)

        kw = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        process_handler = SlapPopen(command,
          preexec_fn=lambda: dropPrivileges(uid, gid),
          cwd=cwd,
          env={}, **kw)

        time.sleep(self.promise_timeout)


        if process_handler.poll() is None:
          process_handler.terminate()
          raise Slapgrid.PromiseError("The promise %r timed out" % promise)
        elif process_handler.poll() != 0:
          stderr = process_handler.communicate()[1]
          if stderr is None:
            stderr = 'No error output from %r.' % promise
          else:
            stderr = 'Promise %r:' % promise + stderr
          raise Slapgrid.PromiseError(stderr)

    if not promise_present:
      self.logger.info("No promise.")


  def processComputerPartitionList(self):
    """Will start supervisord and process each Computer Partition.
    """
    logger = logging.getLogger('ComputerPartitionProcessing')
    logger.info("Processing computer partitions...")
    # Prepares environment
    self.checkEnvironmentAndCreateStructure()
    self._launchSupervisord()
    # Process Computer Partitions
    clean_run = True
    for computer_partition in self.getComputerPartitionList():
      computer_partition_id = computer_partition.getId()
      try:
        software_url = computer_partition.getSoftwareRelease().getURI()
      except NotFoundError:
        software_url = None
      software_path = os.path.join(self.software_root,
            getSoftwareUrlHash(software_url))
      local_partition = Partition(
        software_path=software_path,
        instance_path=os.path.join(self.instance_root,
            computer_partition.getId()),
        supervisord_partition_configuration_path=os.path.join(
          self.supervisord_configuration_directory, '%s.conf' %
          computer_partition_id),
        supervisord_socket=self.supervisord_socket,
        computer_partition=computer_partition,
        computer_id=self.computer_id,
        partition_id=computer_partition_id,
        server_url=self.master_url,
        software_release_url=software_url,
        certificate_repository_path=self.certificate_repository_path,
        console=self.console, buildout=self.buildout)
      # There are no conditions to try to instanciate partition
      try:
        computer_partition_state = computer_partition.getState()
        if computer_partition_state == "started":
          local_partition.install()
          computer_partition.available()
          local_partition.start()
          self._checkPromises(computer_partition)
          computer_partition.started()
        elif computer_partition_state == "stopped":
          local_partition.install()
          computer_partition.available()
          local_partition.stop()
          computer_partition.stopped()
        elif computer_partition_state == "destroyed":
          # Stop, but safely
          try:
            local_partition.stop()
            try:
              computer_partition.stopped()
            except (SystemExit, KeyboardInterrupt):
              exception = traceback.format_exc()
              computer_partition.error(exception)
              raise
            except Exception:
              pass
          except (SystemExit, KeyboardInterrupt):
            exception = traceback.format_exc()
            computer_partition.error(exception)
            raise
          except Exception:
            clean_run = False
            exception = traceback.format_exc()
            logger.error(exception)
            computer_partition.error(exception)
        else:
          error_string = "Computer Partition %r has unsupported state: %s" % \
            (computer_partition_id, computer_partition_state)
          computer_partition.error(error_string)
          raise NotImplementedError(error_string)
      except (SystemExit, KeyboardInterrupt):
        exception = traceback.format_exc()
        computer_partition.error(exception)
        raise
      except Exception:
        clean_run = False
        exception = traceback.format_exc()
        logger.error(exception)
        computer_partition.error(exception)

    logger.info("Finished computer partitions...")
    return clean_run

  def validateXML(self, to_be_validated, xsd_model):
    """Validates a given xml file"""

    logger = logging.getLogger('XMLValidating')

    #We retrieve the xsd model
    xsd_model = StringIO.StringIO(xsd_model)
    xmlschema_doc = etree.parse(xsd_model)
    xmlschema = etree.XMLSchema(xmlschema_doc)

    string_to_validate = StringIO.StringIO(to_be_validated)

    try:
      document = etree.parse(string_to_validate)
    except (etree.XMLSyntaxError, etree.DocumentInvalid) as e:
      logger.info('Failed to parse this XML report :  %s\n%s' % \
        (to_be_validated, _formatXMLError(e)))
      logger.error(_formatXMLError(e))
      return False

    if xmlschema.validate(document):
      return True

    return False

  def asXML(self, computer_partition_usage_list):
    """Generates a XML report from computer partition usage list
    """
    xml_head = ""
    xml_movements = ""
    xml_foot = ""

    xml_head = "<?xml version='1.0' encoding='utf-8'?>" \
               "<journal>" \
               "<transaction type=\"Sale Packing List\">" \
               "<title>Resource consumptions</title>" \
               "<start_date></start_date>" \
               "<stop_date>%s</stop_date>" \
               "<reference>%s</reference>" \
               "<currency></currency>" \
               "<payment_mode></payment_mode>" \
               "<category></category>" \
               "<arrow type=\"Administration\">" \
               "<source></source>" \
               "<destination></destination>" \
               "</arrow>" \
               % (strftime("%Y-%m-%d at %H:%M:%S"), 
                  self.computer_id)

    for computer_partition_usage in computer_partition_usage_list:
      try:
        usage_string = StringIO.StringIO(computer_partition_usage.usage)
        root = etree.parse(usage_string)
      except UnicodeError:
        logger.info("Failed to read %s." % (computer_partition_usage.usage))
        logger.error(UnicodeError)
        raise "Failed to read %s." % (computer_partition_usage.usage)
      except (etree.XMLSyntaxError, etree.DocumentInvalid) as e:
        logger.info("Failed to parse %s." % (usage_string))
        logger.error(e)
        raise _formatXMLError(e)
      except Exception:
        raise "Failed to generate XML report."

      for movement in root.findall('movement'):
        xml_movements += "<movement>"
        for children in movement.getchildren():
          if children.tag == "reference":
            xml_movements += "<%s>%s</%s>" % (children.tag, computer_partition_usage.getId(), children.tag)
          else:
            xml_movements += "<%s>%s</%s>" % (children.tag, children.text, children.tag)
        xml_movements += "</movement>"  

    xml_foot = "</transaction>" \
               "</journal>"

    xml = xml_head + xml_movements + xml_foot
    return xml

  def agregateAndSendUsage(self):
    """Will agregate usage from each Computer Partition.
    """
    slap_computer_usage = self.slap.registerComputer(self.computer_id)
    computer_partition_usage_list = []
    logger = logging.getLogger('UsageReporting')
    logger.info("Aggregating and sending usage reports...")

    #We retrieve XSD models
    try:
      computer_consumption_model = \
        pkg_resources.resource_string(
          'slapos.slap',
          'doc/computer_consumption.xsd')
    except IOError:
      computer_consumption_model = \
        pkg_resources.resource_string(
          __name__, 
          '../../../../slapos/slap/doc/computer_consumption.xsd')

    try:
      partition_consumption_model = \
        pkg_resources.resource_string(
          'slapos.slap',
          'doc/partition_consumption.xsd')
    except IOError:
      partition_consumption_model = \
        pkg_resources.resource_string(
          __name__, 
          '../../../../slapos/slap/doc/partition_consumption.xsd')

    clean_run = True
    #We loop on the different computer partitions
    computer_partition_list = slap_computer_usage.getComputerPartitionList()
    for computer_partition in computer_partition_list:
      computer_partition_id = computer_partition.getId()

      #We want execute all the script in the report folder
      instance_path = os.path.join(self.instance_root,
          computer_partition.getId())
      report_path = os.path.join(instance_path, 'etc', 'report')
      if os.path.isdir(report_path):
        script_list_to_run = os.listdir(report_path)
      else:
        script_list_to_run = []

      #We now generate the pseudorandom name for the xml file
      # and we add it in the invocation_list
      f = tempfile.NamedTemporaryFile()
      name_xml = '%s.%s' % ('slapreport', os.path.basename(f.name))
      path_to_slapreport = os.path.join(instance_path, 'var', 'xml_report',
          name_xml)

      failed_script_list = []
      for script in script_list_to_run:

        invocation_list = []
        invocation_list.append(os.path.join(instance_path, 'etc', 'report',
          script))
        #We add the xml_file name in the invocation_list
        #f = tempfile.NamedTemporaryFile()
        #name_xml = '%s.%s' % ('slapreport', os.path.basename(f.name))
        #path_to_slapreport = os.path.join(instance_path, 'var', name_xml)

        invocation_list.append(path_to_slapreport)
        #Dropping privileges
        uid, gid = None, None
        stat_info = os.stat(instance_path)
        #stat sys call to get statistics informations
        uid = stat_info.st_uid
        gid = stat_info.st_gid
        kw = dict()
        if not self.console:
          kw.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        process_handler = SlapPopen(invocation_list,
          preexec_fn=lambda: dropPrivileges(uid, gid),
          cwd=os.path.join(instance_path, 'etc', 'report'),
          env=None, **kw)
        result = process_handler.communicate()[0]
        if self.console:
          result = 'Please consult messages above'
        if process_handler.returncode is None:
          process_handler.kill()
        if process_handler.returncode != 0:
          clean_run = False
          failed_script_list.append("Script %r failed with %s." % (script, result))
          logger.warning("Failed to run %r, the result was. \n%s" %
            (invocation_list, result))
        if len(failed_script_list):
          computer_partition.error('\n'.join(failed_script_list))

    #Now we loop through the different computer partitions to ggetId()et reports
    report_usage_issue_cp_list = []
    for computer_partition in computer_partition_list:
      filename_delete_list = []
      computer_partition_id = computer_partition.getId()
      instance_path = os.path.join(self.instance_root, computer_partition_id)
      dir_reports = os.path.join(instance_path, 'var', 'xml_report')
      #The directory xml_report contain a number of files equal
      #to the number of software instance running inside the same partition
      if os.path.isdir(dir_reports):
        filename_list = os.listdir(dir_reports)
      else:
        filename_list = []
      #logger.debug('name List %s' % filename_list)
      usage = ''

      for filename in filename_list:

        file_path = os.path.join(dir_reports, filename)
        if os.path.exists(file_path):
          usage_file = open(file_path, 'r')
          usage = usage_file.read()
          usage_file.close()

          #We check the validity of xml content of each reports
          if not self.validateXML(usage, partition_consumption_model):
            logger.info('WARNING: The XML file %s generated by slapreport is not valid - ' \
                            'This report is left as is at %s where you can inspect what went wrong ' % (filename, dir_reports))
            #Warn the SlapOS Master that a partition generates corrupted xml report
          else:
            computer_partition_usage = self.slap.registerComputerPartition(
                    self.computer_id, computer_partition_id)
            computer_partition_usage.setUsage(usage)
            computer_partition_usage_list.append(computer_partition_usage)
            filename_delete_list.append(filename)
        else:
          logger.debug("Usage report %r not found, ignored" % file_path)

        #last_push_date = self.computer.getLastUsagePush()
        #periodicity_timedelta = datetime.timedelta(
        #        self.usage_report_periodicity)
        #if periodicity_timedelta + last_push_date < datetime.datetime.today():
        # Pushes informations, if any

      #After sending the aggregated file we remove all the valid xml reports
      for filename in filename_delete_list:
        os.remove(os.path.join(dir_reports, filename))

    for computer_partition_usage in computer_partition_usage_list:
      logger.info('computer_partition_usage_list : %s - %s' % \
        (computer_partition_usage.usage, computer_partition_usage.getId()))

    #If there is, at least, one report
    if computer_partition_usage_list != []:
      try:
        #We generate the final XML report with asXML method
        computer_consumption = self.asXML(computer_partition_usage_list)

        logger.info('Final xml report : %s' % computer_consumption)

        #We test the XML report before sending it
        if self.validateXML(computer_consumption, computer_consumption_model):
          logger.info('XML file generated by asXML is valid')
          slap_computer_usage.reportUsage(computer_consumption)
        else:
          logger.info('XML file generated by asXML is not valid !')
          raise 'XML file generated by asXML is not valid !'
      except Exception:
        computer_partition_id = computer_partition.getId()
        exception = traceback.format_exc()
        issue = "Cannot report usage for %r: %s" % (computer_partition_id,
          exception)
        logger.info(issue)
        computer_partition.error(issue)
        report_usage_issue_cp_list.append(computer_partition_id)

    for computer_partition in computer_partition_list:
      computer_partition_id = computer_partition.getId()
      try:
        software_url = computer_partition.getSoftwareRelease().getURI()
      except NotFoundError:
        software_url = None
      software_path = os.path.join(self.software_root,
            getSoftwareUrlHash(software_url))
      local_partition = Partition(
        software_path=software_path,
        instance_path=os.path.join(self.instance_root,
            computer_partition.getId()),
        supervisord_partition_configuration_path=os.path.join(
          self.supervisord_configuration_directory, '%s.conf' %
          computer_partition_id),
        supervisord_socket=self.supervisord_socket,
        computer_partition=computer_partition,
        computer_id=self.computer_id,
        partition_id=computer_partition_id,
        server_url=self.master_url,
        software_release_url=software_url,
        certificate_repository_path=self.certificate_repository_path,
        console=self.console, buildout=self.buildout
        )
      if computer_partition.getState() == "destroyed":
        try:
          local_partition.stop()
          try:
            computer_partition.stopped()
          except (SystemExit, KeyboardInterrupt):
            exception = traceback.format_exc()
            computer_partition.error(exception)
            raise
          except Exception:
            pass
        except (SystemExit, KeyboardInterrupt):
          exception = traceback.format_exc()
          computer_partition.error(exception)
          raise
        except Exception:
          clean_run = False
          exception = traceback.format_exc()
          computer_partition.error(exception)
          logger.error(exception)
        if computer_partition.getId() in report_usage_issue_cp_list:
          logger.info('Ignoring destruction of %r, as not report usage was '
            'sent' % computer_partition.getId())
          continue
        local_partition.destroy()
        try:
          computer_partition.destroyed()
        except slap.NotFoundError:
          logger.debug('Ignored slap error while trying to inform about '
              'destroying not fully configured Computer Partition %r' %
                  computer_partition.getId())
        except ServerError as server_error:
          logger.debug('Ignored server error while trying to inform about '
              'destroying Computer Partition %r. Error is :\n%r' %
                  (computer_partition.getId(), server_error.args[0]))

    logger.info("Finished usage reports...")
    return clean_run
