import pathlib
import sys

def pre_make_hook(options, buildout, environ):
  makefile = pathlib.Path('mozilla/Makefile')
  txt = makefile.read_text().replace('SLAPOS_BUILDOUT_PYTHON', sys.executable)
  makefile.write_text(txt)
