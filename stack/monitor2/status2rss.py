import sys
import os
import json
import datetime
import base64
import hashlib

def main():
  _, title, link, public_folder, previous_status_path, output_path = sys.argv
  final_status = "OK";
  # getting status
  for filename in os.listdir(public_folder):
    if filename.endswith(".status.json"):
      filepath = os.path.join(public_folder, filename)
      status = None
      try:
        status = json.load(open(filepath, "r"))
      except ValueError:
        continue
      try:
        if status["status"] != "OK":
          final_status = "BAD"
          break
      except KeyError:
        final_status = "BAD"
        break
  # checking previous status
  try:
    status = open(previous_status_path, "r").readline(4)
    if status == final_status:
      return 0
  except IOError:
    pass
  # update status
  open(previous_status_path, "w").write(final_status)
  # generating RSS
  utcnow = datetime.datetime.utcnow()
  open(output_path, "w").write(
    newRssString(
      title,
      title,
      link,
      utcnow,
      utcnow,
      "60",
      [
        newRssItemString(
          "Status is %s" % final_status,
          "Status is %s" % final_status,
          link,
          newGuid("%s, %s" % (utcnow, final_status)),
          utcnow,
        )
      ],
    )
  )


def escapeHtml(string):
  return string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;")

def newGuid(string):
  sha256 = hashlib.sha256()
  sha256.update(string)
  return sha256.hexdigest()

def newRssItemString(title, description, link, guid, pub_date, guid_is_perma_link=True):
  return """<item>
 <title>%(title)s</title>
 <description>%(description)s</description>
 <link>%(link)s</link>
 <guid isPermaLink="%(guid_is_perma_link)s">%(guid)s</guid>
 <pubDate>%(pub_date)s</pubDate>
</item>""" % {
    "title": escapeHtml(title),
    "description": escapeHtml(description),
    "link": escapeHtml(link),
    "guid": escapeHtml(guid),
    "pub_date": escapeHtml(pub_date.strftime("%a, %d %b %Y %H:%M:%S +0000")),
    "guid_is_perma_link": escapeHtml(repr(guid_is_perma_link).lower()),
  }

def newRssString(title, description, link, last_build_date, pub_date, ttl, rss_item_string_list):
  return """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
 <title>%(title)s</title>
 <description>%(description)s</description>
 <link>%(link)s</link>
 <lastBuildDate>%(last_build_date)s</lastBuildDate>
 <pubDate>%(pub_date)s</pubDate>
 <ttl>%(ttl)s</ttl>
%(items)s
</channel>
</rss>
""" % {
    "title": escapeHtml(title),
    "description": escapeHtml(description),
    "link": escapeHtml(link),
    "last_build_date": escapeHtml(last_build_date.strftime("%a, %d %b %Y %H:%M:%S +0000")),
    "pub_date": escapeHtml(pub_date.strftime("%a, %d %b %Y %H:%M:%S +0000")),
    "ttl": escapeHtml(str(ttl)),
    "items": "\n\n".join([" " + item.replace("\n", "\n ") for item in rss_item_string_list]),
  }

if __name__ == "__main__":
  exit(main())
