#!{{ python_executable }}

import cgi
import cgitb
import json
import sys

cgitb.enable(display=0, logdir="/tmp/cgi.log")

json_file = "{{ json_file }}"
result = json.load(open(json_file))

# Headers
print "Content-Type: text/html"
print

# Body content
form = cgi.FieldStorage()
if "password" not in form:
  print """<html>
  <body>
  <h1>This is the monitoring interface</h1>
  <p>Please enter the monitor_password in the next field to access the data</p>
  <form action="/index.cgi" method="post">
    Password : <input type="password" name="password">
    <input type="submit" value="Access">
  </form></body></html>"""

elif form['password'].value != '{{ password }}':
  print "<html><body><h1>Error</h1><p>Wrong password</p></body></html>"

else:
  print "<html><body>"
  print "<h1>Monitoring :</h1>"
  print "<p><em>Last time of monitoring process : %s</em></p>" % (result['datetime'])
  del result['datetime']
  print "<br/>"

  print "<h2>These scripts and promises have failed :</h2>"
  for r in result:
    if result[r] != '':
      print "<h3>%s</h3><p style=\"padding-left:30px;\">%s</p>" % (r, result[r])
  print "<br/>"

  print "<h2>These scripts and promises were successful :</h2>"
  for r in result:
    if result[r] == '':
      print "<h3>%s</h3><p>%s</p>" % (r, result[r])
  print "</body></html>"