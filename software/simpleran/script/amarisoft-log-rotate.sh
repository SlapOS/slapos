#!/bin/sh

# Rotate and limit combined and individual Amarisoft log sizes
# This program should be launched before starting Amarisoft program

usage() {
  cat << ENDUSAGE
Required parameters:
 START_DATE                       Path of file containing Amarisoft program start date
 LOG                              Amarisoft log path
 STDOUT_LOG                       Path of log containing stdout of the Amarisoft program
 MAX_COMBINED_LOG_KB_SIZE         Max combined size of all Amarisoft logs, in kB
 MAX_COMBINED_STDOUT_LOG_KB_SIZE  Max combined size of all Amarisoft stdout logs, in kB
 MAX_STDOUT_LOG_KB_SIZE           Max individual size of Amarisoft stdout logs
 MAX_LOG_FILE_NUMBER              Max number of Amarisoft logs
ENDUSAGE
1>&2;
}

START_DATE=$1
LOG=$2
STDOUT_LOG=$3
MAX_COMBINED_LOG_KB_SIZE=$4
MAX_COMBINED_STDOUT_LOG_KB_SIZE=$5
MAX_STDOUT_LOG_KB_SIZE=$6
MAX_LOG_FILE_NUMBER=$7
MAX_LOG_FILE_NUMBER=$((MAX_LOG_FILE_NUMBER/2))

if [ $# -ne 7 ] ; then
  usage ; exit 1
fi

set -x

while true
do {
  # Split stdout log into smaller chunks
  if test $(du $STDOUT_LOG | cut -f1) -ge $MAX_STDOUT_LOG_KB_SIZE ; then
    stat $START_DATE > /dev/null 2>&1 || date +"%Y%m%d.%T" > $START_DATE
    head -c -$(($MAX_STDOUT_LOG_KB_SIZE/2))k $STDOUT_LOG > $STDOUT_LOG.$(cat $START_DATE)
    tail -c  $(($MAX_STDOUT_LOG_KB_SIZE/2))k $STDOUT_LOG > $STDOUT_LOG.tmp
    mv $STDOUT_LOG.tmp $STDOUT_LOG
    date +"%Y%m%d.%T" > $START_DATE
  fi

  # Remove almost empty enb radio archive log files
  rm -f $(find $(dirname $LOG) -name "$(basename $LOG).*" -size -5k)

  # Make sure there are not too much logs
  LOG_COUNT=$(ls $LOG.* | wc -l)
  if [ $LOG_COUNT -ge $MAX_LOG_FILE_NUMBER ] ; then
    rm -f $(ls -1t $LOG.* | tail -n $((LOG_COUNT-MAX_LOG_FILE_NUMBER)))
  fi
  LOG_COUNT=$(ls $STDOUT_LOG.* | wc -l)
  if [ $LOG_COUNT -ge $MAX_LOG_FILE_NUMBER ] ; then
    rm -f $(ls -1t $STDOUT_LOG.* | tail -n $((LOG_COUNT-MAX_LOG_FILE_NUMBER)))
  fi

  # Limit combined size for archived logs
  trim() {
    stat > /dev/null 2>&1 $2* || return
    i=-1
    N=$(ls -1t $2* | wc -l)
    TOTAL=$1
    while [ $TOTAL -ge $1 ] && [ $((N-i)) -ge 1 ] ; do
      i=$((i+1))
      TOTAL=$(du -c $(ls -1t $2* | head -n$((N-i))) | tail -n1 | cut -f1)
    done
    rm -f $(ls -1t $2* | tail -n$i)
  }
  trim $MAX_COMBINED_LOG_KB_SIZE $LOG.
  trim $MAX_COMBINED_STDOUT_LOG_KB_SIZE  $STDOUT_LOG.

  sleep 1
}
done
