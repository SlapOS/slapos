##############################################################################
#
# Copyright (c) 2010, 2011, 2012 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
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

class IConnectionError(IException):
  """
  Classes which implement IServerError are used to report a connection problem
  to the slap server.
  """

class IServerError(IException):
  """
  Classes which implement IServerError are used to report unexpected error
  from the slap server.
  """

class INotFoundError(IException):
  """
  Classes which implement INotFoundError are used to report missing
  informations on the slap server.
  """

class IResourceNotReady(IException):
  """
  Classes which implement IResourceNotReady are used to report resource not
  ready on the slap server.
  """

class IRequester(Interface):
  """
  Classes which implement IRequester can request software instance to the
  slapgrid server.
  """

  def request(software_release, software_type, partition_reference,
              shared=False, partition_parameter_kw=None, filter_kw=None):
    """
    Request software release instantiation to slapgrid server.

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

  def getInformation(partition_reference):
    """
    Get informations about an existing instance.
    If it is called from a Computer Partition, get informations
    about Software Instance of the instance tree.

    partition_reference -- local reference of the instance used by the recipe
                           to identify the instances.
    """

class ISoftwareRelease(Interface):
  """
  Software release interface specification
  """

  def getURI():
    """
    Returns a string representing the uri of the software release.
    """

  def getComputerId():
    """
    Returns a string representing the identifier of the computer where the SR
    is installed.
    """

  def getState():
    """
    Returns a string representing the expected state of the software
    installation.

    The result can be: available, destroyed
    """

  def available():
    """
    Notify (to the slapgrid server) that the software release is
    available.
    """

  def building():
    """
    Notify (to the slapgrid server) that the software release is not
    available and under creation.
    """

  def destroyed():
    """
    Notify (to the slapgrid server) that the software installation has
    been correctly destroyed.
    """

  def error(error_log):
    """
    Notify (to the slapgrid server) that the software installation is 
    not available and reports an error.

    error_log -- a text describing the error
                 It can be a traceback for example.
    """

class ISoftwareProductCollection(Interface):
  """
  Fake object representing the abstract of all Software Products.
  Can be used to call "Product().mysoftwareproduct", or, simpler,
  "product.mysoftwareproduct", to get the best Software Release URL of the
  Software Product "mysoftwareproduct".

  Example: product.kvm will have the value of the latest Software
  Release URL of KVM.
  """

class ISoftwareInstance(Interface):
  """
  Classes which implement ISoftwareRelease are used by slap to represent
  informations about a Software Instance.
  """

class IComputerPartition(IRequester):
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

  def error(error_log):
    """
    Notify (to the slapgrid server) that the software instance is 
    not available and reports an error.

    error_log -- a text describing the error
                 It can be a traceback for example.
    """


  def getId():
    """
    Returns a string representing the identifier of the computer partition
    inside the slapgrid server.
    """

  def getInstanceGuid():
    """
    Returns a string representing the unique identifier of the instance
    inside the slapgrid server.
    """

  def getState():
    """
    Returns a string representing the expected state of the computer partition.

    The result can be: started, stopped, destroyed
    """

  def getAccessStatus():
    """Get latest computer partition Access message state"""

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

  def getConnectionParameterDict():
    """
    Returns a dictionary of connection parameters.

    The contained values are connection parameters of a compute partition.
    """

  def getType():
    """
    Returns the Software Type of the instance.
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

  def getCertificate():
    """
    Returns a dictionnary containing the authentification certificates
    associated to the computer partition.
    The dictionnary keys are:
      key -- value is a SSL key
      certificate -- value is a SSL certificate

    Raise an INotFoundError if no software release is associated.
    """

  def setConnectionDict(connection_dict, slave_reference=None):
    """
    Store the connection parameters associated to a partition.

    connection_dict -- dictionary of parameter used to fill the
                              connection dict of the partition.

    slave_reference -- current reference of the slave instance to modify
    """

  def getInstanceParameter(key):
    """
    Returns the instance parameter associated to the key.

    Raise an INotFoundError if no key is defined.

    key -- a string name of the parameter
    """

  def getConnectionParameter(key):
    """
    Return the connection parameter associate to the key.

    Raise an INotFoundError if no key is defined.

    key -- a string name of the parameter
    """

  def rename(partition_reference, slave_reference=None):
    """
    Change the partition reference of a partition

    partition_reference -- new local reference of the instance used by the recipe
                           to identify the instances.

    slave_reference -- current reference of the slave instance to modify
    """

  def getStatus():
    """
    Returns a dictionnary containing the latest status of the
    computer partition.
    The dictionnary keys are:
      user -- user who reported the latest status
      created_at -- date of the status
      text -- message log of the status
    """

  def getFullHostingIpAddressList():
    """
    Returns a dictionnary containing the latest status of the
    computer partition.
    """

  def setComputerPartitionRelatedInstanceList(instance_reference_list):
    """
    Set relation between this Instance and all his children.

    instance_reference_list -- list of instances requested by this Computer
                               Partition.   
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

  def updateConfiguration(configuration_xml):
    """
    Report the current computer configuration.

    configuration_xml -- computer XML description generated by slapformat
    """

  def getStatus():
    """
    Returns a dictionnary containing the latest status of the
    computer.
    The dictionnary keys are:
      user -- user who reported the latest status
      created_at -- date of the status
      text -- message log of the status
    """

  def generateCertificate():
    """
    Returns a dictionnary containing the new certificate files for
    the computer.
    The dictionnary keys are:
      key -- key file
      certificate -- certificate file

    Raise ValueError is another certificate is already valid.
    """

  def revokeCertificate():
    """
    Revoke current computer certificate.

    Raise ValueError is there is not valid certificate.
    """

class IOpenOrder(IRequester):
  """
  Open Order interface specification

  Classes which implement Open Order describe which kind of software instances
  is requested by a given client.
  """

  def requestComputer(computer_reference):
    """
    Request a computer to slapgrid server.

    Returns a new computer document.

    computer_reference -- local reference of the computer
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

  def getSoftwareReleaseListFromSoftwareProduct(software_product_reference, software_release_url):
    """
    Get the list of Software Releases from a product or from another related
    Sofware Release, from a Software Product point of view.
    """

  def getOpenOrderDict():
    """
    Get the list of existing open orders (services) for the current user.
    """
