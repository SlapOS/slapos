import os
import pkg_resources
from slapos.recipe.librecipe import BaseSlapRecipe

class SipTesterRecipe(BaseSlapRecipe):
  def __init__(self, buildout, name, options):
    BaseSlapRecipe.__init__(self, buildout, name, options)
    self.pjsua_configuration_file = os.path.join(self.etc_directory,
                                                 'pjsua.conf')

  def _createPJSUAConfiguration(self, template_name):
    pjsua_input = pkg_resources.resource_string(__name__, os.path.join(
                                                  'template', template_name))
    if self._writeFile(self.pjsua_configuration_file, 
                       pjsua_input % self.options):
      # XXX: How to inform slap/slapgrid that something changed and it might
      #      be not bad idea to restart CP?
      pass
    return self.pjsua_configuration_file

  def _install(self):
    path = self._createPJSUAConfiguration(self.config_template)

    d = {}
    d.update(self.options)
    d['pjsua_configuration_file'] = self.pjsua_configuration_file
    # XXX Hardcoded path
    d['pjsua_binary'] = os.path.join(self.buildout['software_definition'
          ]['software_home'].strip(), 'parts', 'pjproject-1.7', 'bin', 'pjsua')
    d['siptester_binary'] = os.path.join(self.buildout['software_definition'
          ]['software_home'].strip(), 'bin', 'siptester')
    self.running_wrapper_location = pkg_resources.resource_filename(__name__, os.path.join(
                                                  'template', 
                                                  self.wrapper_template))
    self._createRunningWrapper(d)
    return [path, wrapper_path]

  update = install

class ReceiverRecipe(SipTesterRecipe):
  config_template = "pjsua_receiver.conf.in"
  wrapper_template = "init_receiver.in"

class CallerRecipe(SipTesterRecipe):
  config_template = "pjsua_caller.conf.in"
  wrapper_template = "init_caller.in"

  def _install(self):
    # First of all, ask for a sipreceiver
    self.request(self.software_release_url, 'sipreceiver')
    return SipTesterRecipe._install(self)
