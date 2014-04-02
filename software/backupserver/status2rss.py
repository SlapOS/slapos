import datetime
import uuid
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

  time, statistic, desc = line.split(',', 2)

  rss_item = PyRSS2Gen.RSSItem(
    title = desc,
    description = "<p>%s</p>" % "<br/>".join(("%s, %s\n<a href='http://www.nongnu.org/rdiff-backup/FAQ.html#statistics'>Lastest statistic</a>\n%s" % (time, desc,
      open(statistic).read())).split("\n")),
    link = LINK,
    pubDate = datetime.datetime.fromtimestamp(mktime_tz(parsedate_tz(time))),
    guid = PyRSS2Gen.Guid(base64.b64encode("%s, %s" % (time, desc)))
    )
  items.append(rss_item)

### Build the rss feed
rss_feed = PyRSS2Gen.RSS2 (
  title = TITLE,
  link = LINK,
  description = DESCRIPTION,
  lastBuildDate = datetime.datetime.utcnow(),
  items = items
  )

print rss_feed.to_xml()
