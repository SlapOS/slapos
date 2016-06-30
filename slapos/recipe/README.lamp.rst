lamp
=====

The lamp recipe helps you to deploy simply a php based application on slapos. This recipe is 
able to setup mariadb, apache and apache-php for your php application, and is also capable of
configuring your software during installation to ensure a full compatibility.


How to use?
-----------

just add this part in your software.cfg to use the lamp.simple module

.. code-block::

  [instance-recipe]
  egg = slapos.cookbook
  module = lamp.simple

you also need to extend lamp.cfg

.. code-block::

  extends =
    https://lab.nexedi.com/nexedi/slapos/raw/slapos-0.50/stack/lamp.cfg


lamp.runner
===========

When you install some software (such as prestashop) you need to remove or rename folder, with slapos you can not 
access to the www-data directory. to do this, you need to tell to lamp recipe to remove or/and it when software 
will be instantiated. Some software requires more than rename or delete a folder (manualy create database etc...)
in this case you need to write a python script and lamp recipe must run it when installing your software.



How to use?
-----------

this part of lamp recipe work with slapos.toolbox, Therefore you must add it to your recipe.
in software.cfg, replace instance-recipe-egg part by

.. code-block::

  [instance-recipe-egg]
  recipe = zc.recipe.egg
  eggs =
      ${python-mysqlclient:egg}
      ${instance-recipe:egg}
      slapos.toolbox[lampconfigure]

and add into your instance.cfg

.. code-block::

  lampconfigure_directory = ${buildout:bin-directory}/lampconfigure


CONDITION
----------

the action (delete, rename, script, chmod) only starts when the condition is filled.
in instance.cfg, add:: 

  file_token = path_of_file

and the action will begin when path_of_www-data/path_of_file will be created
you can also use database to check condition. add ::

  table_name = name_of_table
  constraint = sql_where_condition

name_of_table is the full or partial name(in some cases we can not know the prefix used to create tables) of table
into mariadb databse for example table_name = admin. if you use
name_of_table = **, the action will begin when database is ready. 
constraint is the sql_condition to use when search entry into name_of_table for example constraint = `admin_id`=1

you can't use file_token and table_name at the same time, otherwise file_token will be used in priority. Beware of conditions that will never be satisfied.



ACTION
-------

The action starts when condition is true

1- delete file or folder into instance.cfg, use:: 

  delete = file_or_folder1, file_or_folder2, file_or_folder3 ...

for example delete = admin 

2- rename file or folder
into instance.cfg, use 

rename_chmod = mode (optional)
rename = old_name1 => new_name1, old_name2 => new_name2, ... 

you can also use
rename = old_name1, old_name2 => new_name2, ... in this case old_name1 will be rename and the new name will be chose
by joining old_name1 and mysql_user: this should give 
rename = old_name1 => old_name1-mysql_user, old_name2 => new_name2, ...
use rename_chmod to apply a mode to new_name1, new_name2, ...

3- Change mode of file or directory

this is usefull if you want to change the mode of files into your www-data, use 

chmod = file1, file2, ....
mode = mode_to_apply (ex= 0644)

4- Launch python script

use script = ${configure-script:location}/${configure-script:filename} into instance.cfg, add part configure-script
into software.cfg

.. code-block::

  parts = configure-script

  [configure-script]
  recipe = hexagonit.recipe.download
  location = ${buildout:parts-directory}/${:_buildout_section_name_}
  url = url_of_script_name.py
  filename = script_name.py
  download-only = True

The script_name.py should contain a main function, sys.argv is given to the main. you can write script_name.py like this::

    ...
    def setup(args):
      mysql_port, mysql_host, mysql_user, mysql_password, mysql_database, base_url, htdocs = args
      .......

    if __name__ == '__main__':
        setup(sys.argv[1:])


- base_url: is the url of php software
- htdocs: is the path of www-data directory
- mysql_user, mysql_password, mysql_database, mysql_host: is the mariadb parameters

you can also use "import MySQLdb" if you want to access to database via your python script