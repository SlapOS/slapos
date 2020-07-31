#!/usr/bin/env python

import json
import os
import re
import sys


if __name__ == "__main__":
  source_configuration, destination_configuration, \
    destination_directory = sys.argv[1:]
  error_num = 0
  md5sum_re = re.compile(r"^([a-fA-F\d]{32})$")
  current_image_dict = {}
  image_prefix = 'image_'

  # build currently wanted list
  configuration_dict = {}
  with open(source_configuration) as fh:
    for line in fh.readlines():
      line = line.strip()
      if not line:
        continue
      split_line = line.split(' ')
      if len(split_line) != 2:
        print 'ERR: line %r is incorrect' % (line,)
        error_num += 1
        continue
      url, md5sum = split_line
      if not md5sum_re.match(md5sum):
        error_num += 1
        print 'ERR: checksum in line %r is incorrect' % (line, )
        continue
      if md5sum not in current_image_dict.items():
        configuration_dict[md5sum] = {
          'url': url,
      else:
        print 'INF: checksum %s repeated, used url %s' % (
      
      configuration_dict['error-amount'] = error_num
      configuration_dict['destination-directory'] = destination_directory
      json.dump(configuration_dict, fh, indent=2)
    sys.exit(error_num)
