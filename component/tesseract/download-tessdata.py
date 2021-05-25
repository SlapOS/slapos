# This is a post-make hook script to download tesseract training data.
#
# This script uses the following buildout options:
#   - tessdata-urls: list of URLs and their expected md5sum as URL fragments
#   - tessdata-location: path where to install the data.

import zc.buildout
import os


def post_make_hook(options, buildout, env):
  if not os.path.exists(directory):
    os.makedirs(options['tessdata-location'])

  download = zc.buildout.download.Download(
      buildout['buildout'],
      hash_name=True,
  )
  for url in options['tessdata-urls'].splitlines():
    url, _, md5sum = url.partition('#')
    if url:
      download(
          url,
          md5sum=md5sum,
          path=os.path.join(options['tessdata-location'],
                            os.path.basename(url)),
      )
