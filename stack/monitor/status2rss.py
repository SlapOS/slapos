import datetime
import PyRSS2Gen
import sys
import sqlite3
import time
import base64

# Based on http://thehelpfulhacker.net/2011/03/27/a-rss-feed-for-your-crontabs/

# ### Defaults
TITLE = sys.argv[1]
LINK = sys.argv[2]
db_path = sys.argv[3]
DESCRIPTION = TITLE
SUCCESS = "SUCCESS"
FAILURE = "FAILURE"

items = []
status = ""

current_timestamp = int(time.time())
# We only build the RSS for the last ten days
period = 3600 * 24 * 10
db = sqlite3.connect(db_path)
rows = db.execute("select timestamp, status from status where timestamp>? order by timestamp", (current_timestamp - period,))
for row in rows:
  line_timestamp, line_status = row
  line_status = line_status.encode()

  if line_status == status:
    continue

  status = line_status

  event_time = datetime.datetime.fromtimestamp(line_timestamp).strftime('%Y-%m-%d %H:%M:%S')

  rss_item = PyRSS2Gen.RSSItem(
    title = status,
    description = "%s: %s" % (event_time, status),
    link = LINK,
    pubDate = event_time,
    guid = PyRSS2Gen.Guid(base64.b64encode("%s, %s" % (event_time, status)))
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
