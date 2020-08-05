#!/usr/bin/env python

import json
import re
import sys


if __name__ == "__main__":
  source_configuration, destination_configuration, \
    destination_directory, error_state_file = sys.argv[1:]
  error_amount = 0
  md5sum_re = re.compile(r"^([a-fA-F\d]{32})$")
  image_prefix = 'image_'
  maximum_image_amount = 4

  # build currently wanted list
  configuration_dict = {
    'destination-directory': destination_directory,
  }
  image_list = []
  with open(source_configuration) as fh:
    image_number = 0
    for entry in fh.read().split():
      split_entry = entry.split('#')
      if len(split_entry) != 2:
        print('ERR: entry %r is incorrect' % (entry,))
        error_amount += 1
        continue
      url, md5sum = split_entry
      if not md5sum_re.match(md5sum):
        error_amount += 1
        print('ERR: checksum in entry %r is malformed' % (entry, ))
        continue
      if md5sum not in [q['md5sum'] for q in image_list]:
        image_number += 1
        image_list.append({
          'md5sum': md5sum,
          'url': url,
          'destination': md5sum,
          'destination-tmp': md5sum + '_tmp',
          'link': 'image_%03i' % (image_number,),
        })
      else:
        print('INF: checksum %s repeated, used url %s' % (url, ))
  image_amount = len(image_list)
  if image_amount > maximum_image_amount:
    print('ERR: Amount of images is %s, which is bigger than maximum '
          '(%s)' % (image_amount, maximum_image_amount))
    error_amount += 1
  else:
    configuration_dict['image-list'] = image_list
  configuration_dict['error-amount'] = error_amount
  with open(destination_configuration, 'w') as fh:
    json.dump(configuration_dict, fh, indent=2)
  with open(error_state_file, 'w') as fh:
    if error_amount == 0:
      print('INF: Configuration generated without errors')
      fh.write('')
    else:
      print('ERR: Configuration generated with %s errors' % (error_amount,))
      fh.write('%s' % (error_amount,))
  sys.exit(error_amount)
