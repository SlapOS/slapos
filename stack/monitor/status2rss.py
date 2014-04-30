import datetime
import PyRSS2Gen
import sys
from email.utils import parsedate_tz, mktime_tz
import base64

# Based on http://thehelpfulhacker.net/2011/03/27/a-rss-feed-for-your-crontabs/

# ### Defaults
TITLE = sys.argv[1]
LINK = sys.argv[2]
DESCRIPTION = TITLE

items = []

while 1:
  try:
    line = sys.stdin.readline()
  except KeyboardInterrupt:
    break

  if not line:
    break

  time, desc = line.split(',', 1)

  rss_item = PyRSS2Gen.RSSItem(
    title = desc,
    description = "%s, %s" % (time, desc),
    link = LINK,
    pubDate = datetime.datetime.fromtimestamp(mktime_tz(parsedate_tz(time))),
    guid = PyRSS2Gen.Guid(base64.b64encode("%s, %s" % (time, desc)))
    )
  items.append(rss_item)

### Build the rss feed
items.reverse()
rss_feed = PyRSS2Gen.RSS2 (
  title = TITLE,
  link = LINK,
  description = DESCRIPTION,
  lastBuildDate = datetime.datetime.utcnow(),
  items = items
  )

print rss_feed.to_xml()
