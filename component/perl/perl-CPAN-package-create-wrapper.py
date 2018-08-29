import os
import textwrap
import glob

def post_make_hook(options, buildout, environmet):
  prefix = options['prefix']
  site_perl = options['site_perl']
  perl_location = options['perl_location']
  bin_folder = os.path.join(prefix, 'bin')
  if not os.path.isdir(bin_folder):
      os.mkdir(bin_folder)

  # install a ./bin/perl wrapper with @INC set
  perl_wrapper_path = os.path.join(bin_folder, 'perl')
  with open(perl_wrapper_path, 'w') as wrapper:
      wrapper.write('''#!/bin/sh
export PERL5LIB="{site_perl}:$PERL5LIB"
exec {perl_location}/bin/perl "$@"
'''.format(**locals()))
  os.chmod(perl_wrapper_path, 0755)

  # create a wrapper for each scripts installed in perl-bin
  for script_path in glob.glob(os.path.join(prefix, 'perl-bin', '*')):
      script_name = os.path.basename(script_path)
      wrapper_path = os.path.join(prefix, 'bin', script_name)
      with open(wrapper_path, 'w') as wrapper:
          wrapper.write('''#!/bin/sh
export PERL5LIB="{site_perl}:$PERL5LIB"
exec {perl_location}/bin/perl {script_path} "$@"
'''.format(**locals()))
      os.chmod(wrapper_path, 0755)
