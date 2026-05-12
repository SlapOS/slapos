#!/bin/sh
export PATH=/opt/slapgrid/cfaa2217e0f9ea9ef9e05b634f6dbecb/bin:/usr/bin:/bin:$PATH
export SLAPOS_CONFIGURATION=/srv/slapgrid/slappart76/srv/runner/etc/slapos.cfg
export SLAPOS_CLIENT_CONFIGURATION=$SLAPOS_CONFIGURATION
SR=/srv/slapgrid/slappart76/srv/project/erp5-mcp/software/openwebui/software.cfg
kill $(cat /srv/slapgrid/slappart76/srv/runner/var/run/slapos-node-software.pid 2>/dev/null) 2>/dev/null
MAKEFLAGS=-j20 slapos node software --only $SR
