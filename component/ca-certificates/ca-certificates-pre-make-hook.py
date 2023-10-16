import sys

# Because ca-certificate is used very early in the bootstrap process,
# even before python is built, we can not use the software release python
# yet, because it would loop forever in slapos.rebootstrap.
# By using sys.executable in a hook like this, we can use python without
# buildout recording a dependency to python in the part options.
def pre_make_hook(options, buildout, environ):
  with open('mozilla/Makefile') as f:
    makefile = f.read()
  makefile.replace('python3 certdata2pem.py', '%s certdata2pem.py' % sys.executable)
  with open('mozilla/Makefile', 'w') as f:
    f.write(makefile)
