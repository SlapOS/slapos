#!/usr/bin/env python

import hashlib
import json
import os
import re
import subprocess
import sys


# stolen from download_file.in
def md5Checksum(file_path):
  with open(file_path, 'rb') as fh:
    m = hashlib.md5()
    while True:
      data = fh.read(8192)
      if not data:
          break
      m.update(data)
    return m.hexdigest()


if __name__ == "__main__":
  configuration, curl, md5sum_fail_file, state_file, processed_md5sum = sys.argv[1:]
  error_amount = 0
  md5sum_re = re.compile(r"^([a-fA-F\d]{32})$")
  image_prefix = 'image_'

  # build currently wanted list
  with open(configuration) as fh:
    try:
      config = json.load(fh)
    except Exception as e:
      print('ERR: Problem loading configuration: %s' % (e,))
      sys.exit(1)

  if config['error-amount'] != 0:
    print('ERR: There are problems with configuration')
    sys.exit(1)

  # clean the destination directory
  file_to_keep_list = []
  for image in config['image-list']:
    file_to_keep_list.append(image['destination'])
    file_to_keep_list.append(image['link'])
  for fname in os.listdir(config['destination-directory']):
    if fname not in file_to_keep_list:
      print('INF: Removing obsolete %s' % (fname,))
      os.remove(os.path.join(config['destination-directory'], fname))

  # prepare state dicts
  # current and new are used to remove not existing configurations
  # and also to allow re-add some configuration
  try:
    with open(md5sum_fail_file) as fh:
      md5sum_state_dict = json.load(fh)
  except Exception:
    md5sum_state_dict = {}
  new_md5sum_state_dict = {}
  
  # fetch the wanted list
  for image in config['image-list']:
    destination = os.path.join(
      config['destination-directory'], image['destination'])
    if os.path.exists(destination):
      if md5Checksum(destination) == image['md5sum']:
        print('INF: %s : already downloaded' % (image['url'],))
        continue
      else:
        print('INF: %s : Removed, as expected checksum does not match %s' % (
          image['url'], image['md5sum']))
        os.remove(destination)
    # key is str, as the dict is dumped to JSON which does not accept tuples
    md5sum_state_key = '%s#%s' % (image['url'], image['md5sum'])
    md5sum_state_amount = md5sum_state_dict.get(md5sum_state_key, 0)
    if md5sum_state_amount >= 4:
      new_md5sum_state_dict[md5sum_state_key] = md5sum_state_amount
      print(
        'ERR: %s : Checksum is incorrect after %s tries, will not retry' % (
          image['url'], md5sum_state_amount))
      error_amount += 1
      continue
    print('INF: %s : Downloading' % (image['url'],))
    download_success = True
    destination_tmp = os.path.join(
      config['destination-directory'], image['destination-tmp'])
    try:
      subprocess.check_output([
        curl,
        '--insecure',  # allow any download
        '--location',  # follow redirects
        '--no-progress-meter',  # do not tell too much
        '--max-time', '14400',  # maximum time for download is 4 hours
        '--max-filesize', '5368709120',  # maximum 5G for an image
        '--output', destination_tmp, image['url']],
        stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      error_amount += 1
      print('ERR: %s : Problem while downloading: %r' % (
        image['url'], e.output.strip()))
      continue
    if not(os.path.exists(destination_tmp)):
      error_amount += 1
      print('ERR: %s : Image disappeared, will retry later')
      continue
    computed_md5sum = md5Checksum(destination_tmp)
    if computed_md5sum != image['md5sum']:
      error_amount += 1
      try:
        os.remove(destination_tmp)
      except Exception:
        pass
      print('ERR: %s : MD5 mismatch expected is %s but got instead %s' % (
        image['url'], image['md5sum'], computed_md5sum))
      # Store yet another failure while computing md5sum for this
      new_md5sum_state_dict[md5sum_state_key] = md5sum_state_amount + 1
    else:
      os.rename(destination_tmp, destination)
      print('INF: %s : Stored with checksum %s' % (
        image['url'], image['md5sum']))
  for image in config['image-list']:
    destination = os.path.join(
      config['destination-directory'], image['destination'])
    link = os.path.join(config['destination-directory'], image['link'])
    if os.path.exists(destination):
      if os.path.lexists(link):
        if not os.path.islink(link):
          os.remove(link)
        if os.path.islink(link) and os.readlink(link) != destination:
            os.remove(link)
      if not os.path.lexists(link):
        print('INF: %s : Symlinking %s -> %s' % (
          image['url'], link, destination))
        os.symlink(destination, link)
  with open(md5sum_fail_file, 'w') as fh:
    if new_md5sum_state_dict != {}:
      json.dump(new_md5sum_state_dict, fh, indent=2)
    else:
      # if no problems reported, just empty the file
      fh.write('')
  with open(state_file, 'w') as fh:
    if error_amount == 0:
      fh.write('')
    else:
      json.dump({'error-amount': error_amount}, fh)
  with open(processed_md5sum, 'w') as fh:
   fh.write(config['config-md5sum'])
  sys.exit(error_amount)
