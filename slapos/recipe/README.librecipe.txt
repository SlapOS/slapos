librecipe
=========

Thanks to using slapos.cookbook:librecipe it is easier to create zc.buildout recipes in SlapOS environment.

How to use?
-----------

In setup.py of recipe add only one install requires to slap.lib.recipe.

In code itself subclass from slap.lib.recipe.BaseSlapRecipe.BaseSlapRecipe.

Use _install hook:

::

  from slap.lib.recipe.BaseSlapRecipe import BaseSlapRecipe

  class Recipe(BaseSlapRecipe):
    ...
    def _install(self):
      # refer below for list of available objects
      specific code
      of recipe

Available variables self.:

 * name and options passed by zc.buildout during init
 * work_directory -- buildout's directory
 * bin_directory -- places for generated binaries
 * running_wrapper_location -- filename of wrapper to create
 * data_root_directory -- directory container for data -- inside this
   directory it is advised to create named directories for provided servers
   which needs data
 * backup_directory -- directory container for backups -- inside this
   directory it is advised o created named directories for backups, with same
   structure as in data_root_directory
 * var_directory -- container for various, unix following things:

   * log_directory -- container for logs
   * run_directory -- container for pidfiles and sockets

 * etc_directory -- place to put named files and directories of configuration
   for provided servers
 * computer_id -- id of computer
 * computer_partition_id -- if of computer partition
 * server_url - url of Vifib server
 * software_release_url -- url of software release being instantiated
 * slap -- initialised connection to Vifib server
 * computer_partition -- initialised connection to computer partition
 * request -- shortcut to computer partition request method

By default all directories are created before calling _install hook.

_install method shall return list of paths which are safe to be removed by
buildout during part uninstallation.

Important assumptions
---------------------

Because in SlapOS environment zc.buildout does not know when data are changed,
recipes shall be always uninstalled/installed. This is done during constructing
recipe instance which subclasses from BaseSlapRecipe.
