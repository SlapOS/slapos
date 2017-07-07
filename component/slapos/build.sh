#!/bin/bash
#
# This simple script to buildout slapos from source using 1.0 branch on 
# /opt/slapos folder, adapt this script as you please.  
#
# Be carefull to not run this script were the script is already installed.

# Use sudo or superuser and create slapos directory (you can pick a different directory)
mkdir -p /opt/slapos/log/
cd /opt/slapos/

# Create buildout.cfg SlapOS bootstrap file
echo "[buildout]
extends = https://lab.nexedi.com/nexedi/slapos/raw/1.0/component/slapos/buildout.cfg
" &gt; buildout.cfg

# Required in some distros such as Mandriva
unset</span> PYTHONPATH
unset</span> PYTHONDONTWRITEBYTECODE
unset</span> CONFIG_SITE

#
# Bootstrap SlapOS, using forked version of buildout.
#
wget https://bootstrap.pypa.io/bootstrap-buildout.py
python -S --builout-version python -S bootstrap-buildout.py --buildout-version 2.5.2+slapos009 -f http://www.nexedi.org/static/packages/source/slapos.buildout/

#
# Warning:Depending on your distribution you might need to
# replace python by python2 in the last command. This happens when your
# distribution considers that the standard python is the 3.x branch.
#
# Finally start to build

bin/buildout -v
