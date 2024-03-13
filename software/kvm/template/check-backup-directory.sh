#!/bin/bash

directory=$1
tmp=$2

# support a case of not ready yet directory
if [ ! -d $directory ] ; then
  exit 0
fi

tmpfile=$(mktemp -p $tmp)

trap "rm -fr $tmpfile" EXIT TERM INT

find $directory -type f -name 'FULL*qcow2' -printf '%f\n' > $tmpfile
full_amount=$(wc -l $tmpfile | cut -d ' ' -f 1)
if [ $full_amount -gt 1 ]; then
  echo "Too many FULL backups"
  cat $tmpfile
  exit 1
fi

find $directory -type f -name 'INC*qcow2' -printf '%f\n' > $tmpfile
if [ $(wc -l $tmpfile | cut -d ' ' -f 1) -gt 0 ] && [ $full_amount -eq 0 ] ; then
  echo "INC present but no FULL backup"
  cat $tmpfile
  exit 1
fi

find $directory -type f -name '*.partial' -printf '%f\n' > $tmpfile
if [ $(wc -l $tmpfile | cut -d ' ' -f 1) -ne 0 ]; then
  echo "Partial file present"
  cat $tmpfile
  exit 1
fi

exit 0
