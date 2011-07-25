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
from utils import dropPrivileges
from utils import SlapPopen
from svcbackend import launchSupervisord
import tempfile
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
  parser.add_argument("--master_ca_file", help="Root certificate of SlapOS "
      "master key.")
  parser.add_argument("--certificate_repository_path",
      help="Path to directory where downloaded certificates would be stored.")
  parser.add_argument("-c", "--console", action="store_true", default=False,
      help="Enables console output and live output from subcommands.")
  parser.add_argument("-v", "--verbose", action="store_true", default=False,
      help="Be verbose.")
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

  for f in [key_file, cert_file, master_ca_file]:
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
            console=option_dict['console'],
            buildout=option_dict.get('buildout')),
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
               master_ca_file=None,
               certificate_repository_path=None,
               console=False):
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
      sys.exit(1)
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
            console=self.console, buildout=self.buildout).install()
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

  def validateXML(self, to_be_validated):
    """Will validate the xml file"""

    #We get the xsd model
    fed = open('choose_the_path', 'r')
    model = StringIO.StringIO(fed.read())
    xmlschema_doc = etree.parse(model)
    xmlschema = etree.XMLSchema(xmlschema_doc)

    string_to_validate = StringIO.StringIO(to_be_validated)
    document = etree.parse(string_to_validate)
    if xmlschema.validate(document):
      return True

    return False

  def agregateAndSendUsage(self):
    """Will agregate usage from each Computer Partition.
    """
    slap_computer_usage = self.slap.registerComputer(self.computer_id)
    computer_partition_usage_list = []
    logger = logging.getLogger('UsageReporting')
    logger.info("Aggregating and sending usage reports...")

    clean_run = True
    #We loop on the different computer partitions
    for computer_partition in slap_computer_usage.getComputerPartitionList():
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

      #
      # Checking if the promises are kept
      #
      # XXX-Antoine: I thought about factorizing this code with
      # the above one. But it seemed like a lot to get through.

      # Get the list of promises
      promise_dir = os.join(instance_path, 'etc', 'promise')
      promises_list = os.listdir(promise_dir)

      # Check whether every promise is kept
      for promise in promises_list:
        command_line = [promise]

        uid, gid = None, None
        stat_info = os.stat(instance_path)

        kw = dict()
        if not self.console:
          kw.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        process_handler = SlapPopen(invocation_list,
          preexec_fn=lambda: dropPrivileges(uid, gid),
          cwd=instance_path,
          env=None, **kw)

        time.sleep(3) # 3 seconds timeout

        if process_handler.returncode is None:
          process_handler.kill()
          computer_partition.error("The promise '%s' timed out" % promise)
        elif process_handler.returncode != 0:
          stderr = process_handler.communicate()[1]
          if stderr is None:
            stderr = 'No error output from %s.' % promise
          computer_partition.error(stderr)


    #Now we loop through the different computer partitions to ggetId()et reports
    report_usage_issue_cp_list = []
    for computer_partition in slap_computer_usage.getComputerPartitionList():
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
          usage += usage_file.read()
          usage_file.close()

          computer_partition_usage = self.slap.registerComputerPartition(
                  self.computer_id, computer_partition_id)
          computer_partition_usage.setUsage(usage)
          computer_partition_usage_list.append(computer_partition_usage)
        else:
          logger.debug("Usage report %r not found, ignored" % file_path)

      #-XXX-Here we'll have a "validate_xml" function
      #if not self.validateXML(usage):
      ##  logger.debug("WARNING: The file xml %s is not valid " %
      #       os.path.join(dir_reports, filename))
      if filename_list:
        logger.debug("Sending usage informations and terminating for "
            "partition %s..." % os.path.basename(instance_path))
        #logger.debug('file %s' % usage)
      else:
        logger.debug("No usage file created for partition %s..." \
                      % os.path.basename(instance_path))

        #last_push_date = self.computer.getLastUsagePush()
        #periodicity_timedelta = datetime.timedelta(
        #        self.usage_report_periodicity)
        #if periodicity_timedelta + last_push_date < datetime.datetime.today():
        # Pushes informations, if any

      try:
        slap_computer_usage.reportUsage(computer_partition_usage_list)
      except Exception:
        computer_partition_id = computer_partition.getId()
        exception = traceback.format_exc()
        issue = "Cannot report usage for %r: %s" % (computer_partition_id,
          exception)
        logger.info(issue)
        computer_partition.error(issue)
        report_usage_issue_cp_list.append(computer_partition_id)

      #After sending the aggregated file we remove everything in the folder
      for filename in filename_list:
        os.remove(os.path.join(dir_reports, filename))

    for computer_partition in slap_computer_usage.getComputerPartitionList():
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

    logger.info("Finished usage reports...")
    return clean_run
