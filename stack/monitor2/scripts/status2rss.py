import sys
import os
import json
import datetime
import base64
import hashlib
import PyRSS2Gen

def getKey(item):
  return item.pubDate

def main():
  _, title, link, base_url, status_folder, output_path = sys.argv

  rss_item_list = []
  for filename in os.listdir(status_folder):
    if filename.endswith(".status.json"):
      filepath = os.path.join(status_folder, filename)
      result_dict = None
      try:
        result_dict = json.load(open(filepath, "r"))
      except ValueError:
        print "Failed to load json file: %s" % filepath
        continue
      description = result_dict.get('message', '')
      event_time = datetime.datetime.fromtimestamp(result_dict['change-time'])
      rss_item = PyRSS2Gen.RSSItem(
        title = '[%s] %s' % (result_dict['status'], result_dict['title']),
        description = "%s: %s\n%s" % (event_time, result_dict['status'], description),
        link = '%s/%s' % (base_url, filename),
        pubDate = event_time,
        guid = PyRSS2Gen.Guid(base64.b64encode("%s, %s" % (event_time, result_dict['status'])))
      )
      rss_item_list.append(rss_item)


  ### Build the rss feed
  sorted(rss_item_list, key=getKey)
  rss_feed = PyRSS2Gen.RSS2 (
    title = title,
    link = link,
    description = '',
    lastBuildDate = datetime.datetime.utcnow(),
    items = rss_item_list
    )
  with open(output_path, 'w') as frss:
    frss.write(rss_feed.to_xml())

if __name__ == "__main__":
  exit(main())
