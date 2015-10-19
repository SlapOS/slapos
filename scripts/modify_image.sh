#! /bin/bash

# This script will modify all the images produced after running it for the given board,
# that is given as first parameter
BOARD=$1

./mount_gpt_image.sh -f $( ./get_latest_image.sh --board=${BOARD} )
sudo rm /tmp/m/etc/init/openssh-server.conf
sudo emerge-${BOARD} --root=/tmp/m --root-deps=rdeps --usepkgonly git babeld-re6stnet re6stnet
./mount_gpt_image.sh -f $( ./get_latest_image.sh --board=${BOARD} ) -u