import os
import textwrap
import glob


def post_make_hook(options, buildout, environment):
  prefix = options['prefix']
  dict_dir = options['dict-dir']
  aspell_bin = os.path.join(
      buildout['aspell']['location'],
      'bin',
      'aspell')

  aspell_bin_wrapper = options['bin-aspell']

  bin_folder = os.path.dirname(aspell_bin_wrapper)
  if not os.path.isdir(bin_folder):
    os.mkdir(bin_folder)

  # install a ./bin/aspell set to use the dict from this part
  with open(aspell_bin_wrapper, 'w') as wrapper:
    wrapper.write('''#!/bin/sh
export ASPELL_CONF="dict-dir {dict_dir}"
exec {aspell_bin} "$@"
'''.format(**locals()))
  os.chmod(aspell_bin_wrapper, 0o755)
