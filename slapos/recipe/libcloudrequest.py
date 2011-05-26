from slapos.recipe.librecipe import BaseSlapRecipe
import zc.buildout
class Recipe(BaseSlapRecipe):
  def _install(self):
    amazon = self.request(
        'https://svn.erp5.org/repos/public/slapos/trunk/software_release/libcloud/software.cfg',
        'Amazon EC Image',
        'Amazon EC Connector Partition',
        True)
    amazon_dict = amazon.getConnectionDict()
    if amazon_dict == {}:
      raise zc.buildout.UserError('Slave not installed yet')
    self.computer_partition.setConnectionDict(amazon.getConnectionDict())
    return []
