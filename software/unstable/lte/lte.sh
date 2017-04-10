#!/bin/bash

function stopLTE {
  sudo /bin/systemctl stop lte
  echo "LTE service stopped"
  exit 0
}
trap stopLTE TERM INT KILL

sudo /bin/systemctl start lte

while (( 1 )); do 
  sleep 1
done
