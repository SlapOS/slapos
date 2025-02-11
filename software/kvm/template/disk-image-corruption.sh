#!/bin/sh
  # Return code 0 is "OK"
  # Return code 3 is "found leaks, but image is OK"
  # http://git.qemu.org/?p=qemu.git;a=blob;f=qemu-img.c;h=4e9a7f5741c9cb863d978225829e68fefcae3947;hb=HEAD#l702
  if [ "{{ disk_device_path }}" != "" ]; then
    # disk device option is used, skip qemu img check
    exit 0
  fi
  {{ qemu_img_path }} check -U {{ disk_path }} > /dev/null 2>&1
  RETURN_CODE=$?
  if [ $RETURN_CODE -eq 0 ] || [ $RETURN_CODE -eq 3 ]; then
    exit 0
  else
    exit 1
  fi

