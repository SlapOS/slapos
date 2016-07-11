import sys
import os
import json
from datetime import datetime
import base64
import hashlib
import PyRSS2Gen
import argparse

def parseArguments():
  """
  Parse arguments for monitor Rss Generator.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('--items_folder',
                      help='Path where to get *.status.json files which contain result of promises.')
  parser.add_argument('--output',
                      help='The Path of file where feed file will be saved.')
  parser.add_argument('--feed_url',
                      help='Url of this feed file.')
  parser.add_argument('--public_url',
                      help='Monitor Instance public URL.')
  parser.add_argument('--private_url',
                      help='Monitor Instance private URL.')
  parser.add_argument('--instance_name',
                      default='UNKNOW Software Instance',
                      help='Software Instance name.')
  parser.add_argument('--hosting_name',
                      default='',
                      help='Hosting Subscription name.')

  return parser.parse_args()

def getKey(item):
  return item.pubDate

def main():
  parser = parseArguments()

  rss_item_list = []
  report_date = datetime.utcnow()
  for filename in os.listdir(parser.items_folder):
    if filename.endswith(".status.json"):
      filepath = os.path.join(parser.items_folder, filename)
      result_dict = None
      try:
        result_dict = json.load(open(filepath, "r"))
      except ValueError:
        print "Failed to load json file: %s" % filepath
        continue
      description = result_dict.get('message', '')
      event_time = datetime.fromtimestamp(result_dict['change-time'])
      rss_item = PyRSS2Gen.RSSItem(
        categories = [result_dict['status']],
        source = PyRSS2Gen.Source(result_dict['title'], parser.public_url),
        title = '[%s] %s' % (result_dict['status'], result_dict['title']),
        comments = description,
        description = "%s: %s\n%s" % (event_time, result_dict['status'], description),
        link = parser.private_url,
        pubDate = event_time,
        guid = PyRSS2Gen.Guid(base64.b64encode("%s, %s" % (parser.hosting_name, result_dict['title'])))
      )
      rss_item_list.append(rss_item)


  ### Build the rss feed
  sorted(rss_item_list, key=getKey)
  rss_feed = PyRSS2Gen.RSS2 (
    title = parser.instance_name,
    link = parser.feed_url,
    description = parser.hosting_name,
    lastBuildDate = report_date,
    items = rss_item_list
    )

  with open(parser.output, 'w') as frss:
    frss.write(rss_feed.to_xml())

if __name__ == "__main__":
  exit(main())
