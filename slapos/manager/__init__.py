# coding: utf-8
import importlib 
import re
import six

from zope.interface import declarations

config_option = "manager_list"


def load_manager(name):
    """Load a manager from local files if it exists."""
    if re.match(r'[a-zA-Z_]', name) is None:
      raise ValueError("Manager name \"{!s}\" is not allowed! Must contain only letters and \"_\"".
        format(name))
    manager_module_name = "slapos.manager.{}".format(name)

    from slapos.manager import interface
    manager_module = importlib.import_module(manager_module_name)
    if not hasattr(manager_module, "Manager"):
      raise AttributeError("Manager class in {} has to be called \"Manager\"".format(
        manager_module_name))
    if not interface.IManager.implementedBy(manager_module.Manager):
      raise RuntimeError("Manager class in {} must zope.interface.implements \"IManager\"".format(
        manager_module_name))

    return manager_module.Manager


def from_config(config):
    """Return list of instances of managers allowed from the config."""
    if config is None:
      return []

    name_list = config.get(config_option, "")
    if isinstance(name_list, six.string_types):
      name_list = name_list.replace(",", " ").split()

    return [load_manager(name)(config) for name in name_list]