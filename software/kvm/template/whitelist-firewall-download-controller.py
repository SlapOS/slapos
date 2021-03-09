#!/usr/bin/env python

import os
import subprocess
import sys
import time
import logging


# Note: Assuring only one running instance is not done, as this script is only
#       run from supervisord, which does it already
if __name__ == "__main__":
  curl, sleep, output, url = sys.argv[1:]
  sleep = int(sleep)
  tmp_output = output + '.tmp'

  logging.basicConfig(
    format='%%(asctime)s [%%(levelname)s] %s : %%(message)s' % (url,),
    level=logging.DEBUG)
  logging.info('Redownloading each %is', sleep)
  while True:
    logging.info('Fetching')
    try:
      subprocess.check_output([
        curl,
        '--location',  # follow redirects
        '--no-progress-meter',  # do not tell too much
        '--max-time', '600',  # 10 minutes is maximum
        '--fail',  # fail in case of wrong HTTP code
        '--output', tmp_output, url],
        stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      logging.error('Problem while downloading: %r', e.output.strip())
    if os.path.exists(tmp_output):
      logging.info('Stored output')
      os.rename(tmp_output, output)
    logging.info('Sleeping for %is', sleep)
    time.sleep(sleep)
