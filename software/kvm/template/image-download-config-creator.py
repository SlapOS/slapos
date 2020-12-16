#!/usr/bin/env python

import hashlib
import json
import re
import sys


if __name__ == "__main__":
  source_configuration, destination_configuration, \
    destination_directory, error_state_file = sys.argv[1:]
  md5sum_re = re.compile(r"^([a-fA-F\d]{32})$")
  image_prefix = 'image_'
  maximum_image_amount = 4

  # build currently wanted list
  configuration_dict = {
    'destination-directory': destination_directory,
  }
  image_list = []
  error_list = []
  print('INF: Storing errors in %s' % (error_state_file,))
  with open(source_configuration, 'rb') as fh:
    image_number = 0
    data = fh.read()
    configuration_dict['config-md5sum'] = hashlib.md5(data).hexdigest()
    if source_configuration.endswith('.json'):
      data = data.strip()
      data_list = []
      if len(data):
        try:
          data_list = json.loads(data)
        except Exception:
          error_list.append('ERR: Data is not a JSON')
          data_list = []
    else:
      data_list = data.decode('utf-8').split()
    for entry in data_list:
      split_entry = entry.split('#')
      if len(split_entry) != 2:
        error_list.append('ERR: entry %r is incorrect' % (entry,))
        continue
      url, md5sum = split_entry
      if not md5sum_re.match(md5sum):
        error_list.append('ERR: checksum in entry %r is malformed' % (entry, ))
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
    error_list.append(
      'ERR: Amount of images is %s, which is bigger than maximum (%s)' % (
        image_amount, maximum_image_amount))
  else:
    configuration_dict['image-list'] = image_list
  error_amount = len(error_list)
  configuration_dict['error-amount'] = error_amount
  with open(destination_configuration, 'w') as fh:
    json.dump(configuration_dict, fh, indent=2)
  with open(error_state_file, 'w') as fh:
    if error_amount == 0:
      print('INF: Configuration generated without errors')
      fh.write('')
    else:
      print('ERR: Configuration generated with %s errors' % (error_amount,))
      fh.write('\n'.join(error_list))
  sys.exit(error_amount)
