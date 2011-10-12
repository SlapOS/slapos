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
from zope.interface import Interface

"""
Note: all strings accepted/returned by the slap library are encoded in UTF-8.
"""
class IException(Interface):
  """
  Classes which implement IException are used to report errors.
  """

class INotFoundError(IException):
  """
  Classes which implement INotFoundError are used to report missing
  informations on the slap server.
  """

class IUnauthorized(IException):
  """
  Classes which implement IUnauthorized are used to report missing
  permissions on the slap server.
  """

class IRequester(Interface):
  """
  Classes which implement IRequester can request software instance to the
  slapgrid server.
  """

  def request(software_release, software_type, partition_reference, 
              shared=False, partition_parameter_kw=None, filter_kw=None):
    """
    Request software release instanciation to slapgrid server.

    Returns a new computer partition document, where this sofware release will
    be installed.

    software_release -- uri of the software release
                        which has to be instanciated

    software_type -- type of component provided by software_release

    partition_reference -- local reference of the instance used by the recipe
                           to identify the instances.

    shared -- boolean to use a shared service

    partition_parameter_kw -- dictionary of parameter used to fill the
                              parameter dict of newly created partition.

    filter_kw -- dictionary of filtering parameter to select the requested
                 computer partition.

      computer_guid - computer of the requested partition
      partition_type - virtio, slave, full, limited
      port - port provided by the requested partition

    Example:
       request('http://example.com/toto/titi', 'typeA', 'mysql_1')
    """

class IBuildoutController(Interface):
  """
  Classes which implement IBuildoutController can report the buildout run
  status to the slapgrid server.
  """

  def available():
    """
    Notify (to the slapgrid server) that the software instance is 
    available.
    """

  def building():
    """
    Notify (to the slapgrid server) that the buildout is not 
    available and under creation.
    """

  def error(error_log):
    """
    Notify (to the slapgrid server) that the buildout is not available
    and reports an error.

    error_log -- a text describing the error
                 It can be a traceback for example.
    """

class ISoftwareRelease(IBuildoutController):
  """
  Software release interface specification
  """

  def getURI():
    """
    Returns a string representing the uri of the software release.
    """

class IComputerPartition(IBuildoutController, IRequester):
  """
  Computer Partition interface specification

  Classes which implement IComputerPartition can propagate the computer
  partition state to the SLAPGRID server and request new computer partition
  creation.
  """

  def stopped():
    """
    Notify (to the slapgrid server) that the software instance is 
    available and stopped.
    """

  def started():
    """
    Notify (to the slapgrid server) that the software instance is 
    available and started.
    """

  def destroyed():
    """
    Notify (to the slapgrid server) that the software instance has
    been correctly destroyed.
    """

  def getId():
    """
    Returns a string representing the identifier of the computer partition
    inside the slapgrid server.
    """

  def getState():
    """
    Returns a string representing the expected state of the computer partition.

    The result can be: started, stopped, destroyed
    """

  def getSoftwareRelease():
    """
    Returns the software release associate to the computer partition.

    Raise an INotFoundError if no software release is associated.
    """

  def getInstanceParameterDict():
    """
    Returns a dictionary of instance parameters.

    The contained values can be used to fill the software instanciation
    profile.
    """

  def setUsage(usage_log):
    """
    Associate a usage log to the computer partition.
    This method does not report the usage to the slapgrid server. See
    IComputer.report.

    usage_log -- a text describing the computer partition usage.
                 It can be an XML for example.
    """

  def bang(log):
    """
    Report a problem detected on a computer partition.
    This will trigger the reinstanciation of all partitions in the instance tree.

    log -- a text explaining why the method was called
    """

class IComputer(Interface):
  """
  Computer interface specification

  Classes which implement IComputer can fetch informations from the slapgrid
  server to know which Software Releases and Software Instances have to be
  installed.
  """

  def getSoftwareReleaseList(): 
    """
    Returns the list of software release which has to be supplied by the
    computer.

    Raise an INotFoundError if computer_guid doesn't exist.
    """

  def getComputerPartitionList(): 
    """
    Returns the list of configured computer partitions associated to this
    computer.

    Raise an INotFoundError if computer_guid doesn't exist.
    """

  def reportUsage(computer_partition_list):
    """
    Report the computer usage to the slapgrid server. 
    IComputerPartition.setUsage has to be called on each computer partition to
    define each usage.

    computer_partition_list -- a list of computer partition for which the usage
                               needs to be reported.
    """

  def bang(log):
    """
    Report a problem detected on a computer.
    This will trigger IComputerPartition.bang on all instances hosted by the
    Computer.

    log -- a text explaining why the method was called
    """

class IOpenOrder(IRequester):
  """
  Open Order interface specification

  Classes which implement Open Order describe which kind of software instances
  is requested by a given client.
  """

class ISupply(Interface):
  """
  Supply interface specification

  Classes which implement Supply describe which kind of software releases
  a given client is ready to supply.
  """

  def supply(software_release, computer_guid=None):
    """
    Tell that given client is ready to supply given sofware release

    software_release -- uri of the software release
                        which has to be instanciated

    computer_guid -- the identifier of the computer inside the slapgrid 
                     server.
    """

class slap(Interface):
  """
  Initialise slap connection to the slapgrid server

  Slapgrid server URL is defined during the slap library installation, 
  as recipes should not use another server.
  """

  def initializeConnection(slapgrid_uri, authentification_key=None):
    """
    Initialize the connection parameters to the slapgrid servers.

    slapgrid_uri -- uri the slapgrid server connector

    authentification_key -- string the authentificate the agent.

    Example: https://slapos.server/slap_interface
    """

  def registerComputer(computer_guid):
    """
    Instanciate a computer in the slap library.

    computer_guid -- the identifier of the computer inside the slapgrid server.
    """

  def registerComputerPartition(computer_guid, partition_id):
    """
    Instanciate a computer partition in the slap library.

    computer_guid -- the identifier of the computer inside the slapgrid server.

    partition_id -- the identifier of the computer partition inside the 
                    slapgrid server.

    Raise an INotFoundError if computer_guid doesn't exist.
    """

  def registerSoftwareRelease(software_release):
    """
    Instanciate a software release in the slap library.

    software_release -- uri of the software release definition
    """

  def registerOpenOrder():
    """
    Instanciate an open order in the slap library.
    """
    
  def registerSupply():
    """   
    Instanciate a supply in the slap library.
    """
