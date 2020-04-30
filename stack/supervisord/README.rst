Supervisord process manager

How to use
==========

Supervisord stack provides a library which can he called in your instance slapos. This stack can be used to run sub services in a partition.

To use:

 * extend ``stack/supervisord/buildout.cfg`` in your software.cfg file.
 * provide ``supervisord-library:target`` and ``supervisord-conf:target`` to your instance template which require to use supervisord controller.
 * add ``{% import "supervisord_lib" as supervisord_lib with context %}`` to instance template which call supervisord library. See example bellow:

**software.cfg**
::

  [template-instance]
  recipe = slapos.recipe.template:jinja2
  context =
      key buildout_bin_directory buildout:bin-directory
      key supervisord        supervisord-library:target
      key supervisord_conf   supervisord-conf:target

**instance.cfg.in**
::

    [template-custom-instance.cfg]
    recipe  = slapos.recipe.template:jinja2
    supervisord-lib = {{ supervisord }}
    import-list =
      file supervisord :supervisord-lib
    context =
        raw buildout_bin_directory  {{ buildout_bin_directory }}
        raw supervisord_conf        {{ supervisord_conf }}


**custom-instance.cfg**
::

  {% import "supervisord" as supervisord with context %}
  {{ supervisord.supervisord("custom-controller", buildout_bin_directory, supervisord_conf, use_service_hash=False) }}

  # add program to service controller
  {% set program_dict = {"name": "mariadb", "command": "${mariadb-service:wrapper}",
    "stopwaitsecs": 300, "environment": []} %}

  {{ supervisord.supervisord_program("custom-controller", "mariadb", program_dict) }}

  ...
  
  [buildout]
  
  parts = 
    ...
    custom-controller-service
    custom-controller-mariadb

