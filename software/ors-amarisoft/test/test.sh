#!/bin/bash -ex

export SLAPOS_TEST_DEBUG=1
export SLAPOS_TEST_VERBOSE=0
export SLAPOS_TEST_SKIP_SOFTWARE_CHECK=1 
export SLAPOS_TEST_SKIP_SOFTWARE_REBUILD=1
time ../k/kpython_for_test -m unittest discover -v -k TestENBParameters
