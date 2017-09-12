# coding: utf-8
from zope.interface import Interface


class IManager(Interface):
  """Manager is called in every step of preparation of the computer."""

  def __init__(config):
    """Manager needs to know config for its functioning.

    :param conf: dictionary-like object with full access to [slapos] section of the config file
    """

  def format(computer):
    """Method called at `slapos node format` phase.

    :param computer: slapos.format.Computer, currently formatted computer
    """

  def software(software):
    """Method called at `slapos node software` phase.

    :param software: slapos.grid.SlapObject.Software, currently processed software
    """

  def instance(partition):
    """Method called at `slapos node instance` phase.

    :param partition: slapos.grid.SlapObject.Partition, currently processed partition
    """

  def report(partition):
    """Method called at `slapos node report` phase.

    :param partition: slapos.grid.SlapObject.Partition, currently processed partition
    """
