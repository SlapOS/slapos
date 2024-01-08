#!/bin/bash -ex

(cd .. && /usr/bin/python3 ../../update-hash)

export SLAPOS_TEST_DEBUG=1
export SLAPOS_TEST_VERBOSE=1
export SLAPOS_TEST_SKIP_SOFTWARE_CHECK=1 
export SLAPOS_TEST_SKIP_SOFTWARE_REBUILD=0

rm -rf snapshot
mkdir snapshot
export SLAPOS_TEST_LOG_DIRECTORY=`pwd`/snapshot

#time ../k/kpython_for_test -m unittest discover -vf -k TestENBParameters
#time ../k/kpython_for_test -m unittest discover -vf -k NBParameters
#time ../k/kpython_for_test -m unittest discover -vf -k CoreNetwork
#time ../k/kpython_for_test -m unittest discover -vf -k MonitorGadget
#time ../k/kpython_for_test -m unittest discover -vf -k SimCard
#time ../k/kpython_for_test -m unittest discover -vf
#time ../k/kpython_for_test -m unittest discover -vf -k TestENB_CPRI
time ../k/kpython_for_test -m unittest discover -vf -k TestENB_SDR
#time ../k/kpython_for_test -m unittest discover -vf -k TestENB_Lopcomm
