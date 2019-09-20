import json
import sys
import subprocess

surykatka = sys.argv[1]

key = sys.argv[2]
url = sys.argv[3]
http_code = sys.argv[4]
ip_list = sys.argv[5:]

output = subprocess.check_output([surykatka])

jsoned = json.loads(output)
entry_list = [q for q in jsoned[key] if q['url'] == url]
entry_list_dump = json.dumps(entry_list, indent=2)
http_code_list = [q['status_code'] for q in entry_list]
db_ip_list = [q['ip'] for q in entry_list]
status = True
if not all([http_code == str(q) for q in http_code_list]):
  print 'http_code %s does not match at least one entry in:\n%s' % (http_code, entry_list_dump)
  status = False
if len(ip_list):
  if set(ip_list) != set(db_ip_list):
    print 'ip_list %s differes from:\n%s' % (ip_list, entry_list_dump)
    status = False
if not status:
  sys.exit(1)
