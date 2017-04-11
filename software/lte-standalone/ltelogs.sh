#!/bin/bash
# Copyright (C) 2012-2015 Amarisoft
# LTE system logger version 2016-10-13

# Path for multi environment support
export PATH="$PATH:/bin/:/usr/bin/:/usr/local/bin"

source /etc/ltestart.conf

while [ "$1" != "" ] ; do

    if [ -e "$1" ] ; then
        # Avoid storing logs with comments only
        HAS_LOG=$(grep -v -l "#" $1)
        if [ "$HAS_LOG" != "" ] ; then
            DATE=$(date -u +%Y%m%d.%H:%M:%S | sed -e "s/ /-/g")
            FILE=$(basename $1)
            mv $1 "${LOG_PATH}/${FILE}.${DATE}"
        else
            rm -f $1
        fi
    fi
    shift
done

