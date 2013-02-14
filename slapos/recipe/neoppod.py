from slapos.recipe.librecipe import GenericBaseRecipe

class NeoBaseRecipe(GenericBaseRecipe):

  _binding_port_mandatory = True

  def install(self):
    options = self.options
    if not options['masters']:
      # All parameters are always provided.
      # This parameter needs special care, because it is initially generated
      # empty, until all requested master nodes get their partitions
      # allocated.
      # Only then can this recipe start succeeding and actually doing anything
      # useful, as per NEO deploying constraints.
      raise Exception('"masters" parameter is mandatory')
    option_list = [
      options['binary'],
      '-l', options['logfile'],
      '-m', options['masters'],
      '-b', self._getBindingAddress(),
      # TODO: reuse partition reference for better log readability.
      #'-n', options['name'],
      '-c', options['cluster'],
    ]
    if options['verbose']:
      option_list.append('-v')
    option_list.extend(self._getOptionList())
    return [self.createPythonScript(
      options['wrapper'],
      'slapos.recipe.librecipe.execute.execute',
      option_list
    )]

  def _getBindingAddress(self):
    options = self.options
    bind = options['ip']
    if 'port' in options:
      # Some node types support port auto-allocation when no binding port is
      # requested.
      bind = bind + ':' + options['port']
    elif self._binding_port_mandatory:
      raise ValueError('"port" option is mandatory.')
    return bind

  def _getOptionList(self):
    raise NotImplementedError

class Storage(NeoBaseRecipe):

  _binding_port_mandatory = False

  def _getOptionList(self):
    return [
      '-d', self.options['database-parameters'],
      '-a', self.options['database-adapter'],
      '-w', self.options['wait-database'],
    ]

class Admin(NeoBaseRecipe):
  def _getOptionList(self):
    return []

class Master(NeoBaseRecipe):
  def _getOptionList(self):
    options = self.options
    return [
      '-p', options['partitions'],
      '-r', options['replicas'],
    ]
