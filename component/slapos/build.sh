#!/bin/sh -ex
#
# This simple script to buildout slapos from source using 1.0 branch on
# /opt/slapos folder, adapt this script as you please.
#
# Be carefull to not run this script where slapos-node is already installed.
#
# Before run this script, ensure dependencies are installed, on debian, you can
# use the command bellow:
#
# apt-get install python3 gcc g++ make patch wget curl
#

# Use sudo or superuser and create slapos directory (you can pick a different directory)
mkdir -p /opt/slapos
cd /opt/slapos/
mkdir -p eggs log download-cache/dist

# Required in some distros such as Mandriva
unset PYTHONPATH
unset PYTHONDONTWRITEBYTECODE
unset CONFIG_SITE

#
# Bootstrap buildout.
#
cat > buildout.cfg <<EOF
[buildout]
extensions =
download-cache = download-cache
parts =
  zc.buildout

# Add location for modified non-official slapos.buildout
find-links +=
  http://www.nexedi.org/static/packages/source/
  http://www.nexedi.org/static/packages/source/slapos.buildout/

[zc.buildout]
recipe = zc.recipe.egg
eggs =
  zc.buildout

[versions]
setuptools = 44.1.1
zc.buildout = 2.7.1+slapos020
zc.recipe.egg = 2.0.3+slapos003
EOF

rm -f bootstrap.py
wget https://lab.nexedi.com/nexedi/slapos.buildout/raw/master/bootstrap/bootstrap.py
python3 -S bootstrap.py \
  --setuptools-version 40.8.0 \
  --setuptools-to-dir eggs
sed -i '1s/$/ -S/' bin/buildout
bin/buildout buildout:newest=true -v

# Install slapos.libnetworkcache (outside of system libraries, see python -S)
cat > buildout.cfg <<EOF
[buildout]
extends = https://lab.nexedi.com/nexedi/slapos/raw/1.0/component/slapos/buildout.cfg
download-cache = download-cache
parts =
  networkcached

[networkcached]
recipe = zc.recipe.egg
eggs =
  slapos.libnetworkcache
  zc.buildout
EOF
sed -i '1s/$/ -S/' bin/buildout
bin/buildout buildout:newest=true -v

#
# Finally start the big build
#
echo "[buildout]
extends = https://lab.nexedi.com/nexedi/slapos/raw/1.0/component/slapos/buildout.cfg
download-cache = download-cache
" > buildout.cfg
bin/buildout buildout:newest=true -v
