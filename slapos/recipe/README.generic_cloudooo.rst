generic_cloudooo
================

The generic_cloudooo recipe helps you to deploy cloudooo services with their configuration files.


How to use?
-----------

Here is an example of a section to add in your software.cfg :

.. code-block::

  [cloudooo-configuration]
  recipe = slapos.cookbook:generic_cloudooo
  configuration-file = ${directory:etc}/cloudooo.cfg
  wrapper = ${directory:services}/cloudooo
  data-directory = ${directory:srv}/cloudooo
  ip = 0.0.0.0
  port = 1234
  ooo-paster = ${directory:bin}/cloudooo_paster
  mimetype_entry_addition =
    text/html application/pdf wkhtmltopdf
  openoffice-port = 1235
  ooo-binary-path = ${directory:libreoffice-bin}/program
  environment =
    FONTCONFIG_FILE = ${fontconfig-instance:conf-path}
    PATH = ${binary-link:target-directory}
  ooo-uno-path = ${directory:libreoffice-bin}/basis-link/program


Where :

- `configuration-file` is the path where the put the configuration file;
- `wrapper` is the path where the put the final executable file;
- `data-directory` is the folder where cloudooo would put it's temporary files;
- `ip` and `port` is where cloudooo will listen to;
- `ooo-paster` is the path of the program that will load cloudooo configuration
  and start the application;
- `mimetype_entry_addition` is additional entries to give to the default
  mimetype registry. (see section below.) The mimetype entry list is sorted in
  order to make the global mimetype at the bottom of the list.
  (i.e. `* * ooo` > `text/* * ooo`)

    .. code-block::

        mimetype_entry_addition =
          <input_format> <output_format> <handler>

- `openoffice-port` is the port where the internal OpenOffice.org service will
  listen to;
- `ooo-binary-path` is the path of the openoffice service executable file;
- `environment` are environment vars to use with the openoffice binary;
- `ooo-uno-path` is the path where UNO library is installed.


Default mimetype registry
-------------------------

.. code-block::

  application/vnd.oasis.opendocument* * ooo
  application/vnd.sun.xml* * ooo
  application/pdf text/* pdf
  application/pdf * ooo
  video/* * ffmpeg
  audio/* * ffmpeg
  application/x-shockwave-flash * ffmpeg
  application/ogg * ffmpeg
  application/ogv * ffmpeg
  image/png image/jpeg imagemagick
  image/png * ooo
  image/* image/* imagemagick
  text/* * ooo
  application/zip * ooo
  application/msword * ooo
  application/vnd* * ooo
  application/x-vnd* * ooo
  application/postscript * ooo
  application/wmf * ooo
  application/csv * ooo
  application/x-openoffice-gdimetafile * ooo
  application/x-emf * ooo
  application/emf * ooo
  application/octet* * ooo
  * application/vnd.oasis.opendocument* ooo
