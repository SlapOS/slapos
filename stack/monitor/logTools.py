from pyparsing import Word, alphas, Suppress, Combine, nums, string, Optional, Regex, Literal
import os, re
import datetime
import uuid
import base64
import sqlite3
import PyRSS2Gen

def init_db(db_path):
  db = sqlite3.connect(db_path)
  c = db.cursor()
  c.executescript("""
CREATE TABLE IF NOT EXISTS rss_entry (
  name VARCHAR(25),
  datetime VARCHAR(15),
  status VARCHAR(20),
  method VARCHAR(25),
  title VARCHAR(255),
  url VARCHAR(255),
  content TEXT);
""")
  db.commit()
  db.close()

def getZopeLogRequestParser():
  integer = Word(nums)
  serverDateTime = Combine(integer + "-" + integer + "-" + integer + " " + 
                        integer + ":" + integer + ":" + integer + "," + integer)
  word = Word( alphas+nums+"@._-" )
  info = Regex("([\d\w\s:\.]+;){2}")#Combine(word + ";" + Literal(" ") + word + ";")
  request = Combine(Suppress("request: ") + Suppress(word+" ") + Regex(".*"))
  no_request = Combine(Suppress("[No request]") + Regex(".*"))
  bnf = serverDateTime.setResultsName("timestamp") +  Suppress("-") + \
          info.setResultsName("title") + \
          (no_request | request).setResultsName("link")
  return bnf

def getZopeParser():
  integer = Word(nums)
  serverDateTime = Combine(integer + "-" + integer + "-" + integer + " " + 
                      integer + ":" + integer + ":" + integer + "," + integer)
  status = Word(string.uppercase, max=7, min=3)
  word = Word( alphas+nums+"@._-" )
  message = Regex(".*")
  bnf = serverDateTime.setResultsName("timestamp") + \
          status.setResultsName("statusCode") + \
          word.setResultsName("method") + message.setResultsName("title")
  return bnf

def isZopeLogBeginLine(line):
  # This expression will check if line start with a date string
  # XXX - if line match expression, then regex.group() return the date
  if not line or line.strip() == "------":
    return None
  regex = re.match(r"(^\d{2,4}-\d{2}-\d{1,2}\s+\d{2}:\d{2}:\d{2}?[,\d]+)",
                        line)
  return regex
  

def parseLog(path, parserbnf, method, filter_with="ERROR", start_date="", date_format=""):
  if not os.path.exists(path):
    print "ERROR: cannot get file: %s" % path
    return []
  log_result = []
  if not date_format:
    date_format = "%Y-%m-%d %H:%M:%S,%f"
  with open(path, 'r') as logfile:
    index = 0
    for line in logfile:
      regex = method(line)
      if not regex:
        if index == 0 or line.strip() == "------":
          continue
        # Add this line to log content
        log_result[index - 1]['content'] += ("\n" + line)
      else:
        try:
          fields = parserbnf.parseString(line)
          if filter_with and not fields.statusCode == filter_with:
            continue
          if start_date and regex.group() < start_date:
            continue
          log_result.append(dict(datetime=datetime.datetime.strptime(
                            fields.timestamp , date_format),
                            status=fields.get('statusCode', ''),
                            method=fields.get('method', ''),
                            url=fields.get('link', ''),
                            title=fields.title,
                            content=fields.get('content', fields.title)))
          index += 1
        except Exception:
          raise
          # print "WARNING: Could not parse log line. %s \n << %s >>" % (str(e), line)
  return log_result

def insertRssDb(db_path, entry_list, rss_name):
  init_db(db_path)
  db = sqlite3.connect(db_path)
  for entry in entry_list:
    date = entry['datetime'].strftime('%Y-%m-%d %H:%M:%S')
    db.execute("insert into rss_entry(name, datetime, status, method, title, url, content) values (?, ?, ?, ?, ?, ?, ?)",
                (rss_name, date, entry['status'], entry['method'], entry['title'], entry['url'], entry['content']))
  db.commit()
  db.close()

def truncateRssDb(db_path, to_date):
  db = sqlite3.connect(db_path)
  db.execute("delete from rss_entry where datetime<?", (to_date,))
  db.commit()
  db.close()

def selectRssDb(db_path, rss_name, start_date, limit=0):
  db = sqlite3.connect(db_path)
  query = "select name, datetime, status, method, title, url, content from rss_entry "
  query += "where name=? and datetime>=? order by datetime DESC"
  if limit:
    query += " limit ?"
    rows = db.execute(query, (rss_name, start_date, limit))
  else:
    rows = db.execute(query, (rss_name, start_date))
  #db.close()
  if rows:
    return rows
  return []

def generateRSS(db_path, name, rss_path, start_date, url_link, limit=0):
  items = []
  
  db = sqlite3.connect(db_path)
  query = "select name, datetime, status, method, title, url, content from rss_entry "
  query += "where name=? and datetime>=? order by datetime DESC"
  if limit:
    query += " limit ?"
    entry_list = db.execute(query, (name, start_date, limit))
  else:
    entry_list = db.execute(query, (name, start_date))
  
  for entry in entry_list:
    name, rss_date, status, method, title, url, content = entry
    if method:
      title = "[%s] %s" % (method, title)
    if status:
      title = "[%s] %s" % (status, title)
    rss_item = PyRSS2Gen.RSSItem(
        title = title,
        link = url,
        description = content.replace('\n', '<br/>'),
        pubDate = rss_date,
        guid = PyRSS2Gen.Guid(base64.b64encode("%s, %s" % (rss_date, url_link)))
        )
    items.append(rss_item)
  db.close()
  
  ### Build the rss feed
  items.reverse()
  rss_feed = PyRSS2Gen.RSS2 (
    title = name,
    link = url_link,
    description = name,
    lastBuildDate = datetime.datetime.utcnow(),
    items = items
    )

  with open(rss_path, 'w') as rss_ouput:
    rss_ouput.write(rss_feed.to_xml())
