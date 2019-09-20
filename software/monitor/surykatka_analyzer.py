import datetime
import email.utils
import json
import subprocess
import sys
import time

surykatka = sys.argv[1]

key = sys.argv[2]
status = True
if key == 'http_query':
  url = sys.argv[3]
  http_code = sys.argv[4]
  ip_list = sys.argv[5:]

  output = subprocess.check_output([surykatka, '--url', url])
  jsoned = json.loads(output)
  entry_list = [q for q in jsoned[key] if q['url'] == url]
  entry_list_dump = json.dumps(entry_list, indent=2)
  http_code_list = [q['status_code'] for q in entry_list]
  db_ip_list = [q['ip'] for q in entry_list]
  if not all([http_code == str(q) for q in http_code_list]):
    print 'http_code %s does not match at least one entry in:\n%s' % (
      http_code, entry_list_dump)
    status = False
  if len(ip_list):
    if set(ip_list) != set(db_ip_list):
      print 'ip_list %s differes from:\n%s' % (ip_list, entry_list_dump)
      status = False
elif key == 'bot_status':
  output = subprocess.check_output([surykatka])
  jsoned = json.loads(output)
  value = jsoned[key][0]
  value_dump = json.dumps(value, indent=2)
  if value['text'] != 'loop':
    print 'Not loop type detected in:\n%s' % (value_dump,)
    status = False
  timetuple = email.utils.parsedate(value['date'])
  last_bot_datetime = datetime.datetime.fromtimestamp(time.mktime(timetuple))
  utcnow = datetime.datetime.utcnow()
  delta = utcnow - last_bot_datetime
  # sanity check
  if delta < datetime.timedelta(minutes=0):
    print 'Last bot datetime %s seems in future, UTC now %s' % (
      last_bot_datetime, utcnow)
    status = False
  if delta > datetime.timedelta(minutes=15):
    print 'Last bot datetime %s is more than 15 minutes old, UTC now %s' % (
      last_bot_datetime, utcnow)
    status = False
else:
  print 'Unknown key %s' % (key,)
  status = False
if not status:
  sys.exit(1)
