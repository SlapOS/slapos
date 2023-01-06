Virtual environment
===================

Introduction
------------

The virtual environment macro allows you to quickly create a development environment.

Options
-------

Several options are available to customize your virtual environment :

name
~~~~

The ``name`` option is the name that will be displayed when the environment is activated. For example::

  name = virtual-env

gives::

  >> source activate
  ( virtual-env ) >>

**Note:** By default, ``name`` is the name of the Buildout section that uses the macro.

location
~~~~~~~~

The ``location`` option is where the script to be sourced will be stored. For example::

  location = project/activate

gives::

  >> source project/activate
  ( virtual-env ) >>
  
**Note:** Don't forget to add the name of the script in the path.

eggs
~~~~

This option should not be used to install eggs during instantiation (in an instance file).

It works the same way as ``zc.recipe.eggs``, you can add to the line several eggs to download for use in the virtual environment.

A custom Python with the chosen eggs will then be generated. For example::

  eggs = numpy

gives::

  ( virtual-env ) >> python
  python
  >>> import numpy

scripts
~~~~~~~

This option should not be used to install scripts during instantiation (in an instance file).

It works in the same way as in ``zc.recipe.eggs``, you can add to the line several scripts to generate for use in the virtual environment.For example::

  eggs = Django
  scripts = django-admin

gives::

  ( virtual-env ) >> django-admin

**Note:** By default if the option is not used, all scripts will be installed.

default-instance
~~~~~~~~~~~~~~~~

The ``default-instance`` option takes the value ``true`` or ``false``.

If set to ``true``, it will create a minimal instance that will publish the path of the script to be sourced.

If it is set to ``false``, you will be able to create your own custom instance.

**Note:** If you want to use the macro in an ``instance`` file, you should set this option to ``false``.

environment
~~~~~~~~~~~

The ``environment`` option allows you to choose the value of the environment variables of the virtual environment.

They are to be written on the line in the form ``VAR = value``. For example::

  environment = 
    VAR1 = value1
    VAR2 = value2

gives::

  ( virtual-env ) >> echo $VAR1
  value1

**Note:** If you want to keep the other values as well, like for PATH for example, you have to do::

  PATH = new_val:$PATH

message
~~~~~~~

The ``message`` option allows to display a message when sourcing the virtual environment.

The message will be considered as a string. For example::

  message =
    You are in a virtual environment.

gives::

  >> source activate
  You are in a virtual environment.

  ( virtual-env) >> 

chain
~~~~~

The ``chain`` option allows you to chain several scripts created by the macro as if it were one. This can be useful if one script is generated in a ``software`` file and another in an ``instance`` file.

When deactivating, the state of the environment will return to the initial state.

To use this option you just have to specify the script to source by running the script. For example::

  chain = project/another_activate

Deactivate
----------

Once you want to exit the virtual environment, you just have to run the ``deactivate`` function. Like::

  ( virtual-env ) >> deactivate
    >> 
